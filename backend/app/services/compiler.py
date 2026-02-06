"""Compiler service for pre-computed patient summary data.

Provides functions to:
1. Fetch the latest observation per LOINC code, grouped by category
2. Compute trend metadata for numeric observations with historical data
3. Compile node context: batch-fetch and prune all connections from a graph node
4. Batch-fetch FHIR resources from Postgres by fhir_id
5. Prune and enrich FHIR resources for LLM consumption
6. Compute medication recency signals (_recency, _duration_days)
7. Compute dose history for active medications (_dose_history)
8. Infer medication-condition links via encounter traversal (_inferred)
"""

import copy
import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import DateTime, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.agent import _prune_fhir_resource
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

# Observation categories we care about
OBSERVATION_CATEGORIES = frozenset([
    "vital-signs",
    "laboratory",
    "survey",
    "social-history",
])

# Threshold for "stable" trend determination (5%)
TREND_THRESHOLD = 0.05


async def get_latest_observations_by_category(
    db: AsyncSession,
    patient_id: uuid.UUID | str,
) -> dict[str, list[dict[str, Any]]]:
    """Fetch the latest observation per LOINC code, grouped by category.

    Groups observations by their LOINC code and category, taking the most
    recent effectiveDateTime per group. Returns a dict keyed by category
    (vital-signs, laboratory, survey, social-history).

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.

    Returns:
        Dict keyed by category, each value a list of FHIR Observation dicts.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    # Use a window function to rank observations by effectiveDateTime
    # within each (LOINC code, category) group, then take rank 1.
    #
    # JSONB path expressions:
    #   LOINC code:  data->'code'->'coding'->0->>'code'
    #   Category:    data->'category'->0->'coding'->0->>'code'
    #   DateTime:    data->>'effectiveDateTime'
    loinc_code = FhirResource.data["code"]["coding"][0]["code"].as_string()
    category_code = FhirResource.data["category"][0]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    # Subquery: rank observations within each (loinc, category) group
    ranked = (
        select(
            FhirResource.data,
            loinc_code.label("loinc_code"),
            category_code.label("category_code"),
            func.row_number()
            .over(
                partition_by=[loinc_code, category_code],
                order_by=func.cast(effective_dt, DateTime).desc(),
            )
            .label("rn"),
        )
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Observation",
            loinc_code.isnot(None),
            category_code.isnot(None),
            category_code.in_(OBSERVATION_CATEGORIES),
        )
        .subquery()
    )

    # Outer query: only the latest per group
    query = select(
        ranked.c.data,
        ranked.c.category_code,
    ).where(ranked.c.rn == 1)

    result = await db.execute(query)
    rows = result.all()

    # Build result dict
    by_category: dict[str, list[dict[str, Any]]] = {
        cat: [] for cat in OBSERVATION_CATEGORIES
    }
    for row in rows:
        cat = row.category_code
        if cat in by_category:
            by_category[cat].append(row.data)

    return by_category


async def compute_observation_trends(
    db: AsyncSession,
    patient_id: uuid.UUID | str,
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute trend metadata for each observation that has historical data.

    For each observation, looks up the previous value of the same LOINC code
    and computes a _trend object with direction, delta, and timespan.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.
        observations: List of FHIR Observation dicts (typically the latest ones).

    Returns:
        The same observations list, with _trend added to numeric observations
        that have a previous value. Non-numeric observations and observations
        without a previous value are returned unchanged.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    # Collect LOINC codes and dates for observations that need trend computation
    trend_candidates: list[tuple[int, str, str]] = []  # (index, loinc, date_str)
    for i, obs in enumerate(observations):
        value_quantity = obs.get("valueQuantity")
        if not value_quantity or not isinstance(value_quantity.get("value"), (int, float)):
            continue
        loinc = _extract_loinc_code(obs)
        date_str = obs.get("effectiveDateTime")
        if loinc and date_str:
            trend_candidates.append((i, loinc, date_str))

    # Batch-fetch previous observations for all candidates in ONE query
    previous_map: dict[tuple[str, str], dict[str, Any]] = {}
    if trend_candidates:
        previous_map = await _get_previous_observations_batch(
            db, patient_id, [(loinc, date_str) for _, loinc, date_str in trend_candidates]
        )

    # Build result with trends
    result = []
    candidate_lookup = {i: (loinc, date_str) for i, loinc, date_str in trend_candidates}
    for i, obs in enumerate(observations):
        obs_copy = copy.deepcopy(obs)

        if i not in candidate_lookup:
            result.append(obs_copy)
            continue

        loinc, date_str = candidate_lookup[i]
        previous = previous_map.get((loinc, date_str))

        if previous is None:
            result.append(obs_copy)
            continue

        prev_vq = previous.get("valueQuantity")
        if not prev_vq or not isinstance(prev_vq.get("value"), (int, float)):
            result.append(obs_copy)
            continue

        current_value = float(obs["valueQuantity"]["value"])
        previous_value = float(prev_vq["value"])
        previous_date_str = previous.get("effectiveDateTime", "")

        trend = _compute_trend(
            current_value=current_value,
            previous_value=previous_value,
            current_date_str=date_str,
            previous_date_str=previous_date_str,
        )
        obs_copy["_trend"] = trend
        result.append(obs_copy)

    return result


def _extract_loinc_code(obs: dict[str, Any]) -> str | None:
    """Extract LOINC code from an Observation's code.coding[0].code."""
    try:
        return obs["code"]["coding"][0]["code"]
    except (KeyError, IndexError, TypeError):
        return None


async def _get_previous_observations_batch(
    db: AsyncSession,
    patient_id: uuid.UUID,
    loinc_date_pairs: list[tuple[str, str]],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Fetch the most recent previous observation for each (LOINC code, date) pair.

    Uses a single query with window functions to avoid N+1 queries.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.
        loinc_date_pairs: List of (loinc_code, before_date_str) tuples.

    Returns:
        Dict mapping (loinc_code, before_date_str) to the previous Observation dict.
        Pairs with no previous observation are omitted.
    """
    if not loinc_date_pairs:
        return {}

    # Collect unique LOINC codes to filter DB rows
    unique_loincs = {loinc for loinc, _ in loinc_date_pairs}

    loinc_expr = FhirResource.data["code"]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    # Fetch all candidate previous observations for these LOINC codes,
    # ranked by date descending within each LOINC code
    ranked = (
        select(
            FhirResource.data,
            loinc_expr.label("loinc_code"),
            effective_dt.label("effective_dt"),
            func.row_number()
            .over(
                partition_by=loinc_expr,
                order_by=func.cast(effective_dt, DateTime).desc(),
            )
            .label("rn"),
        )
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Observation",
            loinc_expr.in_(unique_loincs),
        )
        .subquery()
    )

    # Fetch all ranked rows (we need enough to find the "previous" for each pair)
    query = select(
        ranked.c.data,
        ranked.c.loinc_code,
        ranked.c.effective_dt,
    )

    result = await db.execute(query)
    rows = result.all()

    # Group rows by LOINC code, sorted by date descending
    by_loinc: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_loinc.setdefault(row.loinc_code, []).append(row.data)

    # Sort each group by effectiveDateTime descending (using parsed dates)
    for loinc_code in by_loinc:
        by_loinc[loinc_code].sort(
            key=lambda obs: _parse_fhir_datetime(obs.get("effectiveDateTime", "")),
            reverse=True,
        )

    # For each (loinc, date) pair, find the first observation strictly before the date
    previous_map: dict[tuple[str, str], dict[str, Any]] = {}
    for loinc_code, before_date_str in loinc_date_pairs:
        obs_list = by_loinc.get(loinc_code, [])
        before_dt = _parse_fhir_datetime(before_date_str)
        for obs in obs_list:
            obs_dt = _parse_fhir_datetime(obs.get("effectiveDateTime", ""))
            if obs_dt < before_dt:
                previous_map[(loinc_code, before_date_str)] = obs
                break

    return previous_map


def _compute_trend(
    current_value: float,
    previous_value: float,
    current_date_str: str,
    previous_date_str: str,
) -> dict[str, Any]:
    """Compute trend metadata between two numeric observations.

    Args:
        current_value: The current observation's numeric value.
        previous_value: The previous observation's numeric value.
        current_date_str: ISO datetime of the current observation.
        previous_date_str: ISO datetime of the previous observation.

    Returns:
        Trend dict with direction, delta, delta_percent, previous_value,
        previous_date, and timespan_days.
    """
    delta = current_value - previous_value

    # Direction with 5% threshold
    if previous_value == 0:
        if current_value > 0:
            direction = "rising"
        elif current_value < 0:
            direction = "falling"
        else:
            direction = "stable"
        delta_percent = None
    else:
        delta_percent = (delta / abs(previous_value)) * 100
        if abs(delta_percent) <= TREND_THRESHOLD * 100:
            direction = "stable"
        elif delta > 0:
            direction = "rising"
        else:
            direction = "falling"

    # Compute timespan
    timespan_days = _compute_timespan_days(current_date_str, previous_date_str)

    trend: dict[str, Any] = {
        "direction": direction,
        "delta": delta,
        "delta_percent": delta_percent,
        "previous_value": previous_value,
        "previous_date": previous_date_str,
        "timespan_days": timespan_days,
    }
    return trend


def _compute_timespan_days(current_date_str: str, previous_date_str: str) -> int | None:
    """Compute days between two ISO datetime strings.

    Returns None if either date cannot be parsed.
    """
    try:
        # Handle both datetime and date-only formats
        current_dt = _parse_fhir_datetime(current_date_str)
        previous_dt = _parse_fhir_datetime(previous_date_str)
        return abs((current_dt - previous_dt).days)
    except (ValueError, TypeError):
        return None


def _parse_fhir_datetime(dt_str: str) -> datetime:
    """Parse a FHIR datetime string to a Python datetime.

    Handles common FHIR formats:
    - 2024-01-15T10:30:00Z
    - 2024-01-15T10:30:00+00:00
    - 2024-01-15
    """
    # Strip trailing Z and replace with +00:00 for fromisoformat
    cleaned = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned)


# =============================================================================
# Node Context Compilation
# =============================================================================


async def fetch_resources_by_fhir_ids(
    db: AsyncSession,
    fhir_ids: list[str],
    patient_id: uuid.UUID | str | None = None,
) -> dict[str, dict[str, Any]]:
    """Batch-fetch full FHIR resources from Postgres by fhir_id.

    Args:
        db: Async SQLAlchemy session.
        fhir_ids: List of FHIR IDs to fetch.
        patient_id: Optional patient UUID to scope the query.

    Returns:
        Dict mapping fhir_id to the full FHIR resource data dict.
    """
    if not fhir_ids:
        return {}

    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    query = select(FhirResource.fhir_id, FhirResource.data).where(
        FhirResource.fhir_id.in_(fhir_ids),
    )
    if patient_id is not None:
        query = query.where(FhirResource.patient_id == patient_id)

    result = await db.execute(query)
    rows = result.all()

    return {row.fhir_id: row.data for row in rows}


def prune_and_enrich(
    resource_data: dict[str, Any],
    enrichments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prune a FHIR resource and attach enrichment fields.

    Runs the resource through _prune_fhir_resource() to strip FHIR
    boilerplate, then attaches any synthetic enrichment fields (e.g.
    _trend, _recency, _inferred, _duration_days).

    Args:
        resource_data: Raw FHIR resource dict.
        enrichments: Optional dict of synthetic fields to attach.
            Keys should be underscore-prefixed (e.g. _trend).

    Returns:
        Pruned resource dict with enrichments attached.
    """
    pruned = _prune_fhir_resource(resource_data)
    if enrichments:
        pruned.update(enrichments)
    return pruned


async def compile_node_context(
    fhir_id: str,
    patient_id: uuid.UUID | str,
    graph: KnowledgeGraph,
    db: AsyncSession,
) -> dict[str, list[dict[str, Any]]]:
    """Get all connections from a node, fetch full resources, prune.

    This is the shared building block for both batch compilation (pre-compiled
    patient summaries) and live tool calls (explore_connections). It:

    1. Calls graph.get_all_connections() to discover connected nodes
    2. Batch-fetches full FHIR resources from Postgres (canonical source)
    3. Prunes each resource with _prune_fhir_resource()
    4. For DocumentReference resources, note text is already decoded by the pruner

    Args:
        fhir_id: The FHIR ID of the node to compile context for.
        patient_id: The canonical patient UUID string.
        graph: KnowledgeGraph instance for traversal.
        db: Async SQLAlchemy session for resource fetching.

    Returns:
        Dict keyed by relationship type (e.g. "TREATS", "DIAGNOSED"),
        each value a list of pruned FHIR resource dicts.
    """
    # Step 1: Discover all connections via graph traversal
    connections = await graph.get_all_connections(fhir_id, patient_id=patient_id)

    if not connections:
        return {}

    # Step 2: Collect fhir_ids for batch Postgres fetch
    connected_fhir_ids = [c["fhir_id"] for c in connections if c["fhir_id"]]

    # Step 3: Batch-fetch full resources from Postgres (canonical source)
    # Single query fetches both patient-scoped and shared resources (e.g.
    # Medication nodes which have patient_id=NULL)
    if isinstance(patient_id, str):
        pid = uuid.UUID(patient_id)
    else:
        pid = patient_id
    query = select(FhirResource.fhir_id, FhirResource.data).where(
        FhirResource.fhir_id.in_(connected_fhir_ids),
        or_(
            FhirResource.patient_id == pid,
            FhirResource.patient_id.is_(None),
        ),
    )
    result = await db.execute(query)
    resources_by_id = {row.fhir_id: row.data for row in result.all()}

    # Step 4: Prune each resource and group by relationship type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for conn in connections:
        rel_type = conn["relationship"]
        conn_fhir_id = conn["fhir_id"]

        resource_data = resources_by_id.get(conn_fhir_id)
        if resource_data is None:
            # Resource exists in graph but not in Postgres — skip
            logger.warning(
                "Resource %s found in graph but not in Postgres", conn_fhir_id
            )
            continue

        pruned = prune_and_enrich(resource_data)
        grouped.setdefault(rel_type, []).append(pruned)

    return grouped


# =============================================================================
# Medication Recency Signals
# =============================================================================

# Recency thresholds in days
_RECENCY_NEW_DAYS = 30
_RECENCY_RECENT_DAYS = 180


def compute_medication_recency(
    med_data: dict[str, Any],
    compilation_date: date,
) -> dict[str, Any]:
    """Compute recency and duration metadata for a medication.

    Adds _recency ("new", "recent", or "established") and _duration_days
    based on the authoredOn date relative to the compilation_date.

    Args:
        med_data: FHIR MedicationRequest dict (must have authoredOn for
            recency computation).
        compilation_date: The date to compute recency against.

    Returns:
        Dict with _recency and _duration_days keys. Empty dict if
        authoredOn is missing or unparseable.
    """
    authored_on = med_data.get("authoredOn")
    if not authored_on:
        return {}

    try:
        authored_dt = _parse_fhir_datetime(authored_on)
        # Convert to date for day-level comparison
        authored_date = authored_dt.date() if isinstance(authored_dt, datetime) else authored_dt
    except (ValueError, TypeError):
        return {}

    duration_days = (compilation_date - authored_date).days

    if duration_days < _RECENCY_NEW_DAYS:
        recency = "new"
    elif duration_days <= _RECENCY_RECENT_DAYS:
        recency = "recent"
    else:
        recency = "established"

    return {
        "_recency": recency,
        "_duration_days": duration_days,
    }


# =============================================================================
# Dose History
# =============================================================================


def _extract_dosage_text(med_data: dict[str, Any]) -> str | None:
    """Extract the dosage instruction text from a MedicationRequest.

    Looks at dosageInstruction[0].doseAndRate[0].doseQuantity for a
    structured dose string like "20 MG", falling back to
    dosageInstruction[0].text.
    """
    instructions = med_data.get("dosageInstruction", [])
    if not instructions:
        return None

    first = instructions[0]

    # Try structured dose first
    dose_and_rate = first.get("doseAndRate", [])
    if dose_and_rate:
        dose_qty = dose_and_rate[0].get("doseQuantity", {})
        value = dose_qty.get("value")
        unit = dose_qty.get("unit", "")
        if value is not None:
            return f"{value} {unit}".strip()

    # Fall back to text
    return first.get("text")


def _extract_med_display(med_data: dict[str, Any]) -> str | None:
    """Extract the medication display name from medicationCodeableConcept."""
    concept = med_data.get("medicationCodeableConcept", {})
    codings = concept.get("coding", [])
    if codings:
        return codings[0].get("display")
    return concept.get("text")


async def compute_dose_history(
    db: AsyncSession,
    patient_id: uuid.UUID | str,
    active_med: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compute dose history for an active medication.

    Queries Postgres for prior MedicationRequests with the same medication
    display name but different dosage or a terminal status (completed/stopped).
    Returns a compact chronological list of prior dose entries. Same-dose
    refills are excluded.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.
        active_med: The current active MedicationRequest FHIR dict.

    Returns:
        List of dose history entries (chronological). Each entry has
        "dose", "authoredOn", and "status" keys. Empty list if no
        prior records with different doses exist.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    med_display = _extract_med_display(active_med)
    if not med_display:
        return []

    current_dose = _extract_dosage_text(active_med)
    current_fhir_id = active_med.get("id")

    # Query all MedicationRequests with same medication display
    med_display_expr = FhirResource.data["medicationCodeableConcept"]["coding"][0]["display"].as_string()
    authored_on_expr = FhirResource.data["authoredOn"].as_string()

    query = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "MedicationRequest",
            med_display_expr == med_display,
        )
        .order_by(func.cast(authored_on_expr, DateTime).asc())
    )

    result = await db.execute(query)
    rows = result.all()

    history: list[dict[str, Any]] = []
    for row in rows:
        data = row.data if hasattr(row, "data") else row[0]
        # Skip the active medication itself
        if data.get("id") == current_fhir_id:
            continue

        prior_dose = _extract_dosage_text(data)
        prior_status = data.get("status", "")

        # Only include if dosage differs from current
        if prior_dose == current_dose:
            continue

        entry: dict[str, Any] = {
            "dose": prior_dose,
            "authoredOn": data.get("authoredOn"),
            "status": prior_status,
        }
        history.append(entry)

    return history


# =============================================================================
# Inferred Medication-Condition Links
# =============================================================================


async def infer_medication_condition_links(
    unlinked_meds: list[dict[str, Any]],
    graph: "KnowledgeGraph",
    patient_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Infer medication-condition links via encounter traversal.

    For medications without a direct TREATS edge, traverses:
    med -> PRESCRIBED -> encounter -> DIAGNOSED -> condition

    Args:
        unlinked_meds: List of medication dicts without TREATS edges.
        graph: KnowledgeGraph instance for traversal.
        patient_id: The canonical patient UUID string.

    Returns:
        Dict mapping condition_fhir_id to lists of medication dicts
        flagged with _inferred=True. Meds with no encounter link
        are collected under the "unlinked" key.
    """
    result: dict[str, list[dict[str, Any]]] = {}

    for med in unlinked_meds:
        med_fhir_id = med.get("id")
        if not med_fhir_id:
            result.setdefault("unlinked", []).append(med)
            continue

        # Get all connections from this medication node
        connections = await graph.get_all_connections(
            med_fhir_id, patient_id=patient_id
        )

        # Find encounters via PRESCRIBED relationship (incoming = encounter prescribed this med)
        encounter_fhir_ids = [
            c["fhir_id"]
            for c in connections
            if c["relationship"] == "PRESCRIBED"
            and c["resource_type"] == "Encounter"
        ]

        if not encounter_fhir_ids:
            result.setdefault("unlinked", []).append(med)
            continue

        # For each encounter, find conditions via DIAGNOSED relationship
        found_condition = False
        for enc_fhir_id in encounter_fhir_ids:
            enc_connections = await graph.get_all_connections(
                enc_fhir_id, patient_id=patient_id
            )

            condition_fhir_ids = [
                c["fhir_id"]
                for c in enc_connections
                if c["relationship"] == "DIAGNOSED"
                and c["resource_type"] == "Condition"
            ]

            for cond_fhir_id in condition_fhir_ids:
                med_copy = copy.deepcopy(med)
                med_copy["_inferred"] = True
                result.setdefault(cond_fhir_id, []).append(med_copy)
                found_condition = True

        if not found_condition:
            result.setdefault("unlinked", []).append(med)

    return result
