"""Compiler service for pre-computed patient summary data.

Provides functions to:
1. Fetch the latest observation per LOINC code, grouped by category
2. Compute trend metadata for numeric observations with historical data
"""

import copy
import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource

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
