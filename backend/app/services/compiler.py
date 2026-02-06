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
9. Compile full patient summary (12-step assembly pipeline)
"""

import copy
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
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


# =============================================================================
# Patient Summary Compilation Pipeline
# =============================================================================

# Status filters
_ACTIVE_CONDITION_STATUSES = frozenset(["active", "recurrence", "relapse"])
_RESOLVED_CONDITION_STATUSES = frozenset(["resolved", "remission", "inactive"])
_ACTIVE_CARE_PLAN_STATUSES = frozenset(["active", "on-hold"])
_RECENTLY_RESOLVED_MONTHS = 6

# Maps encounter event keys (from graph) to relationship type labels in the summary
_EVENT_TYPE_MAP: dict[str, str] = {
    "conditions": "DIAGNOSED",
    "medications": "PRESCRIBED",
    "observations": "RECORDED",
    "procedures": "PERFORMED",
    "diagnostic_reports": "REPORTED",
    "immunizations": "ADMINISTERED",
    "care_plans": "CREATED_DURING",
    "document_references": "DOCUMENTED",
    "imaging_studies": "IMAGED",
    "care_teams": "ASSEMBLED",
    "medication_administrations": "GIVEN",
}


def _build_patient_orientation(patient_data: dict[str, Any], compilation_date: date) -> str:
    """Build a narrative orientation string from a Patient FHIR resource.

    Args:
        patient_data: FHIR Patient resource dict.
        compilation_date: Date the summary is compiled.

    Returns:
        Narrative string like "John Smith, Male, DOB 1985-03-15 (age 40)".
    """
    names = patient_data.get("name", [])
    if names:
        first_name = names[0]
        given = " ".join(first_name.get("given", []))
        family = first_name.get("family", "")
        full_name = f"{given} {family}".strip()
    else:
        full_name = "Unknown"

    gender = patient_data.get("gender", "unknown")
    birth_date_str = patient_data.get("birthDate", "")

    age_str = ""
    if birth_date_str:
        try:
            birth_date = datetime.fromisoformat(birth_date_str).date()
            age = (
                compilation_date.year - birth_date.year
                - ((compilation_date.month, compilation_date.day) < (birth_date.month, birth_date.day))
            )
            age_str = f" (age {age})"
        except (ValueError, TypeError):
            pass

    parts = [full_name]
    if gender != "unknown":
        parts.append(gender.capitalize())
    if birth_date_str:
        parts.append(f"DOB {birth_date_str}{age_str}")

    return ", ".join(parts)


def _extract_fhir_id(resource: dict[str, Any]) -> str:
    """Extract the FHIR id from a resource dict."""
    return resource.get("id", "")


async def _fetch_recently_resolved_conditions(
    db: AsyncSession,
    patient_id: uuid.UUID,
    compilation_date: date,
) -> list[dict[str, Any]]:
    """Fetch conditions resolved/remission/inactive within the last 6 months.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.
        compilation_date: Date to compute the 6-month window from.

    Returns:
        List of FHIR Condition dicts.
    """
    cutoff = compilation_date - timedelta(days=_RECENTLY_RESOLVED_MONTHS * 30)
    cutoff_dt = datetime(cutoff.year, cutoff.month, cutoff.day)

    clinical_status_expr = FhirResource.data["clinicalStatus"]["coding"][0]["code"].as_string()
    abatement_expr = FhirResource.data["abatementDateTime"].as_string()

    query = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Condition",
            clinical_status_expr.in_(_RESOLVED_CONDITION_STATUSES),
            abatement_expr.isnot(None),
            func.cast(abatement_expr, DateTime) >= cutoff_dt,
        )
    )

    result = await db.execute(query)
    return [row.data for row in result.all()]


async def _fetch_active_care_plans(
    db: AsyncSession,
    patient_id: uuid.UUID,
) -> list[dict[str, Any]]:
    """Fetch active/on-hold care plans from Postgres.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.

    Returns:
        List of FHIR CarePlan dicts.
    """
    status_expr = FhirResource.data["status"].as_string()

    query = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "CarePlan",
            status_expr.in_(_ACTIVE_CARE_PLAN_STATUSES),
        )
    )

    result = await db.execute(query)
    return [row.data for row in result.all()]


async def _fetch_encounter_fhir_resources(
    db: AsyncSession,
    patient_id: uuid.UUID,
    encounter_fhir_ids: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch full FHIR Encounter resources from Postgres.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.
        encounter_fhir_ids: List of encounter FHIR IDs.

    Returns:
        Dict mapping fhir_id to FHIR Encounter resource data.
    """
    if not encounter_fhir_ids:
        return {}

    query = select(FhirResource.fhir_id, FhirResource.data).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Encounter",
        FhirResource.fhir_id.in_(encounter_fhir_ids),
    )

    result = await db.execute(query)
    return {row.fhir_id: row.data for row in result.all()}


async def compile_patient_summary(
    patient_id: uuid.UUID | str,
    graph: KnowledgeGraph,
    db: AsyncSession,
    compilation_date: date | None = None,
) -> dict[str, Any]:
    """Compile a full patient summary via 12-step assembly pipeline.

    Assembles a structured summary containing:
    - Patient orientation narrative
    - Tier 1: Active conditions with treating meds/care plans/procedures,
              recently resolved conditions, unlinked medications, allergies,
              immunizations, standalone care plans
    - Tier 2: Recent encounters with events and clinical notes
    - Tier 3: Latest observations by category with trends
    - Safety constraints derived from Tier 1

    Args:
        patient_id: The canonical patient UUID.
        graph: KnowledgeGraph instance for traversal.
        db: Async SQLAlchemy session.
        compilation_date: Date to compile against. Defaults to today.

    Returns:
        Complete patient summary dict.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    if compilation_date is None:
        compilation_date = date.today()

    patient_id_str = str(patient_id)

    # =========================================================================
    # Step 1: Patient orientation narrative
    # =========================================================================
    patient_query = select(FhirResource.data).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Patient",
    )
    patient_result = await db.execute(patient_query)
    patient_row = patient_result.first()
    patient_data = patient_row.data if patient_row else {}
    patient_orientation = _build_patient_orientation(patient_data, compilation_date)

    # =========================================================================
    # Step 2: Tier 1 — active conditions, meds, allergies, care plans, immunizations
    # =========================================================================
    active_conditions = await graph.get_verified_conditions(patient_id_str)
    active_meds_raw = await graph.get_verified_medications(patient_id_str)
    allergies_raw = await graph.get_verified_allergies(patient_id_str)
    immunizations_raw = await graph.get_verified_immunizations(patient_id_str)
    recently_resolved_raw = await _fetch_recently_resolved_conditions(
        db, patient_id, compilation_date
    )
    care_plans_raw = await _fetch_active_care_plans(db, patient_id)

    # For each active condition, compile_node_context to get treating meds,
    # care plans, procedures
    tier1_active_conditions: list[dict[str, Any]] = []
    condition_linked_med_ids: set[str] = set()
    condition_linked_cp_ids: set[str] = set()

    for condition in active_conditions:
        cond_fhir_id = _extract_fhir_id(condition)
        if not cond_fhir_id:
            continue

        # Get treating meds, care plans, procedures via graph
        treating_meds = await graph.get_medications_treating_condition(cond_fhir_id)
        care_plans = await graph.get_care_plans_for_condition(cond_fhir_id)
        procedures = await graph.get_procedures_for_condition(cond_fhir_id)

        # Track linked med/care-plan IDs for dedup
        for med in treating_meds:
            mid = _extract_fhir_id(med)
            if mid:
                condition_linked_med_ids.add(mid)
        for cp in care_plans:
            cpid = _extract_fhir_id(cp)
            if cpid:
                condition_linked_cp_ids.add(cpid)

        tier1_active_conditions.append({
            "condition": prune_and_enrich(condition),
            "treating_medications": [prune_and_enrich(m) for m in treating_meds],
            "care_plans": [prune_and_enrich(cp) for cp in care_plans],
            "related_procedures": [prune_and_enrich(p) for p in procedures],
        })

    # Recently resolved conditions (same structure)
    tier1_recently_resolved: list[dict[str, Any]] = []
    for condition in recently_resolved_raw:
        cond_fhir_id = _extract_fhir_id(condition)
        if not cond_fhir_id:
            continue

        treating_meds = await graph.get_medications_treating_condition(cond_fhir_id)
        care_plans = await graph.get_care_plans_for_condition(cond_fhir_id)
        procedures = await graph.get_procedures_for_condition(cond_fhir_id)

        for med in treating_meds:
            mid = _extract_fhir_id(med)
            if mid:
                condition_linked_med_ids.add(mid)
        for cp in care_plans:
            cpid = _extract_fhir_id(cp)
            if cpid:
                condition_linked_cp_ids.add(cpid)

        tier1_recently_resolved.append({
            "condition": prune_and_enrich(condition),
            "treating_medications": [prune_and_enrich(m) for m in treating_meds],
            "care_plans": [prune_and_enrich(cp) for cp in care_plans],
            "related_procedures": [prune_and_enrich(p) for p in procedures],
        })

    # =========================================================================
    # Step 3: Encounter-inferred medication links for unlinked meds
    # =========================================================================
    unlinked_meds = [
        m for m in active_meds_raw
        if _extract_fhir_id(m) not in condition_linked_med_ids
    ]

    inferred_links: dict[str, list[dict[str, Any]]] = {}
    if unlinked_meds:
        inferred_links = await infer_medication_condition_links(
            unlinked_meds, graph, patient_id_str
        )

    # Merge inferred links into active conditions
    for cond_entry in tier1_active_conditions:
        cond_id = cond_entry["condition"].get("id", "")
        if cond_id in inferred_links:
            for med in inferred_links[cond_id]:
                cond_entry["treating_medications"].append(prune_and_enrich(med))
                mid = _extract_fhir_id(med)
                if mid:
                    condition_linked_med_ids.add(mid)

    # Truly unlinked meds (no condition link at all)
    truly_unlinked = inferred_links.get("unlinked", [])

    # =========================================================================
    # Step 4: Medication recency + dose history for all active meds
    # =========================================================================
    # Build lookup for raw meds by fhir_id (avoids O(n) scan per med)
    raw_meds_by_id: dict[str, dict[str, Any]] = {
        _extract_fhir_id(m): m for m in active_meds_raw if _extract_fhir_id(m)
    }

    # Build enriched meds for tier1 conditions
    for cond_entry in tier1_active_conditions:
        enriched_meds = []
        for med_pruned in cond_entry["treating_medications"]:
            recency = compute_medication_recency(med_pruned, compilation_date)
            if recency:
                med_pruned.update(recency)
            # Dose history requires DB query on raw data
            med_fhir_id = med_pruned.get("id", "")
            raw_med = raw_meds_by_id.get(med_fhir_id)
            if raw_med:
                dose_history = await compute_dose_history(db, patient_id, raw_med)
                if dose_history:
                    med_pruned["_dose_history"] = dose_history
            enriched_meds.append(med_pruned)
        cond_entry["treating_medications"] = enriched_meds

    # Enrich unlinked meds
    enriched_unlinked: list[dict[str, Any]] = []
    for med in truly_unlinked:
        pruned = prune_and_enrich(med)
        recency = compute_medication_recency(med, compilation_date)
        if recency:
            pruned.update(recency)
        dose_history = await compute_dose_history(db, patient_id, med)
        if dose_history:
            pruned["_dose_history"] = dose_history
        enriched_unlinked.append(pruned)

    # =========================================================================
    # Step 5: Tier 2 — recent encounters with events and clinical notes
    # =========================================================================
    six_months_ago = (compilation_date - timedelta(days=180)).isoformat()

    # Get encounters sorted by date desc from graph
    all_encounters = await graph.get_patient_encounters(patient_id_str)

    # Fetch full encounter FHIR resources for recent window + last encounter
    recent_enc_ids = []
    for enc in all_encounters:
        period_start = enc.get("period_start", "")
        if period_start and period_start >= six_months_ago:
            recent_enc_ids.append(enc["fhir_id"])

    # Ensure we have at least the most recent encounter
    if all_encounters and all_encounters[0]["fhir_id"] not in recent_enc_ids:
        recent_enc_ids.insert(0, all_encounters[0]["fhir_id"])

    encounter_resources = await _fetch_encounter_fhir_resources(
        db, patient_id, recent_enc_ids
    )

    # Find the last AMB encounter, fall back to any class
    last_amb_fhir_id = None
    for enc_fhir_id in recent_enc_ids:
        enc_data = encounter_resources.get(enc_fhir_id, {})
        class_code = enc_data.get("class", {}).get("code", "")
        if class_code == "AMB":
            last_amb_fhir_id = enc_fhir_id
            break

    if not last_amb_fhir_id and recent_enc_ids:
        last_amb_fhir_id = recent_enc_ids[0]

    # Build Tier 2 encounter list (ordered by date desc)
    tier2_enc_fhir_ids = []
    if last_amb_fhir_id:
        tier2_enc_fhir_ids.append(last_amb_fhir_id)
    for enc_id in recent_enc_ids:
        if enc_id != last_amb_fhir_id and enc_id not in tier2_enc_fhir_ids:
            tier2_enc_fhir_ids.append(enc_id)

    tier2_encounters: list[dict[str, Any]] = []
    tier2_resource_fhir_ids: set[str] = set()

    for enc_fhir_id in tier2_enc_fhir_ids:
        enc_data = encounter_resources.get(enc_fhir_id)
        if not enc_data:
            continue

        # Get encounter events via graph
        events = await graph.get_encounter_events(enc_fhir_id)

        # Track all resource IDs from events for dedup
        for event_list in events.values():
            for event_resource in event_list:
                eid = _extract_fhir_id(event_resource)
                if eid:
                    tier2_resource_fhir_ids.add(eid)

        # Compile events into pruned format grouped by relationship type
        pruned_events: dict[str, list[dict[str, Any]]] = {}

        for event_key, rel_type in _EVENT_TYPE_MAP.items():
            event_resources = events.get(event_key, [])
            if event_resources:
                pruned_events[rel_type] = [
                    prune_and_enrich(r) for r in event_resources
                ]

        # Clinical notes: reuse already-pruned document_references from events
        clinical_notes: list[str] = []
        for pruned_doc in pruned_events.get("DOCUMENTED", []):
            note = pruned_doc.get("clinical_note")
            if note:
                clinical_notes.append(note)

        tier2_encounters.append({
            "encounter": prune_and_enrich(enc_data),
            "events": pruned_events,
            "clinical_notes": clinical_notes,
        })

    # =========================================================================
    # Step 6: Tier 3 — latest observations by category
    # =========================================================================
    tier3_raw = await get_latest_observations_by_category(db, patient_id)

    # =========================================================================
    # Step 7: Observation trends
    # =========================================================================
    all_tier3_obs: list[dict[str, Any]] = []
    for obs_list in tier3_raw.values():
        all_tier3_obs.extend(obs_list)

    enriched_obs = await compute_observation_trends(db, patient_id, all_tier3_obs)

    # Rebuild tier3 with trends by category
    enriched_obs_by_id: dict[str, dict[str, Any]] = {}
    for obs in enriched_obs:
        oid = _extract_fhir_id(obs)
        if oid:
            enriched_obs_by_id[oid] = obs

    # =========================================================================
    # Step 8: Dedup Tier 3 vs Tier 2 by fhir_id
    # =========================================================================
    tier3_by_category: dict[str, list[dict[str, Any]]] = {
        cat: [] for cat in OBSERVATION_CATEGORIES
    }
    for cat, obs_list in tier3_raw.items():
        for obs in obs_list:
            obs_id = _extract_fhir_id(obs)
            if obs_id and obs_id in tier2_resource_fhir_ids:
                continue  # Already in Tier 2
            enriched = enriched_obs_by_id.get(obs_id, obs)
            tier3_by_category[cat].append(prune_and_enrich(enriched))

    # =========================================================================
    # Step 9: Dedup Tier 2 vs Tier 1 (meds only — condition-level takes precedence)
    # =========================================================================
    for enc_entry in tier2_encounters:
        prescribed = enc_entry["events"].get("PRESCRIBED", [])
        if prescribed:
            enc_entry["events"]["PRESCRIBED"] = [
                m for m in prescribed
                if m.get("id", "") not in condition_linked_med_ids
            ]

    # =========================================================================
    # Step 10: Safety constraints
    # =========================================================================
    safety_allergies = [prune_and_enrich(a) for a in allergies_raw]
    safety_constraints: dict[str, Any] = {
        "active_allergies": safety_allergies if safety_allergies else [{"note": "None recorded"}],
        "drug_interactions_note": "Review active medications for potential interactions.",
    }

    # =========================================================================
    # Step 11: Prune + enrich remaining resources
    # =========================================================================
    tier1_allergies = safety_allergies if safety_allergies else [{"note": "None recorded"}]
    tier1_immunizations = [prune_and_enrich(im) for im in immunizations_raw]

    # Standalone care plans not linked to any condition
    tier1_care_plans = [
        prune_and_enrich(cp) for cp in care_plans_raw
        if _extract_fhir_id(cp) not in condition_linked_cp_ids
    ]

    # =========================================================================
    # Step 12: Assemble final summary
    # =========================================================================
    summary: dict[str, Any] = {
        "patient_orientation": patient_orientation,
        "compilation_date": compilation_date.isoformat(),
        "tier1_active_conditions": tier1_active_conditions,
    }

    if tier1_recently_resolved:
        summary["tier1_recently_resolved"] = tier1_recently_resolved

    summary["tier1_unlinked_medications"] = enriched_unlinked
    summary["tier1_allergies"] = tier1_allergies
    summary["tier1_immunizations"] = tier1_immunizations
    summary["tier1_care_plans"] = tier1_care_plans
    summary["tier2_recent_encounters"] = tier2_encounters
    summary["tier3_latest_observations"] = tier3_by_category
    summary["safety_constraints"] = safety_constraints

    return summary


# =============================================================================
# Compilation Storage
# =============================================================================


async def compile_and_store(
    patient_id: uuid.UUID | str,
    graph: KnowledgeGraph,
    db: AsyncSession,
) -> dict[str, Any]:
    """Compile a patient summary and persist it to the Patient FhirResource row.

    Calls compile_patient_summary, then writes the result to the
    compiled_summary JSONB column and sets compiled_at on the Patient's
    FhirResource row.

    Args:
        patient_id: The canonical patient UUID.
        graph: KnowledgeGraph instance for traversal.
        db: Async SQLAlchemy session.

    Returns:
        The compiled summary dict.

    Raises:
        ValueError: If no Patient FhirResource exists for the given ID.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    summary = await compile_patient_summary(patient_id, graph, db)

    # Fetch the Patient FhirResource row
    result = await db.execute(
        select(FhirResource).where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Patient",
        )
    )
    patient_row = result.scalar_one_or_none()
    if patient_row is None:
        raise ValueError(f"No Patient FhirResource found for patient_id={patient_id}")

    patient_row.compiled_summary = summary
    patient_row.compiled_at = datetime.now(timezone.utc)

    logger.info("Compiled and stored summary for patient %s", patient_id)
    return summary


async def get_compiled_summary(
    db: AsyncSession,
    patient_id: uuid.UUID | str,
) -> dict[str, Any] | None:
    """Read a previously stored compiled patient summary.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.

    Returns:
        The compiled summary dict, or None if not yet compiled.
    """
    if isinstance(patient_id, str):
        patient_id = uuid.UUID(patient_id)

    result = await db.execute(
        select(FhirResource.compiled_summary).where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Patient",
        )
    )
    row = result.first()
    if row is None:
        return None
    return row.compiled_summary
