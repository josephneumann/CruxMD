"""Shared FHIR resource parsing utilities.

Consolidates common FHIR extraction patterns used across services.
All functions are pure and handle missing/malformed data gracefully.
"""

from typing import Any


def extract_reference_id(reference: str | None) -> str | None:
    """Extract FHIR ID from a reference string.

    Handles both formats:
    - "urn:uuid:abc-123" -> "abc-123"
    - "Patient/abc-123" -> "abc-123"

    Args:
        reference: FHIR reference string

    Returns:
        Extracted ID or None if reference is empty/None
    """
    if not reference:
        return None

    if reference.startswith("urn:uuid:"):
        return reference[9:]  # len("urn:uuid:")
    elif "/" in reference:
        return reference.split("/")[-1]
    return reference


def extract_reference_ids(refs: list[dict[str, Any]]) -> list[str]:
    """Extract list of FHIR IDs from reference objects.

    Args:
        refs: List of FHIR reference objects with 'reference' keys

    Returns:
        List of extracted IDs (None values filtered out)
    """
    ids = [extract_reference_id(ref.get("reference")) for ref in refs if ref.get("reference")]
    return [id_ for id_ in ids if id_ is not None]


def extract_first_coding(codeable_concept: dict[str, Any]) -> dict[str, Any]:
    """Extract first coding from a FHIR CodeableConcept.

    Args:
        codeable_concept: FHIR CodeableConcept structure

    Returns:
        First coding dict or empty dict if none
    """
    codings = codeable_concept.get("coding", [])
    return codings[0] if codings else {}


def extract_display_name(resource: dict[str, Any]) -> str | None:
    """Extract display name from a FHIR resource.

    Handles multiple patterns:
    - code.coding[0].display (Condition, Observation, etc.)
    - medicationCodeableConcept.coding[0].display (MedicationRequest)
    - code.text (fallback)

    Args:
        resource: FHIR resource with a code field

    Returns:
        Display name string or None if not found
    """
    # Try standard code field first
    code = resource.get("code", {})
    if not code:
        # Check for medicationCodeableConcept (MedicationRequest)
        code = resource.get("medicationCodeableConcept", {})

    if not code:
        return None

    # Try coding array first
    codings = code.get("coding", [])
    if codings:
        return codings[0].get("display")

    # Fall back to text
    return code.get("text")


def extract_clinical_status(resource: dict[str, Any]) -> str:
    """Extract clinical status code from FHIR resource.

    Args:
        resource: FHIR resource with clinicalStatus field

    Returns:
        Status code string or empty string
    """
    clinical_status = resource.get("clinicalStatus", {})
    codings = clinical_status.get("coding", [])
    if codings:
        return codings[0].get("code", "")
    return ""


def extract_encounter_fhir_id(resource: dict[str, Any]) -> str | None:
    """Extract encounter FHIR ID from resource.encounter.reference.

    Args:
        resource: FHIR resource with optional encounter reference

    Returns:
        Encounter FHIR ID or None
    """
    encounter_ref = resource.get("encounter", {}).get("reference")
    return extract_reference_id(encounter_ref)


def extract_observation_value(resource: dict[str, Any]) -> tuple[Any, str | None]:
    """Extract value and unit from FHIR Observation.

    Handles valueQuantity, valueCodeableConcept, and valueString.

    Args:
        resource: FHIR Observation resource

    Returns:
        Tuple of (value, unit) where unit may be None
    """
    if "valueQuantity" in resource:
        vq = resource["valueQuantity"]
        return vq.get("value"), vq.get("unit")
    elif "valueCodeableConcept" in resource:
        coding = extract_first_coding(resource["valueCodeableConcept"])
        return coding.get("display"), None
    elif "valueString" in resource:
        return resource["valueString"], None
    return None, None
