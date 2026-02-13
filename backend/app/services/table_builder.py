"""Deterministic table builder service.

Transforms FHIR resources directly into frontend row schemas, bypassing the LLM.
Each builder queries patient data from Postgres and returns a ClinicalTable dict
with native Python list rows (not JSON-encoded strings).

Reuses extraction patterns from:
- routes/labs.py (lab observation grouping, reference ranges)
- services/compiler.py (condition/med extraction, trends)
- services/reference_ranges.py (interpretation, ranges)
"""

import logging
import uuid
from typing import Any

from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.reference_ranges import (
    build_fhir_interpretation,
    build_fhir_reference_range,
    interpret_component_observation,
    interpret_observation,
)

logger = logging.getLogger(__name__)

# Table type to builder function mapping (populated at module level below)
TABLE_TYPES = frozenset({
    "medications", "lab_results", "vitals", "conditions",
    "allergies", "immunizations", "procedures", "encounters",
})

# Default titles per table type
_DEFAULT_TITLES: dict[str, str] = {
    "medications": "Medications",
    "lab_results": "Lab Results",
    "vitals": "Vital Signs",
    "conditions": "Conditions",
    "allergies": "Allergies",
    "immunizations": "Immunizations",
    "procedures": "Procedures",
    "encounters": "Encounters",
}


# =============================================================================
# Helper: extract display name from CodeableConcept
# =============================================================================

def _display_name(resource: dict[str, Any], field: str = "code") -> str:
    """Extract display string from a FHIR CodeableConcept field."""
    val = resource.get(field, {})
    if isinstance(val, str):
        return val
    codings = val.get("coding", [])
    if codings:
        return codings[0].get("display", "Unknown")
    return val.get("text", "Unknown")


def _extract_status(resource: dict[str, Any], field: str = "status") -> str:
    """Extract status string, handling clinicalStatus CodeableConcept."""
    val = resource.get(field, "unknown")
    if isinstance(val, dict):
        codings = val.get("coding", [])
        return codings[0].get("code", "unknown") if codings else "unknown"
    return str(val)


# =============================================================================
# Medications
# =============================================================================

async def build_medications_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    status: str | None = None,
) -> dict[str, Any] | None:
    """Build a medications table from MedicationRequest resources."""
    conditions = [
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "MedicationRequest",
    ]
    if status:
        status_expr = FhirResource.data["status"].as_string()
        conditions.append(status_expr == status)

    authored_on = FhirResource.data["authoredOn"].as_string()
    stmt = (
        select(FhirResource.data)
        .where(*conditions)
        .order_by(func.cast(authored_on, DateTime).desc().nulls_last())
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    # Dedup by medication display name (keep newest)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for med in resources:
        med_display = _display_name(med, "medicationCodeableConcept")
        if med_display in seen:
            continue
        seen.add(med_display)

        # Extract frequency from dosageInstruction
        frequency = None
        instructions = med.get("dosageInstruction", [])
        if instructions:
            first = instructions[0]
            timing = first.get("timing", {})
            repeat = timing.get("repeat", {})
            freq = repeat.get("frequency")
            period = repeat.get("period")
            period_unit = repeat.get("periodUnit")
            if freq and period and period_unit:
                unit_map = {"d": "daily", "wk": "weekly", "mo": "monthly"}
                frequency = f"{freq}x {unit_map.get(period_unit, period_unit)}"
            elif first.get("text"):
                frequency = first["text"]

        # Extract reason from reasonCode or reasonReference
        reason = None
        reason_codes = med.get("reasonCode", [])
        if reason_codes:
            reason = _display_name({"code": reason_codes[0]})
        elif med.get("reasonReference"):
            refs = med["reasonReference"]
            if isinstance(refs, list) and refs:
                ref = refs[0]
                reason = ref.get("display") if isinstance(ref, dict) else str(ref)

        # Extract requester
        requester = None
        req = med.get("requester", {})
        if isinstance(req, dict):
            requester = req.get("display")
        elif isinstance(req, str):
            requester = req

        rows.append({
            "medication": med_display,
            "frequency": frequency,
            "reason": reason,
            "status": _extract_status(med),
            "authoredOn": (med.get("authoredOn") or "")[:10],
            "requester": requester,
        })

    title = "Active Medications" if status == "active" else _DEFAULT_TITLES["medications"]
    return {"type": "medications", "title": title, "rows": rows}


# =============================================================================
# Lab Results
# =============================================================================

async def build_lab_results_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    codes: list[str] | None = None,
    panel: str | None = None,
) -> dict[str, Any] | None:
    """Build a lab results table from Observation resources (category=laboratory)."""
    category_expr = FhirResource.data["category"][0]["coding"][0]["code"].as_string()
    loinc_expr = FhirResource.data["code"]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    conditions = [
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Observation",
        category_expr == "laboratory",
        loinc_expr.isnot(None),
    ]

    if codes:
        conditions.append(loinc_expr.in_(codes))

    stmt = (
        select(FhirResource.data)
        .where(*conditions)
        .order_by(func.cast(effective_dt, DateTime).desc())
    )
    result = await db.execute(stmt)
    all_obs = [row.data for row in result.all()]

    if not all_obs:
        return None

    # Group by LOINC code, build latest + history
    by_loinc: dict[str, list[dict[str, Any]]] = {}
    for obs in all_obs:
        loinc = obs.get("code", {}).get("coding", [{}])[0].get("code")
        if loinc:
            by_loinc.setdefault(loinc, []).append(obs)

    rows: list[dict[str, Any]] = []
    for _loinc_code, observations in by_loinc.items():
        latest = observations[0]
        vq = latest.get("valueQuantity", {})
        value = vq.get("value")
        if value is None:
            continue

        code_obj = latest.get("code", {})
        codings = code_obj.get("coding", [])
        test_name = codings[0].get("display", "Unknown") if codings else code_obj.get("text", "Unknown")
        unit = vq.get("unit", "")
        date_str = (latest.get("effectiveDateTime") or "")[:10]

        # Reference range
        range_low = None
        range_high = None
        ref_range = latest.get("referenceRange", [])
        if ref_range and isinstance(ref_range, list) and len(ref_range) > 0:
            rr = ref_range[0]
            low_obj = rr.get("low", {})
            high_obj = rr.get("high", {})
            if isinstance(low_obj, dict):
                range_low = low_obj.get("value")
            if isinstance(high_obj, dict):
                range_high = high_obj.get("value")

        # Interpretation
        interpretation = "N"
        interp_list = latest.get("interpretation", [])
        if interp_list and isinstance(interp_list, list):
            interp_codings = interp_list[0].get("coding", []) if isinstance(interp_list[0], dict) else []
            if interp_codings:
                interpretation = interp_codings[0].get("code", "N")

        # Runtime interpretation fallback
        if interpretation == "N" and (range_low is None or range_high is None):
            interp_code, ref_range_tuple = interpret_observation(latest)
            if interp_code and ref_range_tuple:
                interpretation = interp_code
                range_low, range_high = ref_range_tuple

        # Build history (oldest → newest for sparkline)
        history: list[dict[str, Any]] = []
        for obs in reversed(observations):
            obs_vq = obs.get("valueQuantity", {})
            obs_val = obs_vq.get("value")
            obs_date = (obs.get("effectiveDateTime") or "")[:10]
            if obs_val is not None:
                history.append({"value": obs_val, "date": obs_date})

        rows.append({
            "test": test_name,
            "value": value,
            "unit": unit,
            "rangeLow": range_low,
            "rangeHigh": range_high,
            "interpretation": interpretation,
            "date": date_str,
            "history": history,
            "panel": panel,
        })

    # Sort by test name
    rows.sort(key=lambda r: r["test"])

    if not rows:
        return None

    return {"type": "lab_results", "title": _DEFAULT_TITLES["lab_results"], "rows": rows}


# =============================================================================
# Vitals
# =============================================================================

async def build_vitals_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build a vitals table from Observation resources (category=vital-signs)."""
    category_expr = FhirResource.data["category"][0]["coding"][0]["code"].as_string()
    loinc_expr = FhirResource.data["code"]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Observation",
            category_expr == "vital-signs",
            loinc_expr.isnot(None),
        )
        .order_by(func.cast(effective_dt, DateTime).desc())
    )
    result = await db.execute(stmt)
    all_obs = [row.data for row in result.all()]

    if not all_obs:
        return None

    # Group by LOINC code
    by_loinc: dict[str, list[dict[str, Any]]] = {}
    for obs in all_obs:
        loinc = obs.get("code", {}).get("coding", [{}])[0].get("code")
        if loinc:
            by_loinc.setdefault(loinc, []).append(obs)

    # LOINC codes with clinical ranges (display ranges/history for these)
    _RANGED_LOINCS = {
        "85354-9",   # Blood pressure
        "8867-4",    # Heart rate
        "9279-1",    # Respiratory rate
        "39156-5",   # BMI
        "8310-5",    # Body temperature
    }

    rows: list[dict[str, Any]] = []
    for loinc_code, observations in by_loinc.items():
        latest = observations[0]
        code_obj = latest.get("code", {})
        codings = code_obj.get("coding", [])
        vital_name = codings[0].get("display", "Unknown") if codings else "Unknown"

        # Handle BP specially (component observation)
        if loinc_code == "85354-9":
            components = latest.get("component", [])
            sys_val = dia_val = None
            for comp in components:
                comp_code = comp.get("code", {}).get("coding", [{}])[0].get("code")
                comp_vq = comp.get("valueQuantity", {})
                if comp_code == "8480-6":  # Systolic
                    sys_val = comp_vq.get("value")
                elif comp_code == "8462-4":  # Diastolic
                    dia_val = comp_vq.get("value")

            value_display = f"{sys_val}/{dia_val}" if sys_val and dia_val else str(sys_val or dia_val or "")
            numeric_value = sys_val

            # Interpret BP components
            interpretation = None
            range_low = None
            range_high = None
            if sys_val is not None:
                # Use component interpretation
                interpret_component_observation(latest)
                interp_list = latest.get("interpretation", [])
                if interp_list and isinstance(interp_list, list):
                    interp_codings = interp_list[0].get("coding", []) if isinstance(interp_list[0], dict) else []
                    if interp_codings:
                        interpretation = interp_codings[0].get("code")

            # BP history
            history: list[dict[str, Any]] = []
            for obs in reversed(observations):
                obs_comps = obs.get("component", [])
                for comp in obs_comps:
                    if comp.get("code", {}).get("coding", [{}])[0].get("code") == "8480-6":
                        obs_sys = comp.get("valueQuantity", {}).get("value")
                        obs_date = (obs.get("effectiveDateTime") or "")[:10]
                        if obs_sys is not None:
                            history.append({"value": obs_sys, "date": obs_date})

            rows.append({
                "vital": vital_name,
                "value": value_display,
                "numericValue": numeric_value,
                "unit": "mmHg",
                "loinc": loinc_code,
                "date": (latest.get("effectiveDateTime") or "")[:10],
                "history": history if loinc_code in _RANGED_LOINCS else [],
                "rangeLow": range_low,
                "rangeHigh": range_high,
                "interpretation": interpretation,
            })
        else:
            # Standard vital
            vq = latest.get("valueQuantity", {})
            value = vq.get("value")
            if value is None:
                continue

            unit = vq.get("unit", "")
            date_str = (latest.get("effectiveDateTime") or "")[:10]

            # Reference range + interpretation
            range_low = None
            range_high = None
            interpretation = None

            ref_range_list = latest.get("referenceRange", [])
            if ref_range_list and isinstance(ref_range_list, list):
                rr = ref_range_list[0]
                low_obj = rr.get("low", {})
                high_obj = rr.get("high", {})
                if isinstance(low_obj, dict):
                    range_low = low_obj.get("value")
                if isinstance(high_obj, dict):
                    range_high = high_obj.get("value")

            interp_list = latest.get("interpretation", [])
            if interp_list and isinstance(interp_list, list):
                interp_codings = interp_list[0].get("coding", []) if isinstance(interp_list[0], dict) else []
                if interp_codings:
                    interpretation = interp_codings[0].get("code")

            # Runtime interpretation fallback
            if interpretation is None and loinc_code in _RANGED_LOINCS:
                interp_code, ref_range_tuple = interpret_observation(latest)
                if interp_code and ref_range_tuple:
                    interpretation = interp_code
                    range_low, range_high = ref_range_tuple

            # History (only for ranged vitals)
            history = []
            if loinc_code in _RANGED_LOINCS:
                for obs in reversed(observations):
                    obs_vq = obs.get("valueQuantity", {})
                    obs_val = obs_vq.get("value")
                    obs_date = (obs.get("effectiveDateTime") or "")[:10]
                    if obs_val is not None:
                        history.append({"value": obs_val, "date": obs_date})

            rows.append({
                "vital": vital_name,
                "value": str(value),
                "numericValue": value,
                "unit": unit,
                "loinc": loinc_code,
                "date": date_str,
                "history": history,
                "rangeLow": range_low,
                "rangeHigh": range_high,
                "interpretation": interpretation,
            })

    if not rows:
        return None

    return {"type": "vitals", "title": _DEFAULT_TITLES["vitals"], "rows": rows}


# =============================================================================
# Conditions
# =============================================================================

async def build_conditions_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    status: str | None = None,
) -> dict[str, Any] | None:
    """Build a conditions table from Condition resources."""
    clinical_status_expr = FhirResource.data["clinicalStatus"]["coding"][0]["code"].as_string()

    conditions = [
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Condition",
    ]
    if status:
        conditions.append(clinical_status_expr == status)

    onset_expr = FhirResource.data["onsetDateTime"].as_string()
    stmt = (
        select(FhirResource.data)
        .where(*conditions)
        .order_by(func.cast(onset_expr, DateTime).desc().nulls_last())
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    rows: list[dict[str, Any]] = []
    for cond in resources:
        rows.append({
            "condition": _display_name(cond),
            "clinicalStatus": _extract_status(cond, "clinicalStatus"),
            "onsetDate": (cond.get("onsetDateTime") or "")[:10],
            "abatementDate": (cond.get("abatementDateTime") or "")[:10] or None,
        })

    title = "Active Conditions" if status == "active" else _DEFAULT_TITLES["conditions"]
    return {"type": "conditions", "title": title, "rows": rows}


# =============================================================================
# Allergies
# =============================================================================

async def build_allergies_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build an allergies table from AllergyIntolerance resources."""
    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "AllergyIntolerance",
        )
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    rows: list[dict[str, Any]] = []
    for allergy in resources:
        categories = allergy.get("category", [])
        category = categories[0] if isinstance(categories, list) and categories else (
            categories if isinstance(categories, str) else None
        )

        rows.append({
            "allergen": _display_name(allergy),
            "category": category,
            "criticality": allergy.get("criticality", "low"),
            "clinicalStatus": _extract_status(allergy, "clinicalStatus"),
            "onsetDate": (allergy.get("onsetDateTime") or "")[:10] or None,
        })

    # Sort high criticality first
    rows.sort(key=lambda r: 0 if r["criticality"] == "high" else 1)

    return {"type": "allergies", "title": _DEFAULT_TITLES["allergies"], "rows": rows}


# =============================================================================
# Immunizations
# =============================================================================

async def build_immunizations_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build an immunizations table from Immunization resources."""
    occurrence_dt = FhirResource.data["occurrenceDateTime"].as_string()
    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Immunization",
        )
        .order_by(func.cast(occurrence_dt, DateTime).desc().nulls_last())
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    # Dedup by vaccine code
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for imm in resources:
        vaccine_name = _display_name(imm, "vaccineCode")
        if vaccine_name in seen:
            continue
        seen.add(vaccine_name)

        # Extract location from encounter or performer
        location = None
        performer_list = imm.get("performer", [])
        if performer_list:
            actor = performer_list[0].get("actor", {})
            location = actor.get("display") if isinstance(actor, dict) else str(actor)

        rows.append({
            "vaccine": vaccine_name,
            "date": (imm.get("occurrenceDateTime") or "")[:10],
            "location": location,
        })

    return {"type": "immunizations", "title": _DEFAULT_TITLES["immunizations"], "rows": rows}


# =============================================================================
# Procedures
# =============================================================================

async def build_procedures_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build a procedures table from Procedure resources."""
    performed_dt = FhirResource.data["performedDateTime"].as_string()
    performed_period = FhirResource.data["performedPeriod"]["start"].as_string()

    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Procedure",
        )
        .order_by(
            func.coalesce(
                func.cast(performed_dt, DateTime),
                func.cast(performed_period, DateTime),
            ).desc().nulls_last()
        )
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    rows: list[dict[str, Any]] = []
    for proc in resources:
        # Date: performedDateTime or performedPeriod.start
        date_str = proc.get("performedDateTime") or ""
        if not date_str:
            period = proc.get("performedPeriod", {})
            date_str = period.get("start", "") if isinstance(period, dict) else ""

        # Location
        location = None
        loc = proc.get("location", {})
        if isinstance(loc, dict):
            location = loc.get("display")

        # Reason
        reason = None
        reason_codes = proc.get("reasonCode", [])
        if reason_codes:
            reason = _display_name({"code": reason_codes[0]})
        elif proc.get("reasonReference"):
            refs = proc["reasonReference"]
            if isinstance(refs, list) and refs:
                ref = refs[0]
                reason = ref.get("display") if isinstance(ref, dict) else str(ref)

        rows.append({
            "procedure": _display_name(proc),
            "date": date_str[:10],
            "location": location,
            "reason": reason,
        })

    return {"type": "procedures", "title": _DEFAULT_TITLES["procedures"], "rows": rows}


# =============================================================================
# Encounters
# =============================================================================

async def build_encounters_table(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build an encounters table from Encounter resources."""
    period_start = FhirResource.data["period"]["start"].as_string()

    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "Encounter",
        )
        .order_by(func.cast(period_start, DateTime).desc().nulls_last())
    )
    result = await db.execute(stmt)
    resources = [row.data for row in result.all()]

    if not resources:
        return None

    rows: list[dict[str, Any]] = []
    for enc in resources:
        # Type
        enc_types = enc.get("type", [])
        type_display = "Unknown"
        if enc_types and isinstance(enc_types, list):
            first_type = enc_types[0]
            if isinstance(first_type, dict):
                type_display = _display_name({"code": first_type})
            elif isinstance(first_type, str):
                type_display = first_type

        # Class
        enc_class = enc.get("class", {})
        class_code = enc_class.get("code", "AMB") if isinstance(enc_class, dict) else str(enc_class)

        # Date
        period = enc.get("period", {})
        date_str = ""
        if isinstance(period, dict):
            date_str = (period.get("start") or "")[:10]

        # Provider from participant
        provider = None
        participants = enc.get("participant", [])
        if participants:
            for p in participants:
                individual = p.get("individual", {})
                if isinstance(individual, dict):
                    provider = individual.get("display")
                    if provider:
                        break

        # Location
        location = None
        locations = enc.get("location", [])
        if locations:
            loc = locations[0].get("location", {})
            if isinstance(loc, dict):
                location = loc.get("display")

        # Reason
        reason = None
        reason_codes = enc.get("reasonCode", [])
        if reason_codes:
            reason = _display_name({"code": reason_codes[0]})

        rows.append({
            "type": type_display,
            "encounterClass": class_code.upper() if class_code else "AMB",
            "date": date_str,
            "provider": provider,
            "location": location,
            "reason": reason,
        })

    return {"type": "encounters", "title": _DEFAULT_TITLES["encounters"], "rows": rows}


# =============================================================================
# Dispatcher
# =============================================================================

_BUILDERS: dict[str, Any] = {
    "medications": build_medications_table,
    "lab_results": build_lab_results_table,
    "vitals": build_vitals_table,
    "conditions": build_conditions_table,
    "allergies": build_allergies_table,
    "immunizations": build_immunizations_table,
    "procedures": build_procedures_table,
    "encounters": build_encounters_table,
}


async def build_table_for_type(
    table_type: str,
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    status: str | None = None,
    codes: list[str] | None = None,
    panel: str | None = None,
) -> dict[str, Any] | None:
    """Build a clinical table by type, dispatching to the appropriate builder.

    Args:
        table_type: One of TABLE_TYPES (e.g. "medications", "lab_results").
        patient_id: Patient UUID.
        db: Async database session.
        status: Optional status filter (for medications, conditions).
        codes: Optional LOINC codes filter (for labs).
        panel: Optional panel name (for lab grouping).

    Returns:
        ClinicalTable dict with type, title, and rows, or None if no data.
    """
    builder = _BUILDERS.get(table_type)
    if builder is None:
        logger.warning("Unknown table type: %s", table_type)
        return None

    # Pass optional kwargs only to builders that accept them
    if table_type == "medications":
        return await builder(patient_id, db, status=status)
    elif table_type == "lab_results":
        return await builder(patient_id, db, codes=codes, panel=panel)
    elif table_type == "conditions":
        return await builder(patient_id, db, status=status)
    else:
        return await builder(patient_id, db)
