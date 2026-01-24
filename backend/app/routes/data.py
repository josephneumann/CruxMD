"""Patient data API routes for labs, medications, conditions, and timeline."""

import uuid
from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models import FhirResource

router = APIRouter(prefix="/patients", tags=["patient-data"])


# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Clinical status constants
ACTIVE_MEDICATION_STATUSES = {"active", "on-hold"}
ACTIVE_CONDITION_STATUSES = {"active", "recurrence", "relapse"}

# Timeline resource types that can be included
TIMELINE_RESOURCE_TYPES = {
    "Encounter",
    "Condition",
    "Procedure",
    "MedicationRequest",
    "Observation",
    "DiagnosticReport",
}


# =============================================================================
# Response Models
# =============================================================================


class FhirResourceItem(BaseModel):
    """A FHIR resource item in paginated response."""

    id: str
    fhir_id: str
    data: dict[str, Any]


class TimelineResourceItem(BaseModel):
    """A timeline resource item with extracted date."""

    id: str
    fhir_id: str
    resource_type: str
    date: str | None
    data: dict[str, Any]


class PaginatedFhirResponse(BaseModel):
    """Paginated response for FHIR resources."""

    items: list[FhirResourceItem]
    total: int
    skip: int
    limit: int


class PaginatedTimelineResponse(BaseModel):
    """Paginated response for timeline resources."""

    items: list[TimelineResourceItem]
    total: int
    skip: int
    limit: int


# =============================================================================
# Dependencies
# =============================================================================


async def get_verified_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> uuid.UUID:
    """Verify patient exists and return the patient_id.

    This is a FastAPI dependency that handles both auth and patient verification.

    Args:
        patient_id: PostgreSQL UUID of the patient.
        db: Database session.

    Returns:
        The verified patient_id (same as input if valid).

    Raises:
        HTTPException: 404 if patient not found, 401 if auth fails.
    """
    stmt = select(FhirResource.id).where(
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
    return patient_id


# Type alias for verified patient dependency
VerifiedPatient = Annotated[uuid.UUID, Depends(get_verified_patient)]


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_date_from_resource(resource_data: dict) -> date | None:
    """Extract the relevant date from a FHIR resource for timeline ordering.

    Uses early return pattern for efficiency.

    Args:
        resource_data: The FHIR resource data.

    Returns:
        The extracted date or None if no date found.
    """
    resource_type = resource_data.get("resourceType", "")

    def _parse_date(date_str: str | None) -> date | None:
        if not date_str:
            return None
        try:
            return date.fromisoformat(date_str[:10])
        except (ValueError, TypeError):
            return None

    # Early return pattern - avoid list building
    if resource_type == "Encounter":
        if dt := resource_data.get("period", {}).get("start"):
            return _parse_date(dt)

    if resource_type == "Observation":
        if dt := resource_data.get("effectiveDateTime"):
            return _parse_date(dt)
        if dt := resource_data.get("effectivePeriod", {}).get("start"):
            return _parse_date(dt)
        if dt := resource_data.get("issued"):
            return _parse_date(dt)

    if resource_type == "Condition":
        if dt := resource_data.get("onsetDateTime"):
            return _parse_date(dt)
        if dt := resource_data.get("recordedDate"):
            return _parse_date(dt)

    if resource_type == "Procedure":
        if dt := resource_data.get("performedDateTime"):
            return _parse_date(dt)
        if dt := resource_data.get("performedPeriod", {}).get("start"):
            return _parse_date(dt)

    if resource_type == "MedicationRequest":
        if dt := resource_data.get("authoredOn"):
            return _parse_date(dt)

    if resource_type == "DiagnosticReport":
        if dt := resource_data.get("effectiveDateTime"):
            return _parse_date(dt)
        if dt := resource_data.get("effectivePeriod", {}).get("start"):
            return _parse_date(dt)
        if dt := resource_data.get("issued"):
            return _parse_date(dt)

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


def _sort_by_date_desc(resources: list[FhirResource]) -> list[FhirResource]:
    """Sort resources by date in descending order (most recent first).

    Caches date extraction to avoid redundant JSONB parsing.

    Args:
        resources: List of FhirResource objects.

    Returns:
        Sorted list of resources.
    """
    # Cache dates to avoid repeated extraction
    resources_with_dates = [
        (r, _extract_date_from_resource(r.data)) for r in resources
    ]
    resources_with_dates.sort(
        key=lambda x: x[1] if x[1] else date.min,
        reverse=True,
    )
    return [r for r, _ in resources_with_dates]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/{patient_id}/labs", response_model=PaginatedFhirResponse)
async def get_patient_labs(
    patient_id: VerifiedPatient,
    db: AsyncSession = Depends(get_db),
    codes: str | None = Query(
        None, description="Comma-separated LOINC codes to filter by"
    ),
    from_date: date | None = Query(
        None, alias="from", description="Start date (inclusive) ISO format"
    ),
    to_date: date | None = Query(
        None, alias="to", description="End date (inclusive) ISO format"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginatedFhirResponse:
    """Get lab results (Observations) for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient (verified by dependency).
        codes: Optional comma-separated LOINC codes to filter by.
        from_date: Optional start date filter (inclusive).
        to_date: Optional end date filter (inclusive).
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of Observation FHIR resources.
    """
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

    # Sort by date (most recent first) with cached date extraction
    sorted_resources = _sort_by_date_desc(filtered)

    total = len(sorted_resources)
    paginated = sorted_resources[skip : skip + limit]

    return PaginatedFhirResponse(
        items=[
            FhirResourceItem(
                id=str(obs.id),
                fhir_id=obs.fhir_id,
                data=obs.data,
            )
            for obs in paginated
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{patient_id}/medications", response_model=PaginatedFhirResponse)
async def get_patient_medications(
    patient_id: VerifiedPatient,
    db: AsyncSession = Depends(get_db),
    status: Literal["active", "all"] = Query(
        "all", description="Filter by medication status"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginatedFhirResponse:
    """Get medications for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient (verified by dependency).
        status: Filter by status - 'active' for current medications, 'all' for all.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of MedicationRequest FHIR resources.
    """
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
            if med_status not in ACTIVE_MEDICATION_STATUSES:
                continue

        filtered.append(med)

    # Sort by authoredOn date (most recent first)
    sorted_resources = _sort_by_date_desc(filtered)

    total = len(sorted_resources)
    paginated = sorted_resources[skip : skip + limit]

    return PaginatedFhirResponse(
        items=[
            FhirResourceItem(
                id=str(med.id),
                fhir_id=med.fhir_id,
                data=med.data,
            )
            for med in paginated
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{patient_id}/conditions", response_model=PaginatedFhirResponse)
async def get_patient_conditions(
    patient_id: VerifiedPatient,
    db: AsyncSession = Depends(get_db),
    status: Literal["active", "all"] = Query(
        "all", description="Filter by condition status"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginatedFhirResponse:
    """Get conditions for a patient.

    Args:
        patient_id: PostgreSQL UUID of the patient (verified by dependency).
        status: Filter by status - 'active' for current conditions, 'all' for all.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of Condition FHIR resources.
    """
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
            if cond_status not in ACTIVE_CONDITION_STATUSES:
                continue

        filtered.append(cond)

    # Sort by onset date (most recent first)
    sorted_resources = _sort_by_date_desc(filtered)

    total = len(sorted_resources)
    paginated = sorted_resources[skip : skip + limit]

    return PaginatedFhirResponse(
        items=[
            FhirResourceItem(
                id=str(cond.id),
                fhir_id=cond.fhir_id,
                data=cond.data,
            )
            for cond in paginated
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{patient_id}/timeline", response_model=PaginatedTimelineResponse)
async def get_patient_timeline(
    patient_id: VerifiedPatient,
    db: AsyncSession = Depends(get_db),
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
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
) -> PaginatedTimelineResponse:
    """Get a chronological timeline of clinical events for a patient.

    Aggregates Encounters, Conditions, Procedures, MedicationRequests,
    Observations, and DiagnosticReports in chronological order.

    Args:
        patient_id: PostgreSQL UUID of the patient (verified by dependency).
        from_date: Optional start date filter (inclusive).
        to_date: Optional end date filter (inclusive).
        types: Optional comma-separated resource types to include.
        skip: Number of records to skip for pagination.
        limit: Maximum number of records to return.

    Returns:
        Paginated list of FHIR resources sorted by date.
    """
    # Parse resource types if provided
    requested_types = TIMELINE_RESOURCE_TYPES
    if types:
        requested_types = {
            t.strip() for t in types.split(",") if t.strip() in TIMELINE_RESOURCE_TYPES
        }
        if not requested_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid resource types provided",
            )

    # Query all requested resource types for this patient
    stmt = select(FhirResource).where(
        FhirResource.patient_id == patient_id,
        FhirResource.resource_type.in_(requested_types),
    )
    result = await db.execute(stmt)
    resources = result.scalars().all()

    # Filter by date range and cache dates for sorting
    timeline_items: list[tuple[FhirResource, date | None]] = []
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
        key=lambda x: (x[1] is None, x[1] if x[1] else date.min),
        reverse=True,
    )

    total = len(timeline_items)
    paginated = timeline_items[skip : skip + limit]

    return PaginatedTimelineResponse(
        items=[
            TimelineResourceItem(
                id=str(resource.id),
                fhir_id=resource.fhir_id,
                resource_type=resource.resource_type,
                date=item_date.isoformat() if item_date else None,
                data=resource.data,
            )
            for resource, item_date in paginated
        ],
        total=total,
        skip=skip,
        limit=limit,
    )
