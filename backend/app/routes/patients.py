"""Patient API routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models import FhirResource

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
async def list_patients(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> list[dict]:
    """List all patients.

    Returns a list of patient resources with basic info.
    """
    stmt = select(FhirResource).where(FhirResource.resource_type == "Patient")
    result = await db.execute(stmt)
    patients = result.scalars().all()

    return [
        {
            "id": str(patient.id),
            "fhir_id": patient.fhir_id,
            "data": patient.data,
        }
        for patient in patients
    ]


@router.get("/{patient_id}")
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
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
