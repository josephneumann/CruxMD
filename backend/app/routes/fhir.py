"""FHIR API routes for loading bundles."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models import FhirResource

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
    """Load a FHIR Bundle into the database.

    Extracts all resources from the bundle and stores them.
    Patient resources are stored first to get the patient_id
    for linking other resources.

    Args:
        bundle: A FHIR Bundle resource.

    Returns:
        Summary of loaded resources.

    Raises:
        HTTPException: 400 if bundle is invalid.
    """
    # Validate bundle structure
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

    # Extract resources from bundle entries
    resources = []
    for entry in entries:
        resource = entry.get("resource")
        if resource and "resourceType" in resource:
            resources.append(resource)

    if not resources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid bundle: no valid resources found",
        )

    # Sort resources so Patient comes first
    resources.sort(key=lambda r: 0 if r["resourceType"] == "Patient" else 1)

    # Track the patient ID for linking
    patient_db_id: uuid.UUID | None = None
    loaded_count = 0

    for resource in resources:
        resource_type = resource["resourceType"]
        fhir_id = resource.get("id", str(uuid.uuid4()))

        # Create the database record
        fhir_resource = FhirResource(
            fhir_id=fhir_id,
            resource_type=resource_type,
            patient_id=patient_db_id if resource_type != "Patient" else None,
            data=resource,
        )

        db.add(fhir_resource)
        await db.flush()  # Get the generated ID

        # Capture patient ID for linking subsequent resources
        if resource_type == "Patient":
            patient_db_id = fhir_resource.id

        loaded_count += 1

    return BundleLoadResponse(
        message="Bundle loaded successfully",
        resources_loaded=loaded_count,
        patient_id=patient_db_id,
    )
