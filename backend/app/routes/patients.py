"""Patient API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_bearer_token
from app.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_db
from app.models import FhirResource

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
async def list_patients(
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
) -> dict:
    """List patients with pagination.

    Args:
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return (max 100).

    Returns:
        Paginated list of patient resources with metadata.
    """
    # Enforce max page size
    limit = min(limit, MAX_PAGE_SIZE)

    # Get total count for pagination metadata
    count_stmt = select(FhirResource).where(FhirResource.resource_type == "Patient")
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    # Get paginated results
    stmt = (
        select(FhirResource)
        .where(FhirResource.resource_type == "Patient")
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    patients = result.scalars().all()

    return {
        "items": [
            {
                "id": str(patient.id),
                "fhir_id": patient.fhir_id,
                "data": patient.data,
            }
            for patient in patients
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/{patient_id}")
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> dict:
    """Get a single patient by ID.

    Args:
        patient_id: The PostgreSQL UUID of the patient.

    Returns:
        The patient resource data.

    Raises:
        HTTPException: 404 if patient not found.
    """
    stmt = select(FhirResource).where(
        FhirResource.id == patient_id,
        FhirResource.resource_type == "Patient",
    )
    result = await db.execute(stmt)
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    return {
        "id": str(patient.id),
        "fhir_id": patient.fhir_id,
        "data": patient.data,
    }
