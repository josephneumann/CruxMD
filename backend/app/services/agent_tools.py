"""Agent tools for LLM function calling.

Three tools that wrap graph/Postgres/vector queries and return pruned FHIR JSON
suitable for LLM consumption. Tools are designed to be called by the agent
mid-reasoning to fetch additional patient data.

Tools:
  1. query_patient_data  — search by name/filters with pgvector fallback
  2. explore_connections  — graph traversal from a single node
  3. get_patient_timeline — chronological encounter listing with events
"""

import json
import logging
from typing import Any

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

# Minimum exact results before triggering pgvector semantic fallback
_SEMANTIC_FALLBACK_THRESHOLD = 3

# Similarity threshold for pgvector semantic search (0-1)
_SEMANTIC_SIMILARITY_THRESHOLD = 0.4


# =============================================================================
# Tool Schemas (OpenAI function calling format)
# =============================================================================

SHOW_CLINICAL_TABLE_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "show_clinical_table",
    "description": (
        "Display a clinical data table to the user. Use this when your response "
        "would benefit from showing structured data (medications list, lab results, "
        "conditions, etc.). The table is generated deterministically from the patient "
        "record — you do NOT need to populate the data."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "table_type": {
                "type": "string",
                "enum": [
                    "medications", "lab_results", "vitals", "conditions",
                    "allergies", "immunizations", "procedures", "encounters",
                ],
                "description": "Type of clinical data table to display.",
            },
            "status": {
                "type": ["string", "null"],
                "description": (
                    "Filter by status (e.g., 'active', 'completed'). "
                    "Applies to medications and conditions. Optional."
                ),
            },
            "codes": {
                "type": ["array", "null"],
                "items": {"type": "string"},
                "description": "LOINC codes for lab/vital filtering. Optional.",
            },
            "panel": {
                "type": ["string", "null"],
                "description": "Panel name for lab grouping (e.g., 'CBC', 'BMP'). Optional.",
            },
        },
        "required": ["table_type", "status", "codes", "panel"],
        "additionalProperties": False,
    },
    "strict": True,
}

SHOW_CLINICAL_CHART_SCHEMA: dict[str, Any] = {
    "type": "function",
    "name": "show_clinical_chart",
    "description": (
        "Display a clinical chart to the user. Use for trending lab values, "
        "vital signs over time, or encounter timelines. The chart is generated "
        "deterministically from the patient record — you do NOT need to "
        "populate the data."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "enum": ["trend_chart", "encounter_timeline"],
                "description": "Type of clinical chart to display.",
            },
            "loinc_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "LOINC codes to trend (REQUIRED for trend_chart). "
                    "Common codes: Weight=29463-7, BMI=39156-5, "
                    "BP=85354-9, Heart Rate=8867-4, Resp Rate=9279-1, "
                    "Cholesterol=2093-3, LDL=18262-6, HDL=2085-9, "
                    "Triglycerides=2571-8, HbA1c=4548-4, eGFR=33914-3, "
                    "Creatinine=2160-0, Glucose=2345-7, Hemoglobin=718-7, "
                    "WBC=6690-2, Platelets=777-3. "
                    "Always provide at least one LOINC code."
                ),
            },
            "time_range": {
                "type": ["string", "null"],
                "description": (
                    "Time range filter like '1y', '6m', '3m'. "
                    "Pass null to show ALL available data (recommended default)."
                ),
            },
        },
        "required": ["chart_type", "loinc_codes", "time_range"],
        "additionalProperties": False,
    },
    "strict": True,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "query_patient_data",
        "description": (
            "Search patient data by name, resource type, and attribute filters. "
            "Use for finding conditions, medications, observations, procedures, "
            "and other clinical data. Performs exact name matching with automatic "
            "semantic search fallback when few results are found."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional FHIR resource type filter (e.g. 'Condition', "
                        "'MedicationRequest', 'Observation')."
                    ),
                },
                "name": {
                    "type": ["string", "null"],
                    "description": (
                        "Search term to match against resource display names "
                        "(e.g. 'diabetes', 'hemoglobin', 'lisinopril')."
                    ),
                },
                "status": {
                    "type": ["string", "null"],
                    "description": (
                        "Filter by clinical/request status "
                        "(e.g. 'active', 'completed', 'resolved')."
                    ),
                },
                "category": {
                    "type": ["string", "null"],
                    "description": (
                        "Filter by category code "
                        "(e.g. 'laboratory', 'vital-signs' for Observations)."
                    ),
                },
                "date_from": {
                    "type": ["string", "null"],
                    "description": "Optional ISO date for range start (e.g. '2023-01-01').",
                },
                "date_to": {
                    "type": ["string", "null"],
                    "description": "Optional ISO date for range end (e.g. '2024-01-01').",
                },
                "include_full_resource": {
                    "type": ["boolean", "null"],
                    "description": (
                        "Whether to include pruned FHIR JSON for each result. "
                        "Defaults to true."
                    ),
                },
                "limit": {
                    "type": ["integer", "null"],
                    "description": "Maximum number of results to return. Defaults to 20.",
                },
            },
            "required": [
                "resource_type", "name", "status", "category",
                "date_from", "date_to", "include_full_resource", "limit",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "explore_connections",
        "description": (
            "Explore all graph connections from a specific FHIR resource. "
            "Returns related resources grouped by relationship type "
            "(e.g. TREATS, DIAGNOSED, PRESCRIBED). Use to understand how a "
            "resource (Condition, Encounter, etc.) relates to other clinical data. "
            "DocumentReferences include decoded clinical note text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fhir_id": {
                    "type": "string",
                    "description": "FHIR ID of the resource to explore from.",
                },
                "resource_type": {
                    "type": ["string", "null"],
                    "description": (
                        "Optional FHIR resource type of the source node. "
                        "Provided for context but not required for traversal."
                    ),
                },
                "include_full_resource": {
                    "type": ["boolean", "null"],
                    "description": (
                        "Whether to include pruned FHIR JSON for each connected "
                        "resource. Defaults to true."
                    ),
                },
                "max_per_relationship": {
                    "type": ["integer", "null"],
                    "description": (
                        "Maximum resources per relationship type. Defaults to 10."
                    ),
                },
            },
            "required": [
                "fhir_id", "resource_type", "include_full_resource",
                "max_per_relationship",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_patient_timeline",
        "description": (
            "Get the patient's encounter timeline, optionally filtered by date range. "
            "Shows encounters chronologically with associated events (conditions, "
            "medications, observations, procedures). Optionally includes clinical "
            "note text from DocumentReferences."
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
                "include_notes": {
                    "type": ["boolean", "null"],
                    "description": (
                        "Whether to include clinical note text from DocumentReferences "
                        "linked to each encounter. Defaults to false."
                    ),
                },
            },
            "required": ["start_date", "end_date", "include_notes"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    SHOW_CLINICAL_TABLE_SCHEMA,
    SHOW_CLINICAL_CHART_SCHEMA,
]


async def execute_tool(
    name: str,
    arguments: str,
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
    generated_tables: list[dict[str, Any]] | None = None,
    generated_visualizations: list[dict[str, Any]] | None = None,
) -> str:
    """Execute a tool by name with JSON-encoded arguments.

    Args:
        name: Tool function name.
        arguments: JSON-encoded arguments from the LLM.
        patient_id: Current patient ID (injected, not from LLM).
        graph: KnowledgeGraph instance.
        db: AsyncSession for Postgres queries.
        generated_tables: Optional side-channel list. When show_clinical_table
            is called, the generated table dict is appended here so it can
            be attached to the final API response.
        generated_visualizations: Optional side-channel list. When
            show_clinical_chart is called, the generated visualization dict
            is appended here so it can be attached to the final API response.

    Returns:
        Tool result as a JSON string.
    """
    args = json.loads(arguments)

    # Handle show_clinical_table specially — generates table via side channel
    if name == "show_clinical_table":
        return await _execute_show_clinical_table(
            args, patient_id, db, generated_tables,
        )

    # Handle show_clinical_chart specially — generates chart via side channel
    if name == "show_clinical_chart":
        return await _execute_show_clinical_chart(
            args, patient_id, db, generated_visualizations,
        )

    handlers = {
        "query_patient_data": lambda: query_patient_data(
            patient_id=patient_id,
            db=db,
            graph=graph,
            resource_type=args.get("resource_type"),
            name=args.get("name"),
            status=args.get("status"),
            category=args.get("category"),
            date_from=args.get("date_from"),
            date_to=args.get("date_to"),
            include_full_resource=args.get("include_full_resource", True),
            limit=args.get("limit", 20),
        ),
        "explore_connections": lambda: explore_connections(
            fhir_id=args["fhir_id"],
            patient_id=patient_id,
            graph=graph,
            db=db,
            resource_type=args.get("resource_type"),
            include_full_resource=args.get("include_full_resource", True),
            max_per_relationship=args.get("max_per_relationship", 10),
        ),
        "get_patient_timeline": lambda: get_patient_timeline(
            patient_id=patient_id,
            graph=graph,
            db=db,
            start_date=args.get("start_date"),
            end_date=args.get("end_date"),
            include_notes=args.get("include_notes", False),
        ),
    }

    handler = handlers.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return await handler()


async def _execute_show_clinical_table(
    args: dict[str, Any],
    patient_id: str,
    db: AsyncSession,
    generated_tables: list[dict[str, Any]] | None,
) -> str:
    """Execute show_clinical_table: build table and store in side channel."""
    import uuid
    from app.services.table_builder import build_table_for_type

    table_type = args.get("table_type", "")
    try:
        table = await build_table_for_type(
            table_type=table_type,
            patient_id=uuid.UUID(patient_id),
            db=db,
            status=args.get("status"),
            codes=args.get("codes"),
            panel=args.get("panel"),
        )
    except Exception as e:
        logger.error("show_clinical_table failed: %s", e)
        return json.dumps({"error": f"Failed to generate {table_type} table: {e}"})

    if table is None:
        return json.dumps({
            "displayed": False,
            "message": f"No {table_type} data found for this patient.",
        })

    # Store in side channel for attachment to final response
    if generated_tables is not None:
        generated_tables.append(table)

    row_count = len(table.get("rows", []))
    return json.dumps({
        "displayed": True,
        "message": f"Table displayed: {table['title']} ({row_count} rows)",
    })


async def _execute_show_clinical_chart(
    args: dict[str, Any],
    patient_id: str,
    db: AsyncSession,
    generated_visualizations: list[dict[str, Any]] | None,
) -> str:
    """Execute show_clinical_chart: build chart and store in side channel."""
    import uuid
    from app.services.chart_builder import build_chart_for_type

    chart_type = args.get("chart_type", "")
    loinc_codes = args.get("loinc_codes")
    logger.info(
        "show_clinical_chart called: chart_type=%s, loinc_codes=%s, time_range=%s",
        chart_type, loinc_codes, args.get("time_range"),
    )
    try:
        chart = await build_chart_for_type(
            chart_type=chart_type,
            patient_id=uuid.UUID(patient_id),
            db=db,
            loinc_codes=args.get("loinc_codes"),
            time_range=args.get("time_range"),
        )
    except Exception as e:
        logger.error("show_clinical_chart failed: %s", e)
        return json.dumps({"error": f"Failed to generate {chart_type} chart: {e}"})

    if chart is None:
        return json.dumps({
            "displayed": False,
            "message": f"No data found for {chart_type} chart.",
        })

    # Store in side channel for attachment to final response
    if generated_visualizations is not None:
        generated_visualizations.append(chart)

    title = chart.get("title", chart_type)
    data_points = 0
    for series in (chart.get("series") or []):
        data_points += len(series.get("data_points") or [])
    for event in (chart.get("events") or []):
        data_points += 1

    return json.dumps({
        "displayed": True,
        "message": f"Chart displayed: {title} ({data_points} data points)",
    })


# =============================================================================
# Tool 1: query_patient_data
# =============================================================================


async def query_patient_data(
    patient_id: str,
    db: AsyncSession,
    graph: KnowledgeGraph,
    resource_type: str | None = None,
    name: str | None = None,
    status: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    include_full_resource: bool = True,
    limit: int = 20,
) -> str:
    """Search patient data with exact name matching and optional semantic fallback.

    Primary: Postgres ILIKE on embedding_text + attribute filters.
    Fallback: If <3 results and a name was provided, runs pgvector semantic
    search (threshold 0.4) to find semantically similar resources.

    Results are labeled by source ("exact" vs "semantic").
    Returns pruned FHIR JSON.
    """
    try:
        limit = min(max(1, limit), 100)
        exact_results = await _query_exact(
            patient_id=patient_id,
            db=db,
            resource_type=resource_type,
            name=name,
            status=status,
            category=category,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

        # Label exact results
        results: list[dict[str, Any]] = []
        seen_fhir_ids: set[str] = set()
        for row in exact_results:
            entry = _format_result_entry(row, "exact", include_full_resource)
            results.append(entry)
            seen_fhir_ids.add(row.fhir_id)

        # Semantic fallback: if <3 exact results and name was provided
        semantic_results: list[dict[str, Any]] = []
        if name and len(exact_results) < _SEMANTIC_FALLBACK_THRESHOLD:
            semantic_results = await _query_semantic(
                patient_id=patient_id,
                db=db,
                name=name,
                resource_type=resource_type,
                limit=limit - len(exact_results),
                seen_fhir_ids=seen_fhir_ids,
            )
            results.extend(semantic_results)

        if not results:
            return json.dumps({
                "results": [],
                "total": 0,
                "message": "No results found for the given criteria.",
            })

        return json.dumps({
            "results": results,
            "total": len(results),
            "exact_count": len(exact_results),
            "semantic_count": len(semantic_results),
        })

    except Exception as e:
        logger.error(f"query_patient_data failed for {patient_id}: {e}")
        return json.dumps({"error": f"Error searching patient data: {e}"})


async def _query_exact(
    patient_id: str,
    db: AsyncSession,
    resource_type: str | None = None,
    name: str | None = None,
    status: str | None = None,
    category: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
) -> list:
    """Run Postgres ILIKE query on embedding_text with attribute filters."""
    conditions = [FhirResource.patient_id == patient_id]

    if resource_type:
        conditions.append(FhirResource.resource_type == resource_type)

    if name:
        # Escape SQL LIKE wildcards in user-provided search term
        safe_name = name.replace("%", r"\%").replace("_", r"\_")
        conditions.append(
            FhirResource.embedding_text.ilike(f"%{safe_name}%")
        )

    if status:
        # Status can be in clinicalStatus.coding[0].code or status field
        conditions.append(
            func.coalesce(
                FhirResource.data["clinicalStatus"]["coding"][0]["code"].astext,
                FhirResource.data["status"].astext,
            ).ilike(f"%{status}%")
        )

    if category:
        conditions.append(
            FhirResource.data["category"][0]["coding"][0]["code"].astext.ilike(
                f"%{category}%"
            )
        )

    if date_from:
        # Check multiple date fields
        conditions.append(
            func.coalesce(
                FhirResource.data["effectiveDateTime"].astext,
                FhirResource.data["onsetDateTime"].astext,
                FhirResource.data["authoredOn"].astext,
                FhirResource.data["period"]["start"].astext,
            ) >= date_from
        )

    if date_to:
        conditions.append(
            func.coalesce(
                FhirResource.data["effectiveDateTime"].astext,
                FhirResource.data["onsetDateTime"].astext,
                FhirResource.data["authoredOn"].astext,
                FhirResource.data["period"]["start"].astext,
            ) <= date_to
        )

    stmt = (
        select(FhirResource)
        .where(and_(*conditions))
        .limit(limit)
    )

    result = await db.execute(stmt)
    return result.scalars().all()


async def _query_semantic(
    patient_id: str,
    db: AsyncSession,
    name: str,
    resource_type: str | None = None,
    limit: int = 20,
    seen_fhir_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Run pgvector semantic search as fallback.

    Uses VectorSearchService.search_by_text with EmbeddingService.embed_text.
    """
    try:
        from app.services.compiler import prune_and_enrich
        from app.services.embeddings import EmbeddingService
        from app.services.vector_search import VectorSearchService

        embedding_service = EmbeddingService()
        vector_service = VectorSearchService(db)

        search_results = await vector_service.search_by_text(
            patient_id=patient_id,
            query_text=name,
            embed_fn=embedding_service.embed_text,
            limit=limit,
            threshold=_SEMANTIC_SIMILARITY_THRESHOLD,
        )

        await embedding_service.close()

        results: list[dict[str, Any]] = []
        for sr in search_results:
            if seen_fhir_ids and sr.fhir_id in seen_fhir_ids:
                continue
            if resource_type and sr.resource_type != resource_type:
                continue
            entry: dict[str, Any] = {
                "source": "semantic",
                "fhir_id": sr.fhir_id,
                "resource_type": sr.resource_type,
                "similarity_score": round(sr.score, 3),
                "resource": prune_and_enrich(sr.resource),
            }
            results.append(entry)

        return results

    except Exception as e:
        logger.warning(f"Semantic fallback failed: {e}")
        return []


def _format_result_entry(
    row: FhirResource,
    source: str,
    include_full_resource: bool,
) -> dict[str, Any]:
    """Format a FhirResource row into a result entry."""
    entry: dict[str, Any] = {
        "source": source,
        "fhir_id": row.fhir_id,
        "resource_type": row.resource_type,
    }
    if include_full_resource:
        from app.services.compiler import prune_and_enrich
        entry["resource"] = prune_and_enrich(row.data)
    return entry


# =============================================================================
# Tool 2: explore_connections
# =============================================================================


async def explore_connections(
    fhir_id: str,
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
    resource_type: str | None = None,
    include_full_resource: bool = True,
    max_per_relationship: int = 10,
) -> str:
    """Explore all graph connections from a node using compile_node_context.

    Returns pruned FHIR JSON grouped by relationship type (e.g. TREATS,
    DIAGNOSED, PRESCRIBED). DocumentReferences include decoded note text
    (handled by the pruner).
    """
    try:
        from app.services.compiler import compile_node_context

        grouped = await compile_node_context(
            fhir_id=fhir_id,
            patient_id=patient_id,
            graph=graph,
            db=db,
        )

        if not grouped:
            return json.dumps({
                "fhir_id": fhir_id,
                "resource_type": resource_type,
                "connections": {},
                "total": 0,
                "message": f"No connections found for {resource_type or 'resource'} {fhir_id}.",
            })

        # Apply max_per_relationship limit and optionally strip full resource
        connections: dict[str, list[dict[str, Any]]] = {}
        total = 0
        for rel_type, resources in grouped.items():
            trimmed = resources[:max_per_relationship]
            if not include_full_resource:
                # Strip to just fhir_id and resourceType
                trimmed = [
                    {
                        "fhir_id": r.get("id"),
                        "resource_type": r.get("resourceType"),
                    }
                    for r in trimmed
                ]
            connections[rel_type] = trimmed
            total += len(trimmed)

        return json.dumps({
            "fhir_id": fhir_id,
            "resource_type": resource_type,
            "connections": connections,
            "total": total,
        })

    except Exception as e:
        logger.error(f"explore_connections failed for {fhir_id}: {e}")
        return json.dumps({"error": f"Error exploring connections: {e}"})


# =============================================================================
# Tool 3: get_patient_timeline
# =============================================================================


async def get_patient_timeline(
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
    include_notes: bool = False,
) -> str:
    """Get patient encounter timeline with events, optionally including notes.

    Queries Neo4j for encounters, then uses get_encounter_events for each.
    When include_notes=true, fetches DocumentReference via DOCUMENTED edge
    and decodes clinical note text.
    """
    try:
        from app.services.compiler import prune_and_enrich

        encounters = await graph.get_patient_encounters(
            patient_id, start_date, end_date
        )

        if not encounters:
            date_range = ""
            if start_date or end_date:
                date_range = f" ({start_date or '...'} to {end_date or '...'})"
            return json.dumps({
                "encounters": [],
                "total": 0,
                "message": f"No encounters found for this patient{date_range}.",
            })

        # Collect all encounter fhir_ids for batch resource fetch
        encounter_fhir_ids = [e["fhir_id"] for e in encounters]

        # Batch-fetch encounter FHIR resources from Postgres for pruning
        enc_stmt = select(FhirResource.fhir_id, FhirResource.data).where(
            FhirResource.patient_id == patient_id,
            FhirResource.fhir_id.in_(encounter_fhir_ids),
            FhirResource.resource_type == "Encounter",
        )
        enc_result = await db.execute(enc_stmt)
        enc_resources = {row.fhir_id: row.data for row in enc_result.all()}

        timeline: list[dict[str, Any]] = []

        for enc in encounters:
            enc_fhir_id = enc["fhir_id"]
            events = await graph.get_encounter_events(enc_fhir_id)

            # Build event groups with pruned FHIR JSON
            event_groups: dict[str, list[dict[str, Any]]] = {}
            all_event_fhir_ids: list[str] = []

            for event_type, event_resources in events.items():
                if not event_resources:
                    continue
                for r in event_resources:
                    fid = r.get("id")
                    if fid:
                        all_event_fhir_ids.append(fid)

            # Batch-fetch event resources from Postgres for pruning
            event_resource_map: dict[str, dict[str, Any]] = {}
            if all_event_fhir_ids:
                ev_stmt = select(FhirResource.fhir_id, FhirResource.data).where(
                    FhirResource.fhir_id.in_(all_event_fhir_ids),
                )
                ev_result = await db.execute(ev_stmt)
                event_resource_map = {
                    row.fhir_id: row.data for row in ev_result.all()
                }

            for event_type, event_resources in events.items():
                if not event_resources:
                    continue
                # Skip document_references unless include_notes is set
                if event_type == "document_references" and not include_notes:
                    continue

                pruned_events = []
                for r in event_resources:
                    fid = r.get("id")
                    # Use the Postgres canonical data for pruning when available
                    pg_data = event_resource_map.get(fid) if fid else None
                    data = pg_data if pg_data else r
                    pruned_events.append(prune_and_enrich(data))

                event_groups[event_type] = pruned_events

            # Build encounter entry
            enc_data = enc_resources.get(enc_fhir_id)
            enc_entry: dict[str, Any] = {
                "fhir_id": enc_fhir_id,
                "date": (enc.get("period_start") or "")[:10],
                "type": enc.get("type_display") or "Unknown",
                "events": event_groups,
            }
            if enc_data:
                enc_entry["encounter"] = prune_and_enrich(enc_data)

            timeline.append(enc_entry)

        return json.dumps({
            "encounters": timeline,
            "total": len(timeline),
        })

    except Exception as e:
        logger.error(f"get_patient_timeline failed for {patient_id}: {e}")
        return json.dumps({"error": f"Error retrieving patient timeline: {e}"})
