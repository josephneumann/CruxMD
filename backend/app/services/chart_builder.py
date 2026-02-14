"""Deterministic chart builder service.

Transforms FHIR resources directly into frontend visualization schemas,
bypassing the LLM. Each builder queries patient data from Postgres and
returns a ClinicalVisualization dict (or None if no data).

Mirrors patterns from:
- services/table_builder.py (FHIR resource queries, helper utilities)
- services/reference_ranges.py (interpretation, clinical ranges)
- routes/labs.py (lab observation grouping)
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.reference_ranges import (
    REFERENCE_RANGES,
    get_reference_range,
    interpret_observation,
)

logger = logging.getLogger(__name__)

# Chart type to builder function mapping (populated at module level below)
CHART_TYPES = frozenset({"trend_chart", "encounter_timeline"})

# Friendly display names for common lab LOINCs
_LAB_DISPLAY_NAMES: dict[str, str] = {
    "2093-3": "Total Cholesterol",
    "18262-6": "LDL Cholesterol",
    "13457-7": "LDL Cholesterol",
    "2085-9": "HDL Cholesterol",
    "2571-8": "Triglycerides",
    "4548-4": "HbA1c",
    "33914-3": "eGFR",
    "69405-9": "eGFR",
    "2160-0": "Creatinine",
    "3094-0": "BUN",
    "2345-7": "Glucose",
    "14749-6": "Fasting Glucose",
    "718-7": "Hemoglobin",
    "4544-3": "Hematocrit",
    "6690-2": "WBC",
    "789-8": "RBC",
    "777-3": "Platelets",
    "39156-5": "BMI",
    "29463-7": "Body Weight",
    "8302-2": "Body Height",
    "8867-4": "Heart Rate",
    "9279-1": "Respiratory Rate",
    "8310-5": "Body Temperature",
    "85354-9": "Blood Pressure",
    "8480-6": "Systolic BP",
    "8462-4": "Diastolic BP",
}

# LOINC codes that are component observations (BP) — need special extraction
_COMPONENT_LOINC = "85354-9"  # Blood Pressure parent observation
_BP_SYSTOLIC_LOINC = "8480-6"
_BP_DIASTOLIC_LOINC = "8462-4"

# Panel groupings — when all LOINCs in a set are requested, use the panel name
_PANEL_NAMES: dict[frozenset[str], str] = {
    frozenset({"2093-3", "18262-6", "2085-9", "2571-8"}): "Lipid Panel",
    frozenset({"2093-3", "13457-7", "2085-9", "2571-8"}): "Lipid Panel",
    frozenset({"2093-3", "18262-6", "2085-9"}): "Lipid Panel",
}

# Regex for SNOMED suffixes (reused from table_builder)
_SNOMED_SUFFIX_RE = re.compile(
    r"\s*\("
    r"(?:finding|disorder|procedure|situation|morphologic abnormality|"
    r"observable entity|body structure|substance|event|regime/therapy|"
    r"physical object|qualifier value)"
    r"\)\s*$",
    re.IGNORECASE,
)


def _clean_display(name: str) -> str:
    """Strip SNOMED semantic tag suffixes from display names."""
    return _SNOMED_SUFFIX_RE.sub("", name).strip()


def _format_date(iso: str) -> str:
    """Format ISO date string to 'Mon DD, YYYY'. Returns original if unparseable."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y").replace(" 0", " ")
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(iso[:10], "%Y-%m-%d")
            return dt.strftime("%b %d, %Y").replace(" 0", " ")
        except (ValueError, TypeError):
            return iso


def _display_name(resource: dict[str, Any], field: str = "code") -> str:
    """Extract display string from a FHIR CodeableConcept field."""
    val = resource.get(field, {})
    if isinstance(val, str):
        return val
    codings = val.get("coding", [])
    if codings:
        return codings[0].get("display", "Unknown")
    return val.get("text", "Unknown")


# =============================================================================
# Clinical range bands for well-known lab values
# =============================================================================

# eGFR KDIGO CKD stages (mL/min/1.73m2)
_EGFR_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 0, "y2": 15, "severity": "critical", "label": "Stage 5 (Kidney failure)"},
    {"y1": 15, "y2": 30, "severity": "critical", "label": "Stage 4 (Severe)"},
    {"y1": 30, "y2": 45, "severity": "warning", "label": "Stage 3b (Moderate-severe)"},
    {"y1": 45, "y2": 60, "severity": "warning", "label": "Stage 3a (Moderate)"},
    {"y1": 60, "y2": 90, "severity": "normal", "label": "Stage 2 (Mild)"},
    {"y1": 90, "y2": 120, "severity": "normal", "label": "Stage 1 (Normal)"},
]

# HbA1c ADA targets (%)
_HBA1C_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 4.0, "y2": 5.7, "severity": "normal", "label": "Normal"},
    {"y1": 5.7, "y2": 6.5, "severity": "warning", "label": "Prediabetes"},
    {"y1": 6.5, "y2": 8.0, "severity": "warning", "label": "Diabetes (Controlled)"},
    {"y1": 8.0, "y2": 15.0, "severity": "critical", "label": "Diabetes (Uncontrolled)"},
]

# Total Cholesterol (mg/dL)
_CHOLESTEROL_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 0, "y2": 200, "severity": "normal", "label": "Desirable"},
    {"y1": 200, "y2": 240, "severity": "warning", "label": "Borderline High"},
    {"y1": 240, "y2": 400, "severity": "critical", "label": "High"},
]

# LDL Cholesterol (mg/dL)
_LDL_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 0, "y2": 100, "severity": "normal", "label": "Optimal"},
    {"y1": 100, "y2": 130, "severity": "normal", "label": "Near Optimal"},
    {"y1": 130, "y2": 160, "severity": "warning", "label": "Borderline High"},
    {"y1": 160, "y2": 190, "severity": "warning", "label": "High"},
    {"y1": 190, "y2": 300, "severity": "critical", "label": "Very High"},
]

# BMI (kg/m2)
_BMI_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 0, "y2": 18.5, "severity": "warning", "label": "Underweight"},
    {"y1": 18.5, "y2": 25.0, "severity": "normal", "label": "Normal"},
    {"y1": 25.0, "y2": 30.0, "severity": "warning", "label": "Overweight"},
    {"y1": 30.0, "y2": 40.0, "severity": "critical", "label": "Obese"},
]

# Glucose fasting (mg/dL)
_GLUCOSE_RANGE_BANDS: list[dict[str, Any]] = [
    {"y1": 0, "y2": 70, "severity": "warning", "label": "Low"},
    {"y1": 70, "y2": 100, "severity": "normal", "label": "Normal"},
    {"y1": 100, "y2": 126, "severity": "warning", "label": "Prediabetes"},
    {"y1": 126, "y2": 400, "severity": "critical", "label": "Diabetes Range"},
]

# LOINC code → range_bands lookup
_RANGE_BANDS_BY_LOINC: dict[str, list[dict[str, Any]]] = {
    "33914-3": _EGFR_RANGE_BANDS,    # eGFR (CKD-EPI)
    "69405-9": _EGFR_RANGE_BANDS,    # eGFR (CKD-EPI, non-race)
    "4548-4": _HBA1C_RANGE_BANDS,    # HbA1c
    "2093-3": _CHOLESTEROL_RANGE_BANDS,  # Total Cholesterol
    "18262-6": _LDL_RANGE_BANDS,     # LDL Direct
    "13457-7": _LDL_RANGE_BANDS,     # LDL Calculated
    "39156-5": _BMI_RANGE_BANDS,     # BMI
    "2345-7": _GLUCOSE_RANGE_BANDS,  # Glucose (serum/plasma)
    "14749-6": _GLUCOSE_RANGE_BANDS, # Glucose (fasting)
}


def _compute_trend_summary(
    data_points: list[dict[str, Any]],
    ref_range: dict | None,
) -> tuple[str | None, str | None]:
    """Compute trend summary text and status from data points.

    Returns:
        Tuple of (trend_summary, trend_status).
    """
    if len(data_points) < 2:
        # Single point — just report status vs reference range
        if not data_points or ref_range is None:
            return None, None
        val = data_points[-1]["value"]
        if val > ref_range.get("high", float("inf")):
            return "Above Normal", "warning"
        if val < ref_range.get("low", float("-inf")):
            return "Below Normal", "warning"
        return "Within Normal Range", "positive"

    first_val = data_points[0]["value"]
    last_val = data_points[-1]["value"]

    # Percentage change
    if first_val != 0:
        pct_change = ((last_val - first_val) / abs(first_val)) * 100
    else:
        pct_change = 0.0

    # Direction arrow
    if pct_change > 2:
        arrow = "\u2191"  # ↑
    elif pct_change < -2:
        arrow = "\u2193"  # ↓
    else:
        arrow = "\u2192"  # →

    pct_str = f"{abs(pct_change):.0f}%"

    # Status relative to reference range
    status_text = ""
    trend_status = "neutral"
    if ref_range is not None:
        high = ref_range.get("high", float("inf"))
        low = ref_range.get("low", float("-inf"))
        critical_high = ref_range.get("critical_high", float("inf"))
        critical_low = ref_range.get("critical_low", float("-inf"))

        if last_val > critical_high or last_val < critical_low:
            status_text = "Critical"
            trend_status = "critical"
        elif last_val > high:
            status_text = "Above Normal"
            trend_status = "warning"
        elif last_val < low:
            status_text = "Below Normal"
            trend_status = "warning"
        else:
            status_text = "Normal"
            trend_status = "positive"

    summary = f"{arrow} {pct_str}"
    if status_text:
        summary += f" \u00b7 {status_text}"

    return summary, trend_status


# =============================================================================
# BP Component Observation Helper
# =============================================================================


def _build_bp_component_series(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Extract systolic and diastolic series from BP component observations.

    BP (LOINC 85354-9) stores values in component[].valueQuantity, not
    valueQuantity on the parent. Each component has its own LOINC code:
    - 8480-6 = Systolic
    - 8462-4 = Diastolic
    """
    sys_points: list[dict[str, Any]] = []
    dia_points: list[dict[str, Any]] = []
    unit = "mmHg"

    for obs in observations:
        date_str = (obs.get("effectiveDateTime") or "")[:10]
        if not date_str:
            continue
        for comp in obs.get("component", []):
            comp_code = (
                comp.get("code", {}).get("coding", [{}])[0].get("code", "")
            )
            vq = comp.get("valueQuantity", {})
            value = vq.get("value")
            if value is None:
                continue
            unit = vq.get("unit", unit)
            if comp_code == _BP_SYSTOLIC_LOINC:
                sys_points.append({"date": date_str, "value": value})
            elif comp_code == _BP_DIASTOLIC_LOINC:
                dia_points.append({"date": date_str, "value": value})

    result = []
    if sys_points:
        result.append({
            "name": "Systolic",
            "unit": unit,
            "data_points": sys_points,
            "_loinc": _BP_SYSTOLIC_LOINC,
        })
    if dia_points:
        result.append({
            "name": "Diastolic",
            "unit": unit,
            "data_points": dia_points,
            "_loinc": _BP_DIASTOLIC_LOINC,
        })
    return result


# =============================================================================
# Trend Chart Builder
# =============================================================================

async def build_trend_chart(
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    loinc_codes: list[str],
    time_range: str | None = None,
) -> dict[str, Any] | None:
    """Build a trend chart from Observation resources for given LOINC codes.

    Args:
        patient_id: Patient UUID.
        db: Async database session.
        loinc_codes: List of LOINC codes to trend.
        time_range: Optional time range filter (e.g., "1y", "6m", "3m").

    Returns:
        ClinicalVisualization dict with type="trend_chart", or None if no data.
    """
    if not loinc_codes:
        return None

    loinc_expr = FhirResource.data["code"]["coding"][0]["code"].as_string()
    effective_dt = FhirResource.data["effectiveDateTime"].as_string()

    conditions = [
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Observation",
        loinc_expr.in_(loinc_codes),
    ]

    # Apply time range filter
    if time_range:
        cutoff = _parse_time_range(time_range)
        if cutoff:
            conditions.append(
                func.cast(effective_dt, DateTime) >= cutoff
            )

    stmt = (
        select(FhirResource.data)
        .where(*conditions)
        .order_by(func.cast(effective_dt, DateTime).asc())
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

    # Build series for each LOINC code
    series: list[dict[str, Any]] = []
    all_reference_lines: list[dict[str, Any]] = []
    all_range_bands: list[dict[str, Any]] | None = None
    chart_title_parts: list[str] = []
    current_value_str: str | None = None
    overall_trend_summary: str | None = None
    overall_trend_status: str | None = None

    for loinc_code in loinc_codes:
        observations = by_loinc.get(loinc_code, [])
        if not observations:
            continue

        # Blood Pressure: component observation — extract systolic + diastolic
        if loinc_code == _COMPONENT_LOINC:
            bp_series = _build_bp_component_series(observations)
            for bp_s in bp_series:
                if not bp_s["data_points"]:
                    continue
                bp_ref = get_reference_range(bp_s["_loinc"])
                bp_trend, bp_status = _compute_trend_summary(
                    bp_s["data_points"], bp_ref
                )
                if current_value_str is None:
                    latest = bp_s["data_points"][-1]["value"]
                    current_value_str = f"{latest} {bp_s['unit']}".strip()
                    overall_trend_summary = bp_trend
                    overall_trend_status = bp_status
                # Add reference lines for each BP component
                if bp_ref:
                    low = bp_ref.get("low")
                    high = bp_ref.get("high")
                    name = bp_s["name"]
                    if high is not None:
                        all_reference_lines.append({
                            "value": high,
                            "label": str(int(high)),
                            "series_name": name,
                        })
                series.append({
                    "name": bp_s["name"],
                    "unit": bp_s["unit"],
                    "data_points": bp_s["data_points"],
                })
            chart_title_parts.append("Blood Pressure")
            continue

        # Extract series name and unit from first observation
        first_obs = observations[0]
        code_obj = first_obs.get("code", {})
        codings = code_obj.get("coding", [])
        raw_name = codings[0].get("display", "Unknown") if codings else "Unknown"
        series_name = _LAB_DISPLAY_NAMES.get(loinc_code, raw_name)
        unit = first_obs.get("valueQuantity", {}).get("unit", "")

        # Build data points (chronological — already sorted by query)
        data_points: list[dict[str, Any]] = []
        for obs in observations:
            vq = obs.get("valueQuantity", {})
            value = vq.get("value")
            if value is None:
                continue
            date_str = (obs.get("effectiveDateTime") or "")[:10]
            data_points.append({
                "date": date_str,
                "value": value,
            })

        if not data_points:
            continue

        # Get reference range for this LOINC
        ref_range = get_reference_range(loinc_code)

        # Reference lines / range bands only for single-series charts
        # (multi-series with different units makes reference lines meaningless)
        if len(loinc_codes) == 1:
            if loinc_code in _RANGE_BANDS_BY_LOINC:
                all_range_bands = _RANGE_BANDS_BY_LOINC[loinc_code]
            elif ref_range:
                low = ref_range.get("low")
                high = ref_range.get("high")
                if low is not None:
                    all_reference_lines.append({
                        "value": low,
                        "label": f"Low ({low} {unit})" if unit else f"Low ({low})",
                    })
                if high is not None:
                    all_reference_lines.append({
                        "value": high,
                        "label": f"High ({high} {unit})" if unit else f"High ({high})",
                    })

        # Compute current value + trend summary
        latest_value = data_points[-1]["value"]
        current_val_str = f"{latest_value} {unit}".strip()

        trend_summary, trend_status = _compute_trend_summary(data_points, ref_range)

        # Use first series for card header metrics
        if current_value_str is None:
            current_value_str = current_val_str
            overall_trend_summary = trend_summary
            overall_trend_status = trend_status

        chart_title_parts.append(series_name)

        series.append({
            "name": series_name,
            "unit": unit or None,
            "data_points": data_points,
        })

    if not series:
        return None

    # Strip internal keys from series (e.g., _loinc from BP components)
    for s in series:
        s.pop("_loinc", None)

    # Build title — use panel name if all LOINCs match a known panel
    requested_set = frozenset(loinc_codes)
    panel_name = _PANEL_NAMES.get(requested_set)
    if panel_name:
        title = f"{panel_name} Trend"
    elif len(chart_title_parts) == 1:
        title = f"{chart_title_parts[0]} Trend"
    else:
        title = " & ".join(chart_title_parts[:3]) + " Trend"
        if len(chart_title_parts) > 3:
            title += f" (+{len(chart_title_parts) - 3} more)"

    # Build medication timeline if applicable
    medications = await _build_medication_timeline(
        patient_id, db, data_points=series[0]["data_points"]
    )

    # Determine subtitle
    if series[0]["data_points"]:
        first_date = series[0]["data_points"][0]["date"]
        last_date = series[0]["data_points"][-1]["date"]
        subtitle = f"{_format_date(first_date)} \u2013 {_format_date(last_date)}"
    else:
        subtitle = None

    # Y-axis minimum hint — BP readings waste space starting at 0
    y_min: int | None = None
    if _COMPONENT_LOINC in loinc_codes:
        y_min = 40

    viz: dict[str, Any] = {
        "type": "trend_chart",
        "title": title,
        "subtitle": subtitle,
        "current_value": current_value_str,
        "trend_summary": overall_trend_summary,
        "trend_status": overall_trend_status,
        "series": series,
        "reference_lines": all_reference_lines if all_reference_lines else None,
        "range_bands": all_range_bands,
        "medications": medications,
        "events": None,
        "y_min": y_min,
    }
    return viz


def _parse_time_range(time_range: str) -> datetime | None:
    """Parse a time range string like '1y', '6m', '3m' into a cutoff datetime."""
    now = datetime.now()
    time_range = time_range.strip().lower()
    try:
        if time_range.endswith("y"):
            years = int(time_range[:-1])
            return now.replace(year=now.year - years)
        elif time_range.endswith("m"):
            months = int(time_range[:-1])
            year = now.year
            month = now.month - months
            while month <= 0:
                month += 12
                year -= 1
            day = min(now.day, 28)  # safe day for all months
            return now.replace(year=year, month=month, day=day)
        elif time_range.endswith("d"):
            from datetime import timedelta
            days = int(time_range[:-1])
            return now - timedelta(days=days)
    except (ValueError, OverflowError):
        pass
    return None


async def _build_medication_timeline(
    patient_id: uuid.UUID,
    db: AsyncSession,
    *,
    data_points: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    """Build medication timeline rows that overlap the trend data period.

    Returns MedTimelineRow dicts for medications active during the trend,
    or None if no medications found.
    """
    if not data_points:
        return None

    # Parse trend date range
    first_date_str = data_points[0]["date"]
    last_date_str = data_points[-1]["date"]
    try:
        trend_start = datetime.strptime(first_date_str[:10], "%Y-%m-%d")
        trend_end = datetime.strptime(last_date_str[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    if trend_start >= trend_end:
        return None

    # Query MedicationRequest resources for this patient
    authored_on = FhirResource.data["authoredOn"].as_string()
    stmt = (
        select(FhirResource.data)
        .where(
            FhirResource.patient_id == patient_id,
            FhirResource.resource_type == "MedicationRequest",
        )
        .order_by(func.cast(authored_on, DateTime).asc().nulls_last())
    )
    result = await db.execute(stmt)
    meds = [row.data for row in result.all()]

    if not meds:
        return None

    # Group MedicationRequest entries by drug name.
    # Synthea re-prescribes at each encounter, so same drug appears many times.
    # Use earliest authoredOn as start, latest authoredOn as end.
    # If latest entry is "active", extend bar to trend_end.
    drug_spans: dict[str, dict[str, Any]] = {}
    for med in meds:
        drug = _display_name(med, "medicationCodeableConcept")
        if drug == "Unknown":
            continue
        authored_str = med.get("authoredOn", "")
        try:
            authored_dt = datetime.strptime(authored_str[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue
        status = med.get("status", "")
        if drug not in drug_spans:
            drug_spans[drug] = {
                "start": authored_dt,
                "end": authored_dt,
                "is_active": status == "active",
            }
        else:
            span = drug_spans[drug]
            span["start"] = min(span["start"], authored_dt)
            if authored_dt > span["end"]:
                span["end"] = authored_dt
                # Latest entry determines active status
                span["is_active"] = status == "active"

    total_days = (trend_end - trend_start).days or 1
    timeline_rows: list[dict[str, Any]] = []

    for drug, span in drug_spans.items():
        med_start: datetime = span["start"]
        # Active meds extend to trend end; completed meds end at last renewal
        med_end: datetime = trend_end if span["is_active"] else span["end"]

        # Skip meds that don't overlap the trend window
        if med_start > trend_end or med_end < trend_start:
            continue

        # Clamp to trend window
        bar_start = max(med_start, trend_start)
        bar_end = min(med_end, trend_end)

        # Build segments: gap before bar, active bar, gap after bar
        segments: list[dict[str, Any]] = []
        gap_before = (bar_start - trend_start).days
        bar_days = (bar_end - bar_start).days
        gap_after = (trend_end - bar_end).days

        if gap_before > 0:
            segments.append({"label": "", "flex": max(1, round((gap_before / total_days) * 100)), "active": False})
        segments.append({"label": "", "flex": max(1, round((bar_days / total_days) * 100)), "active": True})
        if gap_after > 0:
            segments.append({"label": "", "flex": max(1, round((gap_after / total_days) * 100)), "active": False})

        timeline_rows.append({"drug": drug, "segments": segments})

    return timeline_rows if timeline_rows else None


# =============================================================================
# Encounter Timeline Builder
# =============================================================================

async def build_encounter_timeline(
    patient_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Build an encounter timeline from Encounter resources.

    Args:
        patient_id: Patient UUID.
        db: Async database session.

    Returns:
        ClinicalVisualization dict with type="encounter_timeline", or None if no data.
    """
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

    events: list[dict[str, Any]] = []
    for enc in resources:
        # Type display
        enc_types = enc.get("type", [])
        type_display = "Unknown"
        if enc_types and isinstance(enc_types, list):
            first_type = enc_types[0]
            if isinstance(first_type, dict):
                type_display = _display_name({"code": first_type})
            elif isinstance(first_type, str):
                type_display = first_type

        # Class code (AMB/EMER/IMP)
        enc_class = enc.get("class", {})
        class_code = enc_class.get("code", "AMB") if isinstance(enc_class, dict) else str(enc_class)

        # Date
        period = enc.get("period", {})
        date_str = ""
        if isinstance(period, dict):
            date_str = (period.get("start") or "")[:10]

        # Detail: extract reason from reasonCode or type
        detail = None
        reason_codes = enc.get("reasonCode", [])
        if reason_codes and isinstance(reason_codes, list):
            first_reason = reason_codes[0]
            if isinstance(first_reason, dict):
                detail = _clean_display(_display_name({"code": first_reason}))

        events.append({
            "date": _format_date(date_str),
            "title": _clean_display(type_display),
            "detail": detail,
            "category": class_code.upper() if class_code else "AMB",
        })

    if not events:
        return None

    return {
        "type": "encounter_timeline",
        "title": "Encounter Timeline",
        "subtitle": f"{len(events)} encounters",
        "current_value": None,
        "trend_summary": None,
        "trend_status": None,
        "series": None,
        "reference_lines": None,
        "range_bands": None,
        "medications": None,
        "events": events,
    }


# =============================================================================
# Dispatcher
# =============================================================================

_BUILDERS: dict[str, Any] = {
    "trend_chart": build_trend_chart,
    "encounter_timeline": build_encounter_timeline,
}


async def build_chart_for_type(
    chart_type: str,
    patient_id: uuid.UUID,
    db: AsyncSession,
    **kwargs: Any,
) -> dict[str, Any] | None:
    """Build a clinical visualization by type, dispatching to the appropriate builder.

    Args:
        chart_type: One of CHART_TYPES (e.g. "trend_chart", "encounter_timeline").
        patient_id: Patient UUID.
        db: Async database session.
        **kwargs: Additional arguments passed to the builder (e.g., loinc_codes).

    Returns:
        ClinicalVisualization dict, or None if no data.
    """
    builder = _BUILDERS.get(chart_type)
    if builder is None:
        logger.warning("Unknown chart type: %s", chart_type)
        return None

    if chart_type == "trend_chart":
        loinc_codes = kwargs.get("loinc_codes", [])
        time_range = kwargs.get("time_range")
        return await builder(patient_id, db, loinc_codes=loinc_codes, time_range=time_range)
    else:
        return await builder(patient_id, db)
