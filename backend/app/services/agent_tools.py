"""Agent tools for LLM function calling.

Each tool wraps graph/Postgres queries and returns formatted text
suitable for LLM consumption. Tools are designed to be called by the
agent mid-reasoning to fetch additional patient data.
"""

import json
import logging
from typing import Any

from sqlalchemy import select, and_, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph
from app.utils.fhir_helpers import extract_display_name, extract_observation_value

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Schemas (OpenAI function calling format)
# =============================================================================

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "search_patient_data",
        "description": (
            "Search patient data by concept name (e.g. 'diabetes', 'blood pressure', 'metformin'). "
            "Returns matching conditions, medications, observations, and other resources."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search terms to match against resource names.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_encounter_details",
        "description": (
            "Get all events from a specific encounter: conditions diagnosed, medications prescribed, "
            "observations recorded, procedures performed, and diagnostic reports. "
            "Use encounter FHIR IDs from search results or the patient timeline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "encounter_fhir_id": {
                    "type": "string",
                    "description": "The FHIR ID of the encounter.",
                },
            },
            "required": ["encounter_fhir_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_lab_history",
        "description": (
            "Get the history of a specific lab or observation over time, ordered by date. "
            "Use for trending lab values like 'Hemoglobin A1c', 'Glucose', 'Creatinine'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "lab_name": {
                    "type": "string",
                    "description": "Name of the lab or observation to look up.",
                },
            },
            "required": ["lab_name"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "find_related_resources",
        "description": (
            "Find resources related to a given resource via clinical relationships. "
            "For a Condition: finds treating medications and procedures. "
            "For a DiagnosticReport: finds component observations. "
            "For an Encounter: finds all associated events."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource_fhir_id": {
                    "type": "string",
                    "description": "FHIR ID of the source resource.",
                },
                "resource_type": {
                    "type": "string",
                    "description": "FHIR resource type (e.g. 'Condition', 'DiagnosticReport', 'Encounter').",
                },
            },
            "required": ["resource_fhir_id", "resource_type"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_patient_timeline",
        "description": (
            "Get the patient's encounter timeline, optionally filtered by date range. "
            "Shows encounters with their associated events (conditions, meds, observations, etc.)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": ["string", "null"],
                    "description": "Optional ISO date for range start (e.g. '2023-01-01').",
                },
                "end_date": {
                    "type": ["string", "null"],
                    "description": "Optional ISO date for range end (e.g. '2024-01-01').",
                },
            },
            "required": ["start_date", "end_date"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


async def execute_tool(
    name: str,
    arguments: str,
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
) -> str:
    """Execute a tool by name with JSON-encoded arguments.

    Args:
        name: Tool function name.
        arguments: JSON-encoded arguments from the LLM.
        patient_id: Current patient ID (injected, not from LLM).
        graph: KnowledgeGraph instance.
        db: AsyncSession for Postgres queries.

    Returns:
        Tool result as a plain text string.
    """
    args = json.loads(arguments)

    if name == "search_patient_data":
        return await search_patient_data(patient_id, args["query"], graph, db)
    elif name == "get_encounter_details":
        return await get_encounter_details(args["encounter_fhir_id"], graph)
    elif name == "get_lab_history":
        return await get_lab_history(patient_id, args["lab_name"], db)
    elif name == "find_related_resources":
        return await find_related_resources(
            args["resource_fhir_id"], args["resource_type"], graph
        )
    elif name == "get_patient_timeline":
        return await get_patient_timeline(
            patient_id, graph, args.get("start_date"), args.get("end_date")
        )
    else:
        return f"Unknown tool: {name}"


def _format_resource_summary(resource: dict[str, Any]) -> str:
    """Format a FHIR resource into a one-line summary for LLM consumption."""
    rtype = resource.get("resourceType", "Unknown")
    display = extract_display_name(resource)

    if rtype == "Encounter":
        types = resource.get("type", [{}])
        first_type = types[0] if types else {}
        codings = first_type.get("coding", [])
        display = codings[0].get("display") if codings else None
        period = resource.get("period", {})
        start = period.get("start", "")[:10]
        return f"Encounter: {display or 'Unknown type'} on {start}"

    if rtype == "Observation":
        value, unit = extract_observation_value(resource)
        date = (resource.get("effectiveDateTime") or "")[:10]
        val_str = f"{value} {unit}" if unit else str(value) if value is not None else "no value"
        return f"Observation: {display or 'Unknown'} = {val_str} ({date})"

    if rtype == "Condition":
        status_codings = resource.get("clinicalStatus", {}).get("coding", [])
        status = status_codings[0].get("code", "") if status_codings else ""
        onset = (resource.get("onsetDateTime") or "")[:10]
        parts = [f"Condition: {display or 'Unknown'}"]
        if status:
            parts.append(f"[{status}]")
        if onset:
            parts.append(f"onset {onset}")
        return " ".join(parts)

    if rtype == "MedicationRequest":
        status = resource.get("status", "")
        authored = (resource.get("authoredOn") or "")[:10]
        parts = [f"Medication: {display or 'Unknown'}"]
        if status:
            parts.append(f"[{status}]")
        if authored:
            parts.append(f"prescribed {authored}")
        return " ".join(parts)

    if rtype == "Procedure":
        performed = (resource.get("performedDateTime") or resource.get("performedPeriod", {}).get("start") or "")[:10]
        return f"Procedure: {display or 'Unknown'} on {performed}"

    if rtype == "DiagnosticReport":
        date = (resource.get("effectiveDateTime") or "")[:10]
        return f"Diagnostic Report: {display or 'Unknown'} ({date})"

    if rtype == "AllergyIntolerance":
        criticality = resource.get("criticality", "")
        crit_str = f" [{criticality} criticality]" if criticality else ""
        return f"Allergy: {display or 'Unknown'}{crit_str}"

    return f"{rtype}: {display or resource.get('id', 'Unknown')}"


async def search_patient_data(
    patient_id: str,
    query: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
) -> str:
    """Search patient data by concept name using graph node matching.

    Performs graph node search by display name matching. Returns formatted
    summaries of matching resources.

    Args:
        patient_id: Canonical patient UUID.
        query: Search terms (e.g. "diabetes", "blood pressure").
        graph: KnowledgeGraph instance.
        db: AsyncSession for Postgres queries.

    Returns:
        Formatted text describing matching resources.
    """
    try:
        terms = [t.strip() for t in query.split() if t.strip()]
        if not terms:
            return "No search terms provided."

        matches = await graph.search_nodes_by_name(patient_id, terms)

        if not matches:
            return f"No resources found matching '{query}' for this patient."

        fhir_ids = [m["fhir_id"] for m in matches]
        stmt = select(FhirResource).where(
            and_(
                FhirResource.patient_id == patient_id,
                FhirResource.fhir_id.in_(fhir_ids),
            )
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        resource_map: dict[str, dict[str, Any]] = {
            r.fhir_id: r.data for r in rows
        }

        lines = [f"Search results for '{query}' ({len(matches)} found):"]
        for match in matches:
            fhir_id = match["fhir_id"]
            rtype = match["resource_type"]
            data = resource_map.get(fhir_id)
            if data:
                lines.append(f"  - {_format_resource_summary(data)}")
            else:
                lines.append(f"  - {rtype} (id: {fhir_id})")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to search patient data for {patient_id}: {e}")
        return f"Error searching patient data: {e}"


async def get_encounter_details(
    encounter_fhir_id: str,
    graph: KnowledgeGraph,
) -> str:
    """Get details of a specific encounter and all associated events.

    Uses graph traversal to find conditions diagnosed, medications prescribed,
    observations recorded, procedures performed, and diagnostic reports.

    Args:
        encounter_fhir_id: FHIR ID of the encounter.
        graph: KnowledgeGraph instance.

    Returns:
        Formatted text describing the encounter and its events.
    """
    try:
        events = await graph.get_encounter_events(encounter_fhir_id)

        total = sum(len(v) for v in events.values())
        if total == 0:
            return f"No encounter found with ID '{encounter_fhir_id}', or encounter has no associated events."

        lines = [f"Encounter {encounter_fhir_id}:"]

        for category, resources in events.items():
            if not resources:
                continue
            label = category.replace("_", " ").title()
            lines.append(f"\n  {label}:")
            for r in resources:
                lines.append(f"    - {_format_resource_summary(r)}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get encounter details for {encounter_fhir_id}: {e}")
        return f"Error retrieving encounter details: {e}"


async def get_lab_history(
    patient_id: str,
    lab_name: str,
    db: AsyncSession,
    limit: int = 10,
) -> str:
    """Get history of a specific lab/observation by name, ordered by date.

    Queries Postgres for Observation resources matching the lab name
    using JSONB filtering, ordered by effective date descending.

    Args:
        patient_id: Canonical patient UUID.
        lab_name: Name of the lab/observation (e.g. "Hemoglobin A1c").
        db: AsyncSession for Postgres queries.
        limit: Maximum results to return (default 10).

    Returns:
        Formatted text with lab values over time.
    """
    try:
        stmt = (
            select(FhirResource)
            .where(
                and_(
                    FhirResource.patient_id == patient_id,
                    FhirResource.resource_type == "Observation",
                    func.lower(
                        FhirResource.data["code"]["coding"][0]["display"].astext
                    ).contains(lab_name.lower()),
                )
            )
            .order_by(
                FhirResource.data["effectiveDateTime"].astext.desc()
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = result.scalars().all()

        if not rows:
            return f"No lab results found matching '{lab_name}' for this patient."

        lines = [f"Lab history for '{lab_name}' ({len(rows)} results):"]
        for row in rows:
            obs = row.data
            value, unit = extract_observation_value(obs)
            date = (obs.get("effectiveDateTime") or "")[:10]
            val_str = f"{value} {unit}" if unit else str(value) if value is not None else "no value"
            display = extract_display_name(obs) or lab_name
            lines.append(f"  - {date}: {display} = {val_str}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get lab history for {patient_id}: {e}")
        return f"Error retrieving lab history: {e}"


async def find_related_resources(
    resource_fhir_id: str,
    resource_type: str,
    graph: KnowledgeGraph,
) -> str:
    """Find resources related to a given resource via graph traversal.

    Traverses graph relationships from the specified resource to find
    clinically related resources (e.g., medications treating a condition,
    observations in a diagnostic report).

    Args:
        resource_fhir_id: FHIR ID of the source resource.
        resource_type: FHIR resource type (e.g. "Condition", "DiagnosticReport").
        graph: KnowledgeGraph instance.

    Returns:
        Formatted text describing related resources.
    """
    try:
        lines = [f"Resources related to {resource_type} {resource_fhir_id}:"]
        found_any = False

        if resource_type == "Condition":
            meds = await graph.get_medications_treating_condition(resource_fhir_id)
            if meds:
                found_any = True
                lines.append("\n  Medications treating this condition:")
                for m in meds:
                    lines.append(f"    - {_format_resource_summary(m)}")

            procs = await graph.get_procedures_for_condition(resource_fhir_id)
            if procs:
                found_any = True
                lines.append("\n  Procedures for this condition:")
                for p in procs:
                    lines.append(f"    - {_format_resource_summary(p)}")

        elif resource_type == "DiagnosticReport":
            obs = await graph.get_diagnostic_report_results(resource_fhir_id)
            if obs:
                found_any = True
                lines.append("\n  Observations in this report:")
                for o in obs:
                    lines.append(f"    - {_format_resource_summary(o)}")

        elif resource_type == "Encounter":
            events = await graph.get_encounter_events(resource_fhir_id)
            for category, resources in events.items():
                if resources:
                    found_any = True
                    label = category.replace("_", " ").title()
                    lines.append(f"\n  {label}:")
                    for r in resources:
                        lines.append(f"    - {_format_resource_summary(r)}")

        if not found_any:
            return f"No related resources found for {resource_type} {resource_fhir_id}."

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to find related resources for {resource_type} {resource_fhir_id}: {e}")
        return f"Error finding related resources: {e}"


async def get_patient_timeline(
    patient_id: str,
    graph: KnowledgeGraph,
    start_date: str | None = None,
    end_date: str | None = None,
) -> str:
    """Get patient encounters in a date range, with associated events.

    Queries the graph for encounters, optionally filtered by date range,
    then retrieves events for each encounter.

    Args:
        patient_id: Canonical patient UUID.
        graph: KnowledgeGraph instance.
        start_date: Optional ISO date string for range start (inclusive).
        end_date: Optional ISO date string for range end (inclusive).

    Returns:
        Formatted timeline of encounters and their events.
    """
    try:
        encounters = await graph.get_patient_encounters(patient_id, start_date, end_date)

        date_range = ""
        if start_date or end_date:
            date_range = f" ({start_date or '...'} to {end_date or '...'})"

        if not encounters:
            return f"No encounters found for this patient{date_range}."

        lines = [f"Patient timeline{date_range} — {len(encounters)} encounters:"]

        for enc in encounters:
            date = (enc.get("period_start") or "")[:10]
            etype = enc.get("type_display") or "Unknown type"
            lines.append(f"\n  [{date}] {etype}")

            events = await graph.get_encounter_events(enc["fhir_id"])
            for category, resources in events.items():
                if resources:
                    for r in resources:
                        lines.append(f"    - {_format_resource_summary(r)}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to get patient timeline for {patient_id}: {e}")
        return f"Error retrieving patient timeline: {e}"
