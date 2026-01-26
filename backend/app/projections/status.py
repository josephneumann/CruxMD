"""FHIR Task status mappings.

Shared module for status conversion between CruxMD and FHIR formats.
Used by both extractors (FHIR -> CruxMD) and serializers (CruxMD -> FHIR).
"""

# Map CruxMD status to FHIR Task status
CRUXMD_TO_FHIR = {
    "pending": "requested",
    "in_progress": "in-progress",
    "paused": "on-hold",
    "completed": "completed",
    "cancelled": "cancelled",
    "deferred": "on-hold",  # FHIR doesn't have deferred, use on-hold with extension
}

# Map FHIR status to CruxMD status
FHIR_TO_CRUXMD = {
    "requested": "pending",
    "in-progress": "in_progress",
    "on-hold": "paused",  # Default mapping; deferred uses extension
    "completed": "completed",
    "cancelled": "cancelled",
    "draft": "pending",
    "received": "pending",
    "accepted": "in_progress",
    "rejected": "cancelled",
    "ready": "pending",
    "failed": "cancelled",
    "entered-in-error": "cancelled",
}


def get_fhir_status(cruxmd_status: str) -> str:
    """Convert CruxMD status to FHIR status.

    Args:
        cruxmd_status: CruxMD status value.

    Returns:
        FHIR Task status value.
    """
    return CRUXMD_TO_FHIR.get(cruxmd_status, "requested")


def get_cruxmd_status(fhir_status: str, is_deferred: bool = False) -> str:
    """Convert FHIR status to CruxMD status.

    Args:
        fhir_status: FHIR Task status value.
        is_deferred: Whether the deferred extension is set.

    Returns:
        CruxMD status value.
    """
    if fhir_status == "on-hold" and is_deferred:
        return "deferred"
    return FHIR_TO_CRUXMD.get(fhir_status, "pending")
