"""Lab results API routes — serves full observation history for frontend display.

Returns all laboratory observations for a patient grouped by LOINC code with
full history arrays for sparkline/trend rendering. Reference range and
interpretation fields are read from FHIR data when available (populated by
the reference_ranges module at seed time); null otherwise.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_bearer_token
from app.database import get_db
from app.models import FhirResource

router = APIRouter(prefix="/patients", tags=["labs"])


def _extract_observation_fields(obs: dict[str, Any]) -> dict[str, Any] | None:
    """Extract display fields from a FHIR Observation.

    Returns None for non-numeric observations (no valueQuantity.value).
    """
    vq = obs.get("valueQuantity", {})
    value = vq.get("value")
    if value is None:
        return None

    code_obj = obs.get("code", {})
    codings = code_obj.get("coding", [])
    test_name = (
        codings[0].get("display", "Unknown") if codings else code_obj.get("text", "Unknown")
    )
    loinc_code = codings[0].get("code") if codings else None

    unit = vq.get("unit", "")
    date_str = (obs.get("effectiveDateTime") or "")[:10]

    # Reference range from FHIR data (populated at seed time by reference_ranges module)
    range_low = None
    range_high = None
    ref_range = obs.get("referenceRange", [])
    if ref_range and isinstance(ref_range, list) and len(ref_range) > 0:
        rr = ref_range[0]
        low_obj = rr.get("low", {})
        high_obj = rr.get("high", {})
        if isinstance(low_obj, dict):
            range_low = low_obj.get("value")
        if isinstance(high_obj, dict):
            range_high = high_obj.get("value")

    # HL7 interpretation from FHIR data (N/H/L/HH/LL)
    interpretation = None
    interp_list = obs.get("interpretation", [])
    if interp_list and isinstance(interp_list, list):
        interp_codings = interp_list[0].get("coding", []) if isinstance(interp_list[0], dict) else []
        if interp_codings:
            interpretation = interp_codings[0].get("code")

    return {
        "test": test_name,
        "loincCode": loinc_code,
        "value": value,
        "unit": unit,
        "rangeLow": range_low,
        "rangeHigh": range_high,
        "interpretation": interpretation,
        "date": date_str,
    }


@router.get("/{patient_id}/labs")
async def get_patient_labs(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> dict:
    """Get all laboratory observations grouped by LOINC code with full history.

    Returns data shaped for the frontend lab table: each entry is either a
    standalone result or a panel group containing multiple results. Every
    result includes its full history array for sparkline rendering.

    Reference range and interpretation fields are populated when the FHIR
    Observation contains them (added at seed time by the reference_ranges
    module). Otherwise they are null.

    Args:
        patient_id: PostgreSQL UUID of the patient.

    Returns:
        Dict with entries (list of LabEntry) and total count.
    """
    # Validate patient exists
    patient_stmt = select(FhirResource.id).where(
        FhirResource.id == patient_id,
        FhirResource.resource_type == "Patient",
    )
    patient_result = await db.execute(patient_stmt)
    if patient_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Fetch all laboratory observations, newest first
    category_expr = FhirResource.data["category"][0]["coding"][0]["code"].as_string()
    loinc_expr = FhirResource.data["code"]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Observation",
            category_expr == "laboratory",
            loinc_expr.isnot(None),
        )
        .order_by(func.cast(effective_dt, DateTime).desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Group by LOINC code (maintains desc order within each group)
    by_loinc: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        obs = row.data
        loinc = obs.get("code", {}).get("coding", [{}])[0].get("code")
        if loinc:
            by_loinc.setdefault(loinc, []).append(obs)

    # Build response entries
    entries: list[dict[str, Any]] = []
    for _loinc_code, observations in by_loinc.items():
        latest = observations[0]
        fields = _extract_observation_fields(latest)
        if fields is None:
            continue

        # Build chronological history array (oldest → newest for sparkline)
        history: list[dict[str, Any]] = []
        for obs in reversed(observations):
            obs_vq = obs.get("valueQuantity", {})
            obs_val = obs_vq.get("value")
            obs_date = (obs.get("effectiveDateTime") or "")[:10]
            if obs_val is not None:
                history.append({"value": obs_val, "date": obs_date})

        fields["history"] = history

        entries.append({
            "type": "standalone",
            "result": fields,
        })

    # Stable sort by test name
    entries.sort(key=lambda e: e["result"]["test"])

    return {
        "entries": entries,
        "total": len(entries),
    }
