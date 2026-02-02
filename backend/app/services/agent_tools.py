"""Agent tools for LLM function calling.

Each tool wraps graph/Postgres queries and returns formatted text
suitable for LLM consumption. Tools are designed to be called by the
agent mid-reasoning to fetch additional patient data.
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph
from app.utils.fhir_helpers import extract_display_name, extract_observation_value

logger = logging.getLogger(__name__)


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
    """Search patient data by concept name using graph + vector search.

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
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms:
        return "No search terms provided."

    # Search graph nodes by display name
    matches = await graph.search_nodes_by_name(patient_id, terms)

    if not matches:
        return f"No resources found matching '{query}' for this patient."

    # Fetch full FHIR resources from Postgres for matched fhir_ids
    fhir_ids = [m["fhir_id"] for m in matches]
    stmt = select(FhirResource).where(
        and_(
            FhirResource.patient_id == patient_id,
            FhirResource.fhir_id.in_(fhir_ids),
        )
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Build lookup by fhir_id
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
    events = await graph.get_encounter_events(encounter_fhir_id)

    # Check if encounter was found (all lists empty means no encounter or no events)
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


async def get_lab_history(
    patient_id: str,
    lab_name: str,
    db: AsyncSession,
    limit: int = 10,
) -> str:
    """Get history of a specific lab/observation by name, ordered by date.

    Queries Postgres for Observation resources matching the lab name,
    ordered by effective date descending.

    Args:
        patient_id: Canonical patient UUID.
        lab_name: Name of the lab/observation (e.g. "Hemoglobin A1c").
        db: AsyncSession for Postgres queries.
        limit: Maximum results to return (default 10).

    Returns:
        Formatted text with lab values over time.
    """
    # Use JSONB containment to find observations by display name (case-insensitive via ilike on embedding_text or JSONB)
    # More reliable: query all observations for patient, filter by display name in Python
    # For performance at scale, a JSONB index path query would be better, but this is sufficient for demo
    stmt = (
        select(FhirResource)
        .where(
            and_(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Observation",
            )
        )
        .order_by(FhirResource.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()

    lab_lower = lab_name.lower()
    matching = []
    for row in rows:
        display = extract_display_name(row.data)
        if display and lab_lower in display.lower():
            matching.append(row.data)
        if len(matching) >= limit:
            break

    if not matching:
        return f"No lab results found matching '{lab_name}' for this patient."

    # Sort by effectiveDateTime descending
    matching.sort(
        key=lambda r: r.get("effectiveDateTime", ""),
        reverse=True,
    )

    lines = [f"Lab history for '{lab_name}' ({len(matching)} results):"]
    for obs in matching:
        value, unit = extract_observation_value(obs)
        date = (obs.get("effectiveDateTime") or "")[:10]
        val_str = f"{value} {unit}" if unit else str(value) if value is not None else "no value"
        display = extract_display_name(obs) or lab_name
        lines.append(f"  - {date}: {display} = {val_str}")

    return "\n".join(lines)


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
    # Get all encounters for patient via graph search
    # Encounters are searched by type_display, but for timeline we want all
    # Use a broad search or direct Cypher query
    async with graph._driver.session() as session:
        # Build date filter
        where_clauses = ["TRUE"]
        params: dict[str, Any] = {"patient_id": patient_id}

        if start_date:
            where_clauses.append("e.period_start >= $start_date")
            params["start_date"] = start_date
        if end_date:
            where_clauses.append("e.period_start <= $end_date")
            params["end_date"] = end_date

        where = " AND ".join(where_clauses)
        result = await session.run(
            f"""
            MATCH (p:Patient {{id: $patient_id}})-[:HAS_ENCOUNTER]->(e:Encounter)
            WHERE {where}
            RETURN e.fhir_id as fhir_id, e.type_display as type_display,
                   e.period_start as period_start, e.period_end as period_end
            ORDER BY e.period_start DESC
            """,
            **params,
        )
        encounters = [record.data() async for record in result]

    if not encounters:
        date_range = ""
        if start_date or end_date:
            date_range = f" between {start_date or '...'} and {end_date or '...'}"
        return f"No encounters found for this patient{date_range}."

    lines = []
    date_range = ""
    if start_date or end_date:
        date_range = f" ({start_date or '...'} to {end_date or '...'})"
    lines.append(f"Patient timeline{date_range} — {len(encounters)} encounters:")

    for enc in encounters:
        date = (enc.get("period_start") or "")[:10]
        etype = enc.get("type_display") or "Unknown type"
        lines.append(f"\n  [{date}] {etype}")

        # Get events for this encounter
        events = await graph.get_encounter_events(enc["fhir_id"])
        for category, resources in events.items():
            if resources:
                label = category.replace("_", " ").title()
                for r in resources:
                    lines.append(f"    - {_format_resource_summary(r)}")

    return "\n".join(lines)
