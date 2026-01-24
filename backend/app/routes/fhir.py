"""FHIR API routes for loading bundles."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.services.fhir_loader import load_bundle as load_bundle_service
from app.services.graph import KnowledgeGraph

router = APIRouter(prefix="/fhir", tags=["fhir"])


class BundleLoadResponse(BaseModel):
    """Response from loading a FHIR bundle."""

    message: str
    resources_loaded: int
    patient_id: uuid.UUID | None = None


@router.post("/load-bundle", response_model=BundleLoadResponse)
async def load_bundle(
    bundle: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> BundleLoadResponse:
    """Load a FHIR Bundle into PostgreSQL and Neo4j.

    Uses the fhir_loader service to store resources in PostgreSQL (source of truth)
    and build the knowledge graph in Neo4j (derived view).

    Args:
        bundle: A FHIR Bundle resource.

    Returns:
        Summary of loaded resources.

    Raises:
        HTTPException: 400 if bundle is invalid.
    """
    # Validate bundle structure (fast-fail before service layer)
    if bundle.get("resourceType") != "Bundle":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bundle: resourceType must be 'Bundle'",
        )

    entries = bundle.get("entry", [])
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bundle: no entries found",
        )

    # Count valid resources for response
    resource_count = sum(
        1
        for entry in entries
        if entry.get("resource") and "resourceType" in entry.get("resource", {})
    )

    if resource_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bundle: no valid resources found",
        )

    # Delegate to service layer (handles PostgreSQL and Neo4j)
    graph = KnowledgeGraph()
    try:
        patient_id = await load_bundle_service(db, graph, bundle)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    finally:
        await graph.close()

    return BundleLoadResponse(
        message="Bundle loaded successfully",
        resources_loaded=resource_count,
        patient_id=patient_id,
    )
