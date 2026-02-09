"""LLM Agent Service for clinical reasoning with structured output.

This is the brain of the chat system - it takes patient context and user messages,
reasons about them using GPT-5.2, and returns structured responses with insights,
visualizations, and follow-up suggestions.

Uses the OpenAI Responses API with Pydantic structured outputs for type-safe
response parsing.
"""

import base64
import json
import logging
import time
from collections.abc import AsyncGenerator
from typing import Any, Literal

from openai import AsyncOpenAI
from openai.types.shared_params import Reasoning
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import AgentResponse
from app.schemas.agent import LightningResponse
from app.services.agent_tools import TOOL_SCHEMAS, execute_tool
from app.services.graph import KnowledgeGraph
from app.services.query_classifier import QueryProfile

logger = logging.getLogger(__name__)

# Tier constants for controlling output verbosity
TIER_DEEP = "deep"
TIER_QUICK = "quick"
TIER_LIGHTNING = "lightning"

# Default model for agent responses
DEFAULT_MODEL = "gpt-5-mini"

# Default reasoning effort (medium balances quality with speed; summary="concise" enables streaming summaries)
DEFAULT_REASONING_EFFORT: Literal["low", "medium", "high"] = "medium"

# Maximum tokens for response generation
DEFAULT_MAX_OUTPUT_TOKENS = 16384

# Maximum tool-calling rounds before forcing a final response
MAX_TOOL_ROUNDS = 10

# Shared persona constant — "who I am" across all tiers
_PERSONA = (
    "You are Crux, a clinical intelligence assistant for primary care physicians. "
    "You have deep access to this patient's medical record.\n"
    "\n"
    "Core principles:\n"
    "- Cite specific data points (dates, values) to support every claim\n"
    "- Never fabricate clinical data — if uncertain, say so\n"
    "- Be transparent about completeness: if your answer is based only on a summary "
    "snapshot, say so. Never imply that data doesn't exist just because it's not in "
    "the summary — a deeper search of the full record may find it\n"
    "- When data is absent from what you can see, distinguish between 'not found in "
    "the chart summary' and 'not present in the patient's record' — the former is "
    "a limitation of your current view, the latter is a clinical finding\n"
    "- Never reveal internal implementation details to the user. They do not know "
    "how you work under the hood and should not need to. Specifically:\n"
    "  - Never mention 'patient summary', 'compiled summary', 'summary snapshot', "
    "or any reference to pre-compiled data. Say 'the patient's record' or 'the chart'\n"
    "  - Never expose FHIR terminology: resource IDs, resource types (MedicationRequest, "
    "Observation, etc.), FHIR references, or LOINC/SNOMED codes\n"
    "  - Never mention tools, searches, queries, or internal processing steps\n"
    "  - Never reference tiers, models, or system architecture"
)


def _extract_usage(response: Any) -> dict[str, int]:
    """Extract token usage from an OpenAI response, returning empty dict if unavailable."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    return {
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
    }

def _get_display_name(resource: dict[str, Any], code_field: str = "code") -> str | None:
    """Extract display name from a FHIR resource's code field.

    Args:
        resource: FHIR resource dict
        code_field: Name of the code field to extract from

    Returns:
        Display name string or None if not found
    """
    code = resource.get(code_field, {})
    if isinstance(code, str):
        return code
    codings = code.get("coding", [])
    if codings:
        return codings[0].get("display")
    return code.get("text")


# ── FHIR resource pruning ────────────────────────────────────────────────────
# Instead of maintaining per-type formatters, we recursively simplify the raw
# FHIR JSON so the LLM sees every clinically relevant field without FHIR
# boilerplate (system URIs, meta, profiles, identifiers, narrative HTML).

# Top-level keys to strip (zero clinical value to the LLM)
_STRIP_KEYS = frozenset({
    "meta", "text", "identifier", "implicitRules", "language",
    "contained", "extension", "modifierExtension",
})

# Keys to strip from inner objects (noisy identifiers / serialisation artifacts)
_STRIP_INNER_KEYS = frozenset({
    "system", "use", "assigner", "rank", "postalCode",
})


def _simplify_codeable_concept(cc: dict[str, Any]) -> str | dict[str, Any]:
    """Reduce a CodeableConcept to its display string when possible."""
    codings = cc.get("coding", [])
    display = cc.get("text") or (codings[0].get("display") if codings else None)
    code = codings[0].get("code") if codings else None
    if display and code:
        return display
    if display:
        return display
    return cc  # can't simplify, pass through


def _simplify_reference(ref: dict[str, Any]) -> str | dict[str, Any]:
    """Reduce a Reference to its display string or a short ID."""
    display = ref.get("display")
    raw_ref = ref.get("reference", "")
    # Strip urn:uuid: prefix
    short_ref = raw_ref[9:] if raw_ref.startswith("urn:uuid:") else raw_ref
    if display:
        return display
    if short_ref:
        return short_ref
    return ref


def _is_codeable_concept(val: Any) -> bool:
    """Check if a value looks like a FHIR CodeableConcept."""
    return isinstance(val, dict) and ("coding" in val or ("text" in val and len(val) <= 3))


def _is_reference(val: Any) -> bool:
    """Check if a value looks like a FHIR Reference."""
    return isinstance(val, dict) and "reference" in val and not isinstance(val.get("reference"), dict)


def _simplify_value(val: Any) -> Any:
    """Recursively simplify a FHIR value."""
    if isinstance(val, dict):
        if _is_codeable_concept(val):
            return _simplify_codeable_concept(val)
        if _is_reference(val):
            return _simplify_reference(val)
        return _simplify_dict(val)
    if isinstance(val, list):
        simplified = [_simplify_value(item) for item in val]
        # Unwrap single-element lists of simple values
        if len(simplified) == 1 and isinstance(simplified[0], str):
            return simplified[0]
        return simplified
    return val


def _simplify_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively simplify a FHIR dict, stripping boilerplate keys."""
    result = {}
    for key, val in d.items():
        if key in _STRIP_INNER_KEYS:
            continue
        simplified = _simplify_value(val)
        # Truncate ISO date strings anywhere in the tree.
        # Only match keys that genuinely contain dates — avoid false
        # positives like "location" matching on the "on" suffix.
        if isinstance(simplified, str) and "T" in simplified and (
            key.lower().endswith(("date", "datetime"))
            or key in ("issued", "recorded", "started", "created", "authoredOn")
        ):
            simplified = _truncate_date(simplified)
        # Truncate dates inside period objects anywhere in the tree
        if isinstance(simplified, dict) and key.lower() in (
            "period", "billableperiod", "performedperiod",
        ):
            for pkey in ("start", "end"):
                if isinstance(simplified.get(pkey), str):
                    simplified[pkey] = _truncate_date(simplified[pkey])
        result[key] = simplified
    return result


def _truncate_date(val: str) -> str:
    """Truncate an ISO datetime to date-only if it includes time."""
    if isinstance(val, str) and "T" in val:
        return val[:10]
    return val


def _format_as_table(headers: list[str], rows: list[list[str]]) -> str:
    """Format data as a markdown table.

    Args:
        headers: Column header strings.
        rows: List of rows, each a list of cell strings.

    Returns:
        Markdown table string. Returns empty string if no rows.
    """
    if not rows:
        return ""
    header_line = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, separator, *body_lines])


def _prune_fhir_resource(resource: dict[str, Any]) -> dict[str, Any]:
    """Recursively prune a FHIR resource for LLM consumption.

    Removes FHIR boilerplate (meta, system URIs, identifiers, narrative HTML),
    simplifies CodeableConcepts and References to display strings, decodes
    base64 clinical note content, and truncates dates. The result contains
    every clinically relevant field in a compact, readable form.
    """
    # Pre-process: handle DocumentReference base64 content before recursion
    extra: dict[str, Any] = {}
    if resource.get("resourceType") == "DocumentReference":
        for content_item in resource.get("content", []):
            attachment = content_item.get("attachment", {})
            if attachment.get("data") and "text/plain" in attachment.get("contentType", ""):
                try:
                    decoded = base64.b64decode(attachment["data"]).decode("utf-8")
                    extra["clinical_note"] = decoded
                except Exception:
                    pass

    # Build a filtered copy, then let _simplify_dict handle recursive
    # simplification, date truncation, and inner-key stripping.
    filtered = {}
    skip_keys = _STRIP_KEYS | {
        # Device noise
        "udiCarrier", "distinctIdentifier", "lotNumber", "serialNumber",
        # Claim/EOB noise
        "insurance", "priority",
    }
    for key, val in resource.items():
        if key in skip_keys:
            continue
        # Replace raw content with decoded clinical_note
        if key == "content" and "clinical_note" in extra:
            continue
        filtered[key] = val

    pruned = _simplify_dict(filtered)
    pruned.update(extra)
    return pruned


def _format_tier1_conditions(conditions: list[dict[str, Any]], tier: str = TIER_DEEP) -> str:
    """Format Tier 1 active conditions with treating meds, care plans, and procedures.

    Conditions are displayed as headers (hierarchical). Treating medications are
    rendered as a markdown table under each condition. Care plans and procedures
    remain as structured text.

    Args:
        conditions: List of condition dicts with treating_medications, care_plans, etc.
        tier: Output tier (deep/fast/lightning). Deep includes FHIR IDs.
    """
    if not conditions:
        return "No active conditions recorded."

    lines: list[str] = []
    for entry in conditions:
        cond = entry.get("condition", {})
        # In pruned resources, code may be simplified to a string
        code_val = cond.get("code")
        if isinstance(code_val, str):
            cond_display = code_val
        else:
            cond_display = _get_display_name(cond) or cond.get("resourceType", "Unknown condition")
        clinical_status = cond.get("clinicalStatus", "unknown")
        if isinstance(clinical_status, dict):
            status_codings = clinical_status.get("coding", [])
            clinical_status = status_codings[0].get("code") if status_codings else "unknown"

        onset = cond.get("onsetDateTime", "")
        if onset:
            onset = onset[:10]

        # Build condition header — Lightning: name + onset only; others add status + optional FHIR ID
        cond_parts: list[str] = []
        if tier != TIER_LIGHTNING and clinical_status.lower() != "active":
            cond_parts.append(f"status: {clinical_status}")
        if onset:
            cond_parts.append(f"onset: {onset}")
        if tier == TIER_DEEP:
            cond_parts.append(f"id: {cond.get('id', 'unknown')}")

        cond_line = f"  - {cond_display}"
        if cond_parts:
            cond_line += f" ({', '.join(cond_parts)})"
        lines.append(cond_line)

        # Treating medications — markdown table
        # Lightning: 3-column table (no dose history). Quick/Deep: 4-column with dose history.
        treating_meds = entry.get("treating_medications", [])
        if treating_meds:
            med_rows: list[list[str]] = []
            for med in treating_meds:
                mcc = med.get("medicationCodeableConcept")
                if isinstance(mcc, str):
                    med_display = mcc
                else:
                    med_display = _get_display_name(med, "medicationCodeableConcept") or "Unknown medication"
                med_status = med.get("status", "unknown")
                recency = med.get("_recency", "")
                if tier == TIER_LIGHTNING:
                    med_rows.append([med_display, med_status, recency])
                else:
                    dose_hist_str = ""
                    if med.get("_dose_history"):
                        dose_hist = med["_dose_history"]
                        changes = [f"{d.get('dose', '?')} on {(d.get('authoredOn', ''))[:10]}" for d in dose_hist]
                        dose_hist_str = ", ".join(changes)
                    med_rows.append([med_display, med_status, recency, dose_hist_str])
            if tier == TIER_LIGHTNING:
                table = _format_as_table(["Medication", "Status", "Recency"], med_rows)
            else:
                table = _format_as_table(["Medication", "Status", "Recency", "Dose History"], med_rows)
            # Indent the table under the condition
            for table_line in table.split("\n"):
                lines.append(f"    {table_line}")

        # Care plans and procedures — skip for Lightning (token savings)
        if tier != TIER_LIGHTNING:
            care_plans = entry.get("care_plans", [])
            if care_plans:
                for cp in care_plans:
                    cat_val = cp.get("category")
                    if isinstance(cat_val, str):
                        cp_display = cat_val
                    else:
                        cp_display = _get_display_name(cp) or cp.get("title", "Unknown care plan")
                        if cp_display == "Unknown care plan" and isinstance(cat_val, str):
                            cp_display = cat_val
                    cp_status = cp.get("status", "unknown")
                    lines.append(f"      CarePlan: {cp_display} (status: {cp_status})")

            procedures = entry.get("related_procedures", [])
            if procedures:
                for proc in procedures:
                    code_val = proc.get("code")
                    if isinstance(code_val, str):
                        proc_display = code_val
                    else:
                        proc_display = _get_display_name(proc) or "Unknown procedure"
                    lines.append(f"      Procedure: {proc_display}")

    return "\n".join(lines)


def _format_tier1_section(
    label: str,
    items: list[dict[str, Any]],
    display_fn=None,
    *,
    headers: list[str] | None = None,
    row_fn=None,
) -> str:
    """Format a simple Tier 1 section as a markdown table or flat list.

    When headers and row_fn are provided, renders as a markdown table.
    Otherwise falls back to display_fn for flat-list rendering.

    Args:
        label: Section header label.
        items: List of FHIR resource dicts.
        display_fn: Legacy single-line display function (used for care plans).
        headers: Table column headers (enables table mode).
        row_fn: Function that takes a dict and returns a list of cell strings.
    """
    if not items:
        return ""
    lines = [f"\n  {label}:"]
    if headers and row_fn:
        rows = [row_fn(item) for item in items]
        table = _format_as_table(headers, rows)
        for table_line in table.split("\n"):
            lines.append(f"    {table_line}")
    else:
        for item in items:
            lines.append(f"    - {display_fn(item)}")
    return "\n".join(lines)


def _allergy_row(a: dict[str, Any]) -> list[str]:
    """Return a table row [Allergen, Criticality, Category] for an allergy."""
    code = a.get("code")
    if isinstance(code, str):
        display = code
    else:
        display = _get_display_name(a) or "Unknown allergen"
    criticality = a.get("criticality", "unknown")
    categories = a.get("category", [])
    cat = categories[0] if isinstance(categories, list) and categories else (categories if isinstance(categories, str) else "unknown")
    return [display, criticality, cat]


def _immunization_row(im: dict[str, Any]) -> list[str]:
    """Return a table row [Vaccine, Date] for an immunization."""
    vc = im.get("vaccineCode")
    if isinstance(vc, str):
        display = vc
    else:
        display = _get_display_name(im, "vaccineCode") or "Unknown vaccine"
    occ = im.get("occurrenceDateTime", "")
    if occ:
        occ = occ[:10]
    return [display, occ]


def _unlinked_med_row(med: dict[str, Any]) -> list[str]:
    """Return a table row [Medication, Status, Recency] for an unlinked medication."""
    mcc = med.get("medicationCodeableConcept")
    if isinstance(mcc, str):
        display = mcc
    else:
        display = _get_display_name(med, "medicationCodeableConcept") or "Unknown medication"
    status = med.get("status", "unknown")
    recency = med.get("_recency", "")
    return [display, status, recency]


def _care_plan_display(cp: dict[str, Any]) -> str:
    """Format a standalone care plan for display."""
    cat_val = cp.get("category")
    if isinstance(cat_val, str):
        display = cat_val
    else:
        code_val = cp.get("code")
        if isinstance(code_val, str):
            display = code_val
        else:
            display = _get_display_name(cp) or cp.get("title", "Unknown care plan")
    status = cp.get("status", "unknown")
    return f"{display} (status: {status})"


def _format_tier2_encounters(encounters: list[dict[str, Any]], tier: str = TIER_DEEP) -> str:
    """Format Tier 2 recent encounters.

    Args:
        encounters: List of encounter entry dicts.
        tier: Output tier (deep includes FHIR IDs).
    """
    if not encounters:
        return "No recent encounters."

    lines: list[str] = []
    for enc_entry in encounters:
        enc = enc_entry.get("encounter", {})
        enc_type = enc.get("type", "Unknown")
        if isinstance(enc_type, list):
            enc_type = enc_type[0] if enc_type else "Unknown"
        period = enc.get("period", {})
        start = ""
        if isinstance(period, dict):
            start = period.get("start", "")
        elif isinstance(period, str):
            start = period
        if start:
            start = start[:10]

        class_info = enc.get("class", {})
        class_code = class_info.get("code", "") if isinstance(class_info, dict) else str(class_info)

        header = f"  [{start}] {enc_type}"
        if class_code:
            header += f" ({class_code})"
        if tier == TIER_DEEP:
            header += f" id:{enc.get('id', '?')}"
        lines.append(header)

        # Events grouped by relationship type
        rel_labels = {
            "DIAGNOSED": "Diagnoses",
            "PRESCRIBED": "Medications",
            "RECORDED": "Observations",
        }
        events = enc_entry.get("events", {})
        for rel_type, label in rel_labels.items():
            resources = events.get(rel_type, [])
            if not resources:
                continue
            displays = []
            for r in resources:
                r_display = _get_display_name(r) or r.get("resourceType", "?")
                displays.append(r_display)
            lines.append(f"    {label}: {', '.join(displays)}")

        # Clinical notes from DOCUMENTED events
        documented = events.get("DOCUMENTED", [])
        for r in documented:
            clinical_note = r.get("clinical_note")
            if clinical_note:
                note_preview = clinical_note[:500] + "..." if len(clinical_note) > 500 else clinical_note
                lines.append(f"    Note: {note_preview}")

    return "\n".join(lines)


def _format_tier3_observations(obs_by_category: dict[str, list[dict[str, Any]]]) -> str:
    """Format Tier 3 latest observations by category as markdown tables.

    Each non-empty category renders as a labelled table with columns:
    Observation | Value | Date | Ref Range | Trend
    """
    category_labels = {
        "laboratory": "Lab Results",
        "vital-signs": "Vital Signs",
        "survey": "Surveys",
        "social-history": "Social History",
    }
    lines: list[str] = []
    for category, obs_list in obs_by_category.items():
        if not obs_list:
            continue
        label = category_labels.get(category, category.title())
        lines.append(f"\n  {label}:")

        rows: list[list[str]] = []
        for obs in obs_list:
            code_val = obs.get("code")
            if isinstance(code_val, str):
                obs_display = code_val
            else:
                obs_display = _get_display_name(obs) or "Unknown observation"

            value_str = ""
            vq = obs.get("valueQuantity")
            if isinstance(vq, dict):
                val = vq.get("value")
                unit = vq.get("unit", "")
                if val is not None:
                    value_str = f"{val} {unit}".rstrip()
            elif obs.get("valueString"):
                value_str = obs["valueString"]

            date_str = ""
            eff_dt = obs.get("effectiveDateTime", "")
            if eff_dt:
                date_str = eff_dt[:10]

            ref_str = ""
            ref_range = obs.get("referenceRange", [])
            if ref_range and isinstance(ref_range, list) and ref_range[0]:
                rr = ref_range[0]
                low = rr.get("low", {})
                high = rr.get("high", {})
                if isinstance(low, dict) and isinstance(high, dict):
                    low_val = low.get("value")
                    high_val = high.get("value")
                    if low_val is not None and high_val is not None:
                        ref_str = f"{low_val}-{high_val}"

            trend_str = ""
            trend = obs.get("_trend")
            if isinstance(trend, dict):
                direction = trend.get("direction", "")
                prev_val = trend.get("previous_value")
                prev_date = (trend.get("previous_date", "") or "")[:10]
                trend_str = direction
                if prev_val is not None:
                    trend_str += f", prev={prev_val}"
                if prev_date:
                    trend_str += f" on {prev_date}"

            rows.append([obs_display, value_str, date_str, ref_str, trend_str])

        table = _format_as_table(
            ["Observation", "Value", "Date", "Ref Range", "Trend"], rows
        )
        for table_line in table.split("\n"):
            lines.append(f"    {table_line}")

    if not lines:
        return "No recent observations."
    return "\n".join(lines)


def _format_safety_constraints_v2(safety: dict[str, Any]) -> str:
    """Format safety constraints from the compiled summary."""
    lines: list[str] = []

    allergies = safety.get("active_allergies", [])
    if allergies:
        for a in allergies:
            if a.get("note") == "None recorded":
                lines.append("- No known allergies recorded.")
                continue
            code = a.get("code")
            if isinstance(code, str):
                display = code
            else:
                display = _get_display_name(a) or "Unknown allergen"
            criticality = a.get("criticality", "unknown")
            lines.append(f"- ALLERGY: {display} (criticality: {criticality})")

    note = safety.get("drug_interactions_note")
    if note:
        lines.append(f"- {note}")

    if not lines:
        return "No specific safety constraints."
    return "\n".join(lines)


def _build_patient_summary_section(
    compiled_summary: dict[str, Any],
    patient_profile: str | None = None,
    tier: str = TIER_DEEP,
) -> str:
    """Build the patient summary section for all three tiers.

    Tier controls verbosity:
      - TIER_LIGHTNING: conditions + meds (slim), allergies, immunizations, observations.
        Skips resolved conditions, unlinked meds, care plans, tier 2 encounters, FHIR IDs.
      - TIER_QUICK: Full tier 1/2/3 data but omits FHIR IDs.
      - TIER_DEEP: Full tier 1/2/3 data with FHIR IDs.

    Args:
        compiled_summary: Dict from compile_patient_summary().
        patient_profile: Optional non-clinical patient profile narrative.
        tier: Output tier controlling verbosity (deep/quick/lightning).

    Returns:
        Formatted patient summary string.
    """
    patient_orientation = compiled_summary.get("patient_orientation", "Unknown patient")
    compilation_date = compiled_summary.get("compilation_date", "unknown")

    summary_parts: list[str] = [
        f"## Patient Record (compiled {compilation_date})\n",
        f"**Patient:** {patient_orientation}\n",
    ]

    if patient_profile:
        summary_parts.append(f"**Profile:** {patient_profile}\n")

    # Tier 1: Active conditions
    tier1_conditions = compiled_summary.get("tier1_active_conditions", [])
    summary_parts.append("### Active Conditions & Treatments")
    summary_parts.append(_format_tier1_conditions(tier1_conditions, tier=tier))

    # Tier 1: Recently resolved conditions — skip for Lightning
    if tier != TIER_LIGHTNING:
        tier1_resolved = compiled_summary.get("tier1_recently_resolved", [])
        if tier1_resolved:
            summary_parts.append("\n### Recently Resolved Conditions (last 6 months)")
            summary_parts.append(_format_tier1_conditions(tier1_resolved, tier=tier))

    # Tier 1: Allergies — table
    tier1_allergies = compiled_summary.get("tier1_allergies", [])
    allergy_lines = _format_tier1_section(
        "Allergies", tier1_allergies,
        headers=["Allergen", "Criticality", "Category"],
        row_fn=_allergy_row,
    )
    if allergy_lines:
        summary_parts.append(allergy_lines)

    # Tier 1: Unlinked medications — skip for Lightning
    if tier != TIER_LIGHTNING:
        tier1_unlinked = compiled_summary.get("tier1_unlinked_medications", [])
        if tier1_unlinked:
            unlinked_lines = _format_tier1_section(
                "Medications (not linked to a condition)", tier1_unlinked,
                headers=["Medication", "Status", "Recency"],
                row_fn=_unlinked_med_row,
            )
            if unlinked_lines:
                summary_parts.append(unlinked_lines)

    # Tier 1: Immunizations — table
    tier1_immunizations = compiled_summary.get("tier1_immunizations", [])
    if tier1_immunizations:
        imm_lines = _format_tier1_section(
            "Immunizations", tier1_immunizations,
            headers=["Vaccine", "Date"],
            row_fn=_immunization_row,
        )
        if imm_lines:
            summary_parts.append(imm_lines)

    # Tier 1: Standalone care plans — skip for Lightning
    if tier != TIER_LIGHTNING:
        tier1_care_plans = compiled_summary.get("tier1_care_plans", [])
        if tier1_care_plans:
            cp_lines = _format_tier1_section("Standalone Care Plans", tier1_care_plans, _care_plan_display)
            if cp_lines:
                summary_parts.append(cp_lines)

    # Tier 2: Recent encounters — skip for Lightning
    if tier != TIER_LIGHTNING:
        tier2 = compiled_summary.get("tier2_recent_encounters", [])
        summary_parts.append("\n### Recent Encounters")
        summary_parts.append(_format_tier2_encounters(tier2, tier=tier))

    # Tier 3: Latest observations
    tier3 = compiled_summary.get("tier3_latest_observations", {})
    summary_parts.append("\n### Latest Observations")
    summary_parts.append(_format_tier3_observations(tier3))

    return "\n".join(summary_parts)


def _build_safety_section(compiled_summary: dict[str, Any]) -> str:
    """Build the safety constraints section shared by both fast and standard prompts.

    Args:
        compiled_summary: Dict from compile_patient_summary().

    Returns:
        Formatted safety section string.
    """
    safety = compiled_summary.get("safety_constraints", {})
    safety_text = _format_safety_constraints_v2(safety)

    return (
        "## Safety Constraints\n"
        "\n"
        "The following constraints MUST be respected in every response:\n"
        "\n"
        f"{safety_text}\n"
        "\n"
        "Additional safety rules:\n"
        "- Always highlight drug allergies when discussing medication changes\n"
        "- Flag critical lab values that require immediate attention\n"
        "- Never recommend starting, stopping, or changing medications — only surface "
        "relevant data and considerations for the physician's decision\n"
        "- If unsure about a clinical fact, state the uncertainty rather than guessing"
    )


def _build_safety_section_lightning(compiled_summary: dict[str, Any]) -> str:
    """Build a minimal safety section for Lightning-tier fact extraction.

    Lightning only extracts facts from the chart — it never discusses medication
    changes, recommendations, or clinical reasoning. The safety section is
    trimmed to just active allergy alerts and a single fabrication guard.

    Args:
        compiled_summary: Dict from compile_patient_summary().

    Returns:
        Formatted safety section string.
    """
    safety = compiled_summary.get("safety_constraints", {})
    safety_text = _format_safety_constraints_v2(safety)

    return (
        "## Safety Constraints\n"
        "\n"
        f"{safety_text}"
    )


def build_system_prompt_lightning(
    compiled_summary: dict[str, Any],
    patient_profile: str | None = None,
) -> str:
    """Build a minimal system prompt for Lightning-tier fact extraction.

    Even more trimmed than the Quick prompt: concise role, slim patient
    summary (no encounters, care plans, or procedures), minimal safety
    (allergy alerts + fabrication guard only), brief format section.
    No reasoning directives, no tool descriptions, no insight/viz/table
    instructions.

    Args:
        compiled_summary: Dict from compile_patient_summary().
        patient_profile: Optional non-clinical patient profile narrative.

    Returns:
        Formatted system prompt string.
    """
    tier_instructions = (
        "For this query, extract and present the requested data from the patient "
        "record below. Be concise — use bullet lists for multiple items.\n"
        "\n"
        "If the requested information is not available in the record below, "
        "set needs_deeper_search to true and write a brief narrative like "
        "'Searching the full patient record for [value]...'"
    )

    summary_section = _build_patient_summary_section(compiled_summary, patient_profile, tier=TIER_LIGHTNING)

    safety_section = _build_safety_section_lightning(compiled_summary)

    format_section = (
        "## Response Format\n"
        "Respond with a JSON object containing:\n"
        "- narrative: Brief summary in markdown (1-2 sentences max — the table carries the detail)\n"
        "- tables: Clinical data tables when presenting structured data (see Table Types below)\n"
        "- follow_ups: 2-3 short follow-up questions (under 80 chars each)\n"
        "- needs_deeper_search: Set to true ONLY if the requested data is not present "
        "in the patient record above. If you found the answer, set to false.\n"
        "\n"
        "## Table Types\n"
        "When the user asks about a category of clinical data, ALWAYS include a typed table "
        "instead of listing items in the narrative. Keep the narrative to a brief summary.\n"
        "Use the row keys exactly as specified:\n"
        "\n"
        "medications: medication (full RxNorm string e.g. \"Lisinopril 10 MG Oral Tablet\"), "
        "frequency (e.g. \"1x daily\" or null), reason, status (active/completed), authoredOn, requester\n"
        "lab_results: test, value (number), unit, rangeLow (number), rangeHigh (number), "
        "interpretation (N/H/L/HH/LL), date, history (array of {value, date} with last 6 readings). "
        "Optional: panel (group name).\n"
        "vitals: vital, value (display string), numericValue (number), unit, loinc, date\n"
        "conditions: condition, clinicalStatus (active/resolved), onsetDate, abatementDate (null for active)\n"
        "allergies: allergen, category (medication/food/environment), criticality (high/low), "
        "clinicalStatus (active/inactive), onsetDate\n"
        "immunizations: vaccine (CVX display), date, location\n"
        "procedures: procedure (SNOMED display), date, location, reason (null if unknown)\n"
        "encounters: type (SNOMED display), encounterClass (AMB/EMER/IMP), date, provider, "
        "location, reason (null if unknown)"
    )

    return "\n\n".join([
        _PERSONA,
        tier_instructions,
        summary_section,
        safety_section,
        format_section,
    ])


def build_system_prompt_quick(
    compiled_summary: dict[str, Any],
    patient_profile: str | None = None,
) -> str:
    """Build the Quick-tier system prompt for focused chart lookups.

    Trimmed prompt for Quick-tier queries: no reasoning directives, no tool
    descriptions, concise role and response format. Saves ~2700-3000 chars
    (~750 tokens) of input vs the Deep prompt.

    Args:
        compiled_summary: Dict from compile_patient_summary().
        patient_profile: Optional non-clinical patient profile narrative.

    Returns:
        Formatted system prompt string.
    """
    tier_instructions = (
        "For this query, answer directly from the patient record below. "
        "Be concise and data-focused. Use tools to search when needed."
    )

    summary_section = _build_patient_summary_section(compiled_summary, patient_profile, tier=TIER_QUICK)

    safety_section = _build_safety_section(compiled_summary)

    format_section = (
        "## Response Format\n"
        "Provide your response as a structured JSON object with:\n"
        "- narrative: Main response in markdown (concise, data-focused)\n"
        "- insights: Clinical insights if relevant (info/warning/critical/positive)\n"
        "- tables: Clinical data tables when presenting structured data (see Table Types below)\n"
        "- follow_ups: 2-3 SHORT follow-up questions (under 80 chars each)\n"
        "\n"
        "## Table Types\n"
        "When your response includes structured clinical data, include a typed table.\n"
        "Use the row keys exactly as specified:\n"
        "\n"
        "medications: medication (full RxNorm string e.g. \"Lisinopril 10 MG Oral Tablet\"), "
        "frequency (e.g. \"1x daily\" or null), reason, status (active/completed), authoredOn, requester\n"
        "lab_results: test, value (number), unit, rangeLow (number), rangeHigh (number), "
        "interpretation (N/H/L/HH/LL — HL7 FHIR codes), date, history (array of {value: number, date: string} "
        "with last 6 readings). Optional: panel (string — group name e.g. \"Complete Blood Count (CBC)\"; "
        "rows sharing the same panel value render as a collapsible group).\n"
        "vitals: vital (LOINC display), value (display string e.g. \"128/82\"), "
        "numericValue (number — systolic for BP), unit, loinc, date. "
        "Optional: history (array of {value, date}), rangeLow (number), rangeHigh (number), "
        "interpretation (N/H/L/HH/LL). Only include range/history for vitals with clinical ranges "
        "(BP, HR, RR, BMI, Temp).\n"
        "conditions: condition, clinicalStatus (active/resolved), onsetDate, abatementDate (null for active)\n"
        "allergies: allergen, category (medication/food/environment), criticality (high/low), "
        "clinicalStatus (active/inactive), onsetDate\n"
        "immunizations: vaccine (CVX display), date, location\n"
        "procedures: procedure (SNOMED display), date, location, reason (null if unknown)\n"
        "encounters: type (SNOMED display), encounterClass (AMB/EMER/IMP), date, provider, "
        "location, reason (null if unknown)"
    )

    return "\n\n".join([
        _PERSONA,
        tier_instructions,
        summary_section,
        safety_section,
        format_section,
    ])


def build_system_prompt_deep(
    compiled_summary: dict[str, Any],
    patient_profile: str | None = None,
) -> str:
    """Build the Deep-tier system prompt for full clinical reasoning.

    Consumes the output of compile_patient_summary()
    directly, embedding the full structured summary in the prompt instead of
    formatting raw FHIR resources at prompt-build time.

    Structure:
      0. Shared persona (_PERSONA)
      1. Tier instructions (PCP reasoning approach)
      2. Pre-compiled patient summary (structured text)
      3. Agent reasoning directives
      4. Tool descriptions + usage guidance
      5. Safety constraints
      6. Response format

    Args:
        compiled_summary: Dict from compile_patient_summary().
        patient_profile: Optional non-clinical patient profile narrative.

    Returns:
        Formatted system prompt string.
    """
    # ── Section 1: Tier Instructions ──────────────────────────────────────────
    tier_instructions = (
        "For this query, act as an intelligent chart review partner. Reason through "
        "the clinical picture and retrieve additional data with your tools as needed.\n"
        "\n"
        "Clinical reasoning approach:\n"
        "- Think like a PCP: holistic, longitudinal, focused on the whole patient\n"
        "- Proactively surface cross-condition interactions and medication conflicts\n"
        "- Use FHIR IDs internally for tool calls, but never include them in your response\n"
        "- Flag when data is absent or the record may be incomplete — offer to search"
    )

    # ── Section 2: Pre-compiled Patient Summary ──────────────────────────────
    summary_section = _build_patient_summary_section(compiled_summary, patient_profile, tier=TIER_DEEP)

    # ── Section 3: Agent Reasoning Directives ────────────────────────────────
    reasoning_section = (
        "## Reasoning Directives\n"
        "\n"
        "Follow these reasoning principles when analyzing the patient record:\n"
        "\n"
        "1. **Absence reporting**: When asked about data that is NOT in the record, "
        "explicitly state it is absent from the record. Do not assume absence means "
        "normal — it may indicate a gap in documentation. Suggest using a tool to "
        "search for it.\n"
        "\n"
        "2. **Cross-condition reasoning**: Actively look for interactions between "
        "conditions, medications, and lab values. For example, if a patient has "
        "diabetes and is on a statin, note the relevance of liver function tests. "
        "Consider how one condition's treatment may affect another.\n"
        "\n"
        "3. **Tool-chain self-checking**: After receiving tool results, verify they "
        "answer the original question. If the results are insufficient or ambiguous, "
        "call another tool or refine your query rather than guessing. Chain tools "
        "when needed: e.g., find a condition ID, then explore_connections to see "
        "its treating medications.\n"
        "\n"
        "4. **Temporal awareness**: Pay attention to dates. Note when values are "
        "stale (>6 months old) and flag them. Consider whether recent changes "
        "in medications may explain lab trends.\n"
        "\n"
        "5. **Confidence calibration**: Distinguish between what is confirmed in "
        "the record vs what you are inferring. Use phrases like 'the record shows' "
        "for confirmed data and 'this may suggest' for clinical inference."
    )

    # ── Section 4: Tool Descriptions + Usage Guidance ────────────────────────
    tool_section = (
        "## Tools\n"
        "\n"
        "You have three tools to retrieve additional patient data on demand. "
        "Use them when the pre-compiled summary does not contain enough detail "
        "to fully answer the question. You can call multiple tools in a single "
        "round and make multiple rounds of calls.\n"
        "\n"
        "**Do NOT guess or fabricate clinical data — if you need it, call a tool.**\n"
        "\n"
        "### query_patient_data\n"
        "Search patient data by name, resource type, and filters. Performs exact "
        "matching with automatic semantic search fallback.\n"
        "- Use for: finding specific conditions, medications, observations, procedures\n"
        "- Example: search for all HbA1c results, or all active medications\n"
        "\n"
        "### explore_connections\n"
        "Explore graph connections from a specific FHIR resource by its ID. Returns "
        "related resources grouped by relationship type (TREATS, DIAGNOSED, PRESCRIBED, etc.).\n"
        "- Use for: understanding how a condition relates to medications, or what "
        "happened during an encounter\n"
        "- Tip: use a FHIR ID from the summary (e.g., a condition ID) as the starting point\n"
        "\n"
        "### get_patient_timeline\n"
        "Get the patient's encounter timeline, optionally filtered by date range. "
        "Shows encounters chronologically with associated events.\n"
        "- Use for: understanding visit history, what happened when, clinical notes\n"
        "\n"
        "### Important: Understanding enrichment fields in the summary\n"
        "\n"
        "**`_trend`**: Shows the direction of change and ONE previous value for an "
        "observation. This is a point-in-time comparison, not a full trend analysis. "
        "For multi-point trend analysis or to see the complete history of a lab value, "
        "use `query_patient_data` with the appropriate LOINC code or name.\n"
        "\n"
        "**`_dose_history`**: Shows recent dose changes for a medication. This captures "
        "only dose changes (not same-dose refills) and may not include the complete "
        "medication history. For the full prescribing history of a medication, "
        "use `query_patient_data` with resource_type='MedicationRequest'.\n"
        "\n"
        "**`_recency`**: Indicates how recently a medication was started "
        "('new' <30d, 'recent' <180d, 'established' >=180d).\n"
        "\n"
        "**`_inferred`**: When true, the medication-condition link was inferred via "
        "shared encounter traversal, not a direct TREATS relationship in the graph."
    )

    # ── Section 5: Safety Constraints ────────────────────────────────────────
    safety_section = _build_safety_section(compiled_summary)

    # ── Section 6: Response Format ───────────────────────────────────────────
    format_section = (
        "## Response Format\n"
        "Provide your response as a structured JSON object with:\n"
        "- thinking: Your reasoning process (optional, for transparency)\n"
        "- narrative: Main response in markdown format\n"
        "- insights: Important clinical insights to highlight (info, warning, critical, positive)\n"
        "- tables: Clinical data tables when presenting structured data (see Table Types below)\n"
        "- visualizations: Charts when data warrants visual trending (see Visualization Types below)\n"
        "- follow_ups: 2-3 SHORT follow-up questions (under 80 chars each) displayed as clickable chips\n"
        "\n"
        "## Table Types\n"
        "When your response includes structured clinical data, include a typed table.\n"
        "Use the row keys exactly as specified:\n"
        "\n"
        "medications: medication (full RxNorm string e.g. \"Lisinopril 10 MG Oral Tablet\"), "
        "frequency (e.g. \"1x daily\" or null), reason, status (active/completed), authoredOn, requester\n"
        "lab_results: test, value (number), unit, rangeLow (number), rangeHigh (number), "
        "interpretation (N/H/L/HH/LL — HL7 FHIR codes), date, history (array of {value: number, date: string} "
        "with last 6 readings). Optional: panel (string — group name e.g. \"Complete Blood Count (CBC)\"; "
        "rows sharing the same panel value render as a collapsible group).\n"
        "vitals: vital (LOINC display), value (display string e.g. \"128/82\"), "
        "numericValue (number — systolic for BP), unit, loinc, date. "
        "Optional: history (array of {value, date}), rangeLow (number), rangeHigh (number), "
        "interpretation (N/H/L/HH/LL). Only include range/history for vitals with clinical ranges "
        "(BP, HR, RR, BMI, Temp).\n"
        "conditions: condition, clinicalStatus (active/resolved), onsetDate, abatementDate (null for active)\n"
        "allergies: allergen, category (medication/food/environment), criticality (high/low), "
        "clinicalStatus (active/inactive), onsetDate\n"
        "immunizations: vaccine (CVX display), date, location\n"
        "procedures: procedure (SNOMED display), date, location, reason (null if unknown)\n"
        "encounters: type (SNOMED display), encounterClass (AMB/EMER/IMP), date, provider, "
        "location, reason (null if unknown)\n"
        "\n"
        "## Visualization Types\n"
        "\n"
        "trend_chart: For lab/vital trends over time.\n"
        "  Required: title, series (name, unit, data_points with date+value)\n"
        "  Header: current_value (latest reading), trend_summary (e.g., \"↓ 21% · Above Target\"), "
        "trend_status (positive/warning/critical/neutral)\n"
        "  Optional: reference_lines (value, label) for target thresholds\n"
        "  Optional: range_bands (y1, y2, severity, label?) for clinical staging zones "
        "(e.g., KDIGO eGFR bands, ADA HbA1c ranges). Severity: normal (green), warning (amber), "
        "critical (red).\n"
        "  Optional: medications (drug, segments with label+flex+active) for medication timeline "
        "aligned below chart — include when treatment changes correlate with the trend.\n"
        "  Auto-rendering: Single series without range_bands → area chart. With range_bands → "
        "line chart + colored zones. 2+ series → multi-line with legend.\n"
        "\n"
        "encounter_timeline: For chronological encounter view.\n"
        "  Provide events (date, title, detail, category where category is AMB/EMER/IMP)."
    )

    # ── Assemble ─────────────────────────────────────────────────────────────
    return "\n\n".join([
        _PERSONA,
        tier_instructions,
        summary_section,
        reasoning_section,
        tool_section,
        safety_section,
        format_section,
    ])


class AgentService:
    """LLM agent service for clinical reasoning with structured output.

    Uses OpenAI's Responses API with Pydantic structured outputs to generate
    type-safe responses with clinical insights, visualizations, and follow-ups.

    Example:
        agent = AgentService()

        response = await agent.generate_response(
            system_prompt=compiled_prompt,
            patient_id="uuid-here",
            message="What medications is this patient taking for diabetes?",
            history=[
                {"role": "user", "content": "Tell me about this patient"},
                {"role": "assistant", "content": "This is a 65-year-old..."},
            ],
        )

        print(response.narrative)
        for insight in response.insights or []:
            print(f"[{insight.type}] {insight.title}")
    """

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str = DEFAULT_MODEL,
        reasoning_effort: Literal["low", "medium", "high"] = DEFAULT_REASONING_EFFORT,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ):
        """Initialize AgentService.

        Args:
            client: Optional pre-configured AsyncOpenAI client (for testing).
                   If not provided, creates one from settings.
            model: Model to use for generation. Defaults to gpt-5.2.
            reasoning_effort: Reasoning effort level. Defaults to "low" for speed.
            max_output_tokens: Maximum tokens in response. Defaults to 4096.

        Raises:
            ValueError: If no client provided and OPENAI_API_KEY is not configured.
        """
        if client is not None:
            self._client = client
        else:
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Set it in your .env file or environment."
                )
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_output_tokens = max_output_tokens

    async def close(self) -> None:
        """Close the OpenAI client connection."""
        await self._client.close()

    @staticmethod
    def _append_response_output(kwargs: dict[str, Any], response: Any) -> None:
        """Append response output items to kwargs["input"], serializing SDK objects.

        SDK objects from .parse() carry extra fields (e.g. parsed_arguments)
        that the API rejects on re-send. This method serializes function_call
        items to plain dicts with only the required fields.
        """
        for item in response.output:
            if item.type == "function_call":
                kwargs["input"].append({
                    "type": "function_call",
                    "id": item.id,
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments,
                })
            else:
                kwargs["input"].append(item)

    async def _execute_tool_calls(
        self,
        kwargs: dict[str, Any],
        patient_id: str,
        graph: KnowledgeGraph,
        db: AsyncSession,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Execute tool-calling rounds, yielding SSE events for each tool interaction.

        After this returns, kwargs["input"] contains the full conversation
        including all tool calls and results, ready for a final call.

        Yields (event_type, data_json) tuples:
          - ("tool_call", json) when the LLM invokes a tool
          - ("tool_result", json) when a tool returns its result

        Args:
            kwargs: API call kwargs (mutated in place).
            patient_id: Current patient ID for tool execution.
            graph: KnowledgeGraph instance.
            db: AsyncSession instance.
        """
        for _round in range(MAX_TOOL_ROUNDS):
            round_start = time.perf_counter()
            response = await self._client.responses.parse(**kwargs)
            api_ms = (time.perf_counter() - round_start) * 1000

            tool_calls = [
                item for item in response.output
                if item.type == "function_call"
            ]
            if not tool_calls:
                usage = _extract_usage(response)
                logger.info(
                    "Tool round %d: no tool calls, responding directly (%.1fs, %s)",
                    _round + 1, api_ms / 1000, usage or "no usage",
                )
                kwargs.pop("tools", None)
                kwargs["_last_response"] = response
                return

            tool_names = [tc.name for tc in tool_calls]
            logger.info(
                "Tool round %d: %d call(s) %s (api=%.1fs)",
                _round + 1, len(tool_calls), tool_names, api_ms / 1000,
            )

            self._append_response_output(kwargs, response)

            for tool_call in tool_calls:
                yield ("tool_call", json.dumps({
                    "name": tool_call.name,
                    "call_id": tool_call.call_id,
                    "arguments": tool_call.arguments,
                }))

                exec_start = time.perf_counter()
                result = await execute_tool(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    patient_id=patient_id,
                    graph=graph,
                    db=db,
                )
                exec_ms = (time.perf_counter() - exec_start) * 1000
                result_len = len(result)
                logger.info(
                    "  tool %s: %.0fms, result=%d chars",
                    tool_call.name, exec_ms, result_len,
                )

                kwargs["input"].append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": result,
                })

                yield ("tool_result", json.dumps({
                    "call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "output": result,
                }))

        # Max rounds reached — remove tools to force text generation
        logger.info("Max tool rounds (%d) reached, forcing final response", MAX_TOOL_ROUNDS)
        kwargs.pop("tools", None)
        kwargs["_last_response"] = None

    @staticmethod
    def _build_input_messages(
        system_prompt: str,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build input messages from a pre-built system prompt string.

        Args:
            system_prompt: Complete system prompt string.
            message: Current user message.
            history: Optional conversation history.

        Returns:
            List of message dicts for the API.
        """
        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        return messages

    @staticmethod
    def _boost_effort(effort: str) -> str:
        """Bump reasoning effort up one level: low -> medium -> high."""
        return {"low": "medium", "medium": "high"}.get(effort, effort)

    async def generate_response(
        self,
        message: str,
        system_prompt: str,
        patient_id: str,
        history: list[dict[str, str]] | None = None,
        reasoning_boost: bool = False,
        graph: KnowledgeGraph | None = None,
        db: AsyncSession | None = None,
        query_profile: QueryProfile | None = None,
    ) -> AgentResponse:
        """Generate a structured response for a clinical question.

        Args:
            message: The user's question or message.
            system_prompt: Pre-built system prompt string from compiled summary.
            patient_id: Patient UUID string for tool execution.
            history: Optional list of previous messages in the conversation.
            reasoning_boost: If True, bump effort one level above the tier default.
            graph: KnowledgeGraph instance for tool execution.
            db: AsyncSession for tool execution.
            query_profile: Optional query profile from classifier. Controls
                reasoning effort, max tokens, and tool availability.

        Returns:
            AgentResponse with narrative, insights, visualizations, and follow-ups

        Raises:
            ValueError: If message is empty.
        """
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        t0 = time.perf_counter()
        input_messages = self._build_input_messages(system_prompt, message, history)

        # Resolution: tier default, optionally boosted one level
        base_effort = (query_profile.reasoning_effort if query_profile else None) or self._reasoning_effort
        effective_effort = self._boost_effort(base_effort) if reasoning_boost else base_effort
        effective_model = (query_profile.model if query_profile else None) or self._model
        effective_max_tokens = (query_profile.max_output_tokens if query_profile else None) or self._max_output_tokens
        use_reasoning = query_profile.reasoning if query_profile else True
        tools_available = graph is not None and db is not None
        include_tools = tools_available and (query_profile.include_tools if query_profile else True)
        response_schema_class = LightningResponse if (query_profile and query_profile.response_schema == "lightning") else AgentResponse
        prompt_chars = sum(len(m.get("content", "")) for m in input_messages)

        logger.info(
            "generate_response: model=%s, effort=%s, reasoning=%s, tools=%s, "
            "tier=%s, schema=%s, messages=%d, prompt_chars=%d (~%d tokens)",
            effective_model, effective_effort,
            "enabled" if use_reasoning else "disabled",
            "enabled" if include_tools else "disabled",
            query_profile.tier.value if query_profile else "default",
            response_schema_class.__name__,
            len(input_messages), prompt_chars, prompt_chars // 4,
        )

        kwargs: dict[str, Any] = {
            "model": effective_model,
            "input": input_messages,
            "text_format": response_schema_class,
            "max_output_tokens": effective_max_tokens,
        }
        # Only add reasoning for reasoning-capable models (gpt-4o-mini rejects it)
        if use_reasoning:
            kwargs["reasoning"] = Reasoning(effort=effective_effort, summary="concise")

        if include_tools:
            kwargs["tools"] = TOOL_SCHEMAS

            # Run tool rounds (discard SSE events — non-streaming path).
            # _execute_tool_calls stores the final non-tool response in kwargs.
            tool_rounds = 0
            async for _ in self._execute_tool_calls(
                kwargs, patient_id, graph, db
            ):
                tool_rounds += 1

        # Reuse the response from _execute_tool_calls if available,
        # otherwise make a fresh call (no tools path, or max rounds hit).
        response = kwargs.pop("_last_response", None)
        if response is None:
            response = await self._client.responses.parse(**kwargs)

        parsed_response = response.output_parsed

        if parsed_response is None:
            # Fallback: try to parse from raw output if structured parsing failed
            logger.warning("Structured parsing returned None, attempting fallback")
            raw_output = getattr(response, "output_text", None)
            if raw_output:
                parsed_response = response_schema_class.model_validate_json(raw_output)
            else:
                raise RuntimeError(
                    "LLM response could not be parsed. "
                    "Neither structured output nor raw text was available."
                )

        # Wrap LightningResponse into AgentResponse for uniform return type
        if isinstance(parsed_response, LightningResponse):
            agent_response = AgentResponse(
                narrative=parsed_response.narrative,
                tables=parsed_response.tables,
                follow_ups=parsed_response.follow_ups,
                needs_deeper_search=parsed_response.needs_deeper_search,
            )
        else:
            agent_response = parsed_response

        elapsed = time.perf_counter() - t0
        usage = _extract_usage(response)
        logger.info(
            "generate_response complete: %.1fs, usage=%s, "
            "insights=%d, follow_ups=%d",
            elapsed, usage or "n/a",
            len(agent_response.insights or []),
            len(agent_response.follow_ups or []),
        )

        return agent_response

    async def generate_response_stream(
        self,
        message: str,
        system_prompt: str,
        patient_id: str,
        history: list[dict[str, str]] | None = None,
        reasoning_boost: bool = False,
        graph: KnowledgeGraph | None = None,
        db: AsyncSession | None = None,
        query_profile: QueryProfile | None = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Stream a structured response, yielding deltas as they arrive.

        Yields (event_type, data_json) tuples:
          - ("reasoning", json) for reasoning summary text deltas
          - ("narrative", json) for output text deltas

        After all deltas, yields ("done", json) with the final parsed AgentResponse.

        Args:
            message: The user's question or message.
            system_prompt: Pre-built system prompt string from compiled summary.
            patient_id: Patient UUID string for tool execution.
            history: Optional conversation history.
            reasoning_boost: If True, bump effort one level above the tier default.
            graph: KnowledgeGraph instance for tool execution.
            db: AsyncSession for tool execution.
            query_profile: Optional query profile from classifier. Controls
                reasoning effort, max tokens, and tool availability.

        Raises:
            ValueError: If message is empty.
        """
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        t0 = time.perf_counter()
        input_messages = self._build_input_messages(system_prompt, message, history)

        # Resolution: tier default, optionally boosted one level
        base_effort = (query_profile.reasoning_effort if query_profile else None) or self._reasoning_effort
        effective_effort = self._boost_effort(base_effort) if reasoning_boost else base_effort
        effective_model = (query_profile.model if query_profile else None) or self._model
        effective_max_tokens = (query_profile.max_output_tokens if query_profile else None) or self._max_output_tokens
        use_reasoning = query_profile.reasoning if query_profile else True
        tools_available = graph is not None and db is not None
        include_tools = tools_available and (query_profile.include_tools if query_profile else True)
        response_schema_class = LightningResponse if (query_profile and query_profile.response_schema == "lightning") else AgentResponse
        prompt_chars = sum(len(m.get("content", "")) for m in input_messages)

        logger.info(
            "stream_response: model=%s, effort=%s, reasoning=%s, tools=%s, "
            "tier=%s, schema=%s, messages=%d, prompt_chars=%d (~%d tokens)",
            effective_model, effective_effort,
            "enabled" if use_reasoning else "disabled",
            "enabled" if include_tools else "disabled",
            query_profile.tier.value if query_profile else "default",
            response_schema_class.__name__,
            len(input_messages), prompt_chars, prompt_chars // 4,
        )

        kwargs: dict[str, Any] = {
            "model": effective_model,
            "input": input_messages,
            "text_format": response_schema_class,
            "max_output_tokens": effective_max_tokens,
        }
        # Only add reasoning for reasoning-capable models (gpt-4o-mini rejects it)
        if use_reasoning:
            kwargs["reasoning"] = Reasoning(effort=effective_effort, summary="concise")

        if include_tools:
            kwargs["tools"] = TOOL_SCHEMAS

        # Unified streaming loop: every API round uses responses.stream() so
        # text/reasoning deltas appear immediately (~5s TTFT) instead of waiting
        # for a blocking parse() call (~73s) before any output.
        first_token_time: float | None = None
        tool_events = 0

        for _round in range(MAX_TOOL_ROUNDS + 1):
            round_start = time.perf_counter()

            async with self._client.responses.stream(**kwargs) as stream:
                async for event in stream:
                    if event.type == "response.reasoning_summary_text.delta":
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        yield ("reasoning", json.dumps({"delta": event.delta}))
                    elif event.type == "response.output_text.delta":
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        yield ("narrative", json.dumps({"delta": event.delta}))

                final = await stream.get_final_response()

            api_ms = (time.perf_counter() - round_start) * 1000

            # Check if the model returned tool calls
            tool_calls = [
                item for item in final.output
                if item.type == "function_call"
            ]

            if not tool_calls:
                # No tool calls — this is the final response
                usage = _extract_usage(final)
                logger.info(
                    "Stream round %d: no tool calls, finalising (%.1fs, %s)",
                    _round + 1, api_ms / 1000, usage or "no usage",
                )

                parsed_response = final.output_parsed
                if parsed_response is None:
                    raw_output = getattr(final, "output_text", None)
                    if raw_output:
                        parsed_response = response_schema_class.model_validate_json(raw_output)
                    else:
                        raise RuntimeError(
                            "LLM response could not be parsed. "
                            "Neither structured output nor raw text was available."
                        )

                # Wrap LightningResponse into AgentResponse for uniform return type
                if isinstance(parsed_response, LightningResponse):
                    agent_response = AgentResponse(
                        narrative=parsed_response.narrative,
                        tables=parsed_response.tables,
                        follow_ups=parsed_response.follow_ups,
                    )
                else:
                    agent_response = parsed_response

                total_elapsed = time.perf_counter() - t0
                ttft = ((first_token_time - t0) * 1000) if first_token_time else None
                logger.info(
                    "stream_response complete: total=%.1fs, "
                    "ttft=%s, tool_events=%d, usage=%s, "
                    "insights=%d, follow_ups=%d",
                    total_elapsed,
                    f"{ttft:.0f}ms" if ttft else "n/a",
                    tool_events, usage or "n/a",
                    len(agent_response.insights or []),
                    len(agent_response.follow_ups or []),
                )

                yield ("done", agent_response.model_dump_json())
                return

            # Tool calls found — execute them and loop
            tool_names = [tc.name for tc in tool_calls]
            logger.info(
                "Stream round %d: %d tool call(s) %s (api=%.1fs)",
                _round + 1, len(tool_calls), tool_names, api_ms / 1000,
            )

            self._append_response_output(kwargs, final)

            for tool_call in tool_calls:
                yield ("tool_call", json.dumps({
                    "name": tool_call.name,
                    "call_id": tool_call.call_id,
                    "arguments": tool_call.arguments,
                }))
                tool_events += 1

                exec_start = time.perf_counter()
                result = await execute_tool(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    patient_id=patient_id,
                    graph=graph,
                    db=db,
                )
                exec_ms = (time.perf_counter() - exec_start) * 1000
                logger.info(
                    "  tool %s: %.0fms, result=%d chars",
                    tool_call.name, exec_ms, len(result),
                )

                kwargs["input"].append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": result,
                })

                yield ("tool_result", json.dumps({
                    "call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "output": result,
                }))
                tool_events += 1

        # Max rounds exhausted — strip tools and force a final streaming call
        logger.info("Max tool rounds (%d) reached, forcing final stream", MAX_TOOL_ROUNDS)
        kwargs.pop("tools", None)

        async with self._client.responses.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "response.reasoning_summary_text.delta":
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    yield ("reasoning", json.dumps({"delta": event.delta}))
                elif event.type == "response.output_text.delta":
                    if first_token_time is None:
                        first_token_time = time.perf_counter()
                    yield ("narrative", json.dumps({"delta": event.delta}))

            final = await stream.get_final_response()

        parsed_response = final.output_parsed
        if parsed_response is None:
            raw_output = getattr(final, "output_text", None)
            if raw_output:
                parsed_response = response_schema_class.model_validate_json(raw_output)
            else:
                raise RuntimeError(
                    "LLM response could not be parsed. "
                    "Neither structured output nor raw text was available."
                )

        # Wrap LightningResponse into AgentResponse for uniform return type
        if isinstance(parsed_response, LightningResponse):
            agent_response = AgentResponse(
                narrative=parsed_response.narrative,
                tables=parsed_response.tables,
                follow_ups=parsed_response.follow_ups,
                needs_deeper_search=parsed_response.needs_deeper_search,
            )
        else:
            agent_response = parsed_response

        total_elapsed = time.perf_counter() - t0
        ttft = ((first_token_time - t0) * 1000) if first_token_time else None
        usage = _extract_usage(final)
        logger.info(
            "stream_response complete (max rounds): total=%.1fs, "
            "ttft=%s, tool_events=%d, usage=%s, "
            "insights=%d, follow_ups=%d",
            total_elapsed,
            f"{ttft:.0f}ms" if ttft else "n/a",
            tool_events, usage or "n/a",
            len(agent_response.insights or []),
            len(agent_response.follow_ups or []),
        )

        yield ("done", agent_response.model_dump_json())
