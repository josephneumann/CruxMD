"""Patient data API routes for labs, medications, conditions, and timeline."""

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models import FhirResource

router = APIRouter(prefix="/patients", tags=["patient-data"])


# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


async def _verify_patient_exists(
    patient_id: uuid.UUID, db: AsyncSession
) -> FhirResource:
    """Verify patient exists and return the resource.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        db: Database session.

    Returns:
        The patient FhirResource.

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
    return patient


def _extract_date_from_resource(resource_data: dict) -> date | None:
    """Extract the relevant date from a FHIR resource for timeline ordering.

    Args:
        resource_data: The FHIR resource data.

    Returns:
        The extracted date or None if no date found.
    """
    resource_type = resource_data.get("resourceType", "")

    # Try common FHIR date fields in order of preference
    date_fields = []

    if resource_type == "Encounter":
        # period.start is most relevant for encounters
        period = resource_data.get("period", {})
        if period.get("start"):
            date_fields.append(period["start"])

    if resource_type == "Observation":
        date_fields.extend([
            resource_data.get("effectiveDateTime"),
            resource_data.get("effectivePeriod", {}).get("start"),
            resource_data.get("issued"),
        ])

    if resource_type == "Condition":
        date_fields.extend([
            resource_data.get("onsetDateTime"),
            resource_data.get("recordedDate"),
        ])

    if resource_type == "Procedure":
        date_fields.extend([
            resource_data.get("performedDateTime"),
            resource_data.get("performedPeriod", {}).get("start"),
        ])

    if resource_type == "MedicationRequest":
        date_fields.extend([
            resource_data.get("authoredOn"),
        ])

    if resource_type == "DiagnosticReport":
        date_fields.extend([
            resource_data.get("effectiveDateTime"),
            resource_data.get("effectivePeriod", {}).get("start"),
            resource_data.get("issued"),
        ])

    # Find first non-None date
    for date_str in date_fields:
        if date_str:
            try:
                # Handle both date and datetime formats
                return date.fromisoformat(date_str[:10])
            except (ValueError, TypeError):
                continue

    return None


def _get_loinc_codes_from_resource(resource_data: dict) -> list[str]:
    """Extract LOINC codes from an Observation resource.

    Args:
        resource_data: The FHIR Observation data.

    Returns:
        List of LOINC codes found in the resource.
    """
    codes = []
    code_data = resource_data.get("code", {})
    codings = code_data.get("coding", [])

    for coding in codings:
        system = coding.get("system", "")
        code = coding.get("code")
        if system == "http://loinc.org" and code:
            codes.append(code)

    return codes


def _get_clinical_status(resource_data: dict) -> str | None:
    """Extract clinical status from a FHIR resource.

    Args:
        resource_data: The FHIR resource data.

    Returns:
        The clinical status string or None.
    """
    resource_type = resource_data.get("resourceType", "")

    if resource_type == "Condition":
        clinical_status = resource_data.get("clinicalStatus", {})
        codings = clinical_status.get("coding", [])
        if codings:
            return codings[0].get("code")

    if resource_type == "MedicationRequest":
        return resource_data.get("status")

    if resource_type == "AllergyIntolerance":
        clinical_status = resource_data.get("clinicalStatus", {})
        codings = clinical_status.get("coding", [])
        if codings:
            return codings[0].get("code")

    return None


@router.get("/{patient_id}/labs")
async def get_patient_labs(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    codes: str | None = Query(
        None, description="Comma-separated LOINC codes to filter by"
    ),
    from_date: date | None = Query(
        None, alias="from", description="Start date (inclusive) ISO format"
    ),
    to_date: date | None = Query(
        None, alias="to", description="End date (inclusive) ISO format"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> dict:
    """Get lab results (Observations) for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        codes: Optional comma-separated LOINC codes to filter by.
        from_date: Optional start date filter (inclusive).
        to_date: Optional end date filter (inclusive).
        offset: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of Observation FHIR resources.
    """
    await _verify_patient_exists(patient_id, db)

    # Parse LOINC codes if provided
    loinc_codes = None
    if codes:
        loinc_codes = [c.strip() for c in codes.split(",") if c.strip()]

    # Query all Observations for this patient
    stmt = select(FhirResource).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Observation",
    )
    result = await db.execute(stmt)
    observations = result.scalars().all()

    # Filter in Python (JSONB queries can be complex)
    filtered = []
    for obs in observations:
        data = obs.data

        # Filter by LOINC codes if provided
        if loinc_codes:
            obs_loinc_codes = _get_loinc_codes_from_resource(data)
            if not any(code in loinc_codes for code in obs_loinc_codes):
                continue

        # Filter by date range
        obs_date = _extract_date_from_resource(data)
        if obs_date:
            if from_date and obs_date < from_date:
                continue
            if to_date and obs_date > to_date:
                continue

        filtered.append(obs)

    # Sort by date (most recent first)
    filtered.sort(
        key=lambda x: _extract_date_from_resource(x.data) or date.min,
        reverse=True,
    )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "items": [
            {
                "id": str(obs.id),
                "fhir_id": obs.fhir_id,
                "data": obs.data,
            }
            for obs in paginated
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{patient_id}/medications")
async def get_patient_medications(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    status: Literal["active", "all"] = Query(
        "all", description="Filter by medication status"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> dict:
    """Get medications for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        status: Filter by status - 'active' for current medications, 'all' for all.
        offset: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of MedicationRequest FHIR resources.
    """
    await _verify_patient_exists(patient_id, db)

    # Query MedicationRequest resources for this patient
    stmt = select(FhirResource).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "MedicationRequest",
    )
    result = await db.execute(stmt)
    medications = result.scalars().all()

    # Filter by status if needed
    filtered = []
    for med in medications:
        data = med.data

        if status == "active":
            med_status = _get_clinical_status(data)
            # FHIR MedicationRequest active statuses
            if med_status not in ("active", "on-hold"):
                continue

        filtered.append(med)

    # Sort by authoredOn date (most recent first)
    filtered.sort(
        key=lambda x: _extract_date_from_resource(x.data) or date.min,
        reverse=True,
    )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "items": [
            {
                "id": str(med.id),
                "fhir_id": med.fhir_id,
                "data": med.data,
            }
            for med in paginated
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/{patient_id}/conditions")
async def get_patient_conditions(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    status: Literal["active", "all"] = Query(
        "all", description="Filter by condition status"
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> dict:
    """Get conditions for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        status: Filter by status - 'active' for current conditions, 'all' for all.
        offset: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of Condition FHIR resources.
    """
    await _verify_patient_exists(patient_id, db)

    # Query Condition resources for this patient
    stmt = select(FhirResource).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type == "Condition",
    )
    result = await db.execute(stmt)
    conditions = result.scalars().all()

    # Filter by status if needed
    filtered = []
    for cond in conditions:
        data = cond.data

        if status == "active":
            cond_status = _get_clinical_status(data)
            # FHIR Condition active statuses
            if cond_status not in ("active", "recurrence", "relapse"):
                continue

        filtered.append(cond)

    # Sort by onset date (most recent first)
    filtered.sort(
        key=lambda x: _extract_date_from_resource(x.data) or date.min,
        reverse=True,
    )

    total = len(filtered)
    paginated = filtered[offset : offset + limit]

    return {
        "items": [
            {
                "id": str(cond.id),
                "fhir_id": cond.fhir_id,
                "data": cond.data,
            }
            for cond in paginated
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# Timeline resource types that can be included
TIMELINE_RESOURCE_TYPES = {
    "Encounter",
    "Condition",
    "Procedure",
    "MedicationRequest",
    "Observation",
    "DiagnosticReport",
}


@router.get("/{patient_id}/timeline")
async def get_patient_timeline(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    from_date: date | None = Query(
        None, alias="from", description="Start date (inclusive) ISO format"
    ),
    to_date: date | None = Query(
        None, alias="to", description="End date (inclusive) ISO format"
    ),
    types: str | None = Query(
        None,
        description="Comma-separated resource types to include (default: all)",
    ),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> dict:
    """Get a chronological timeline of clinical events for a patient.

    Aggregates Encounters, Conditions, Procedures, MedicationRequests,
    Observations, and DiagnosticReports in chronological order.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        from_date: Optional start date filter (inclusive).
        to_date: Optional end date filter (inclusive).
        types: Optional comma-separated resource types to include.
        offset: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of FHIR resources sorted by date.
    """
    await _verify_patient_exists(patient_id, db)

    # Parse resource types if provided
    requested_types = TIMELINE_RESOURCE_TYPES
    if types:
        requested_types = {
            t.strip() for t in types.split(",") if t.strip() in TIMELINE_RESOURCE_TYPES
        }
        if not requested_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid resource types. Valid types: {', '.join(sorted(TIMELINE_RESOURCE_TYPES))}",
            )

    # Query all requested resource types for this patient
    stmt = select(FhirResource).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type.in_(requested_types),
    )
    result = await db.execute(stmt)
    resources = result.scalars().all()

    # Filter by date range and add date for sorting
    timeline_items = []
    for resource in resources:
        data = resource.data
        resource_date = _extract_date_from_resource(data)

        # Filter by date range
        if resource_date:
            if from_date and resource_date < from_date:
                continue
            if to_date and resource_date > to_date:
                continue

        timeline_items.append((resource, resource_date))

    # Sort by date (most recent first), resources without dates go to the end
    timeline_items.sort(
        key=lambda x: (x[1] is None, x[1] or date.min),
        reverse=True,
    )

    total = len(timeline_items)
    paginated = timeline_items[offset : offset + limit]

    return {
        "items": [
            {
                "id": str(resource.id),
                "fhir_id": resource.fhir_id,
                "resource_type": resource.resource_type,
                "date": item_date.isoformat() if item_date else None,
                "data": resource.data,
            }
            for resource, item_date in paginated
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
