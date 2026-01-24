"""Patient profile schema for non-clinical patient narratives."""

from pydantic import BaseModel


class PatientProfile(BaseModel):
    """Non-clinical narrative about the patient's life.

    Profiles are stored as FHIR extensions on Patient resources, maintaining
    FHIR-native architecture. Use `load_bundle_with_profile()` to attach
    profiles during loading, and `get_patient_profile()` to extract them.

    Can be generated lazily by the LLM from clinical data, or pre-generated
    during fixture creation for demo consistency.
    """

    # Identity
    preferred_name: str  # "Maria" (vs legal name "Maria Elena Garcia")
    pronouns: str  # "she/her"

    # Life context
    occupation: str  # "Retired elementary school teacher"
    living_situation: str  # "Lives with husband of 42 years"
    family_summary: str  # "3 adult children, 6 grandchildren"

    # Personality & preferences
    hobbies: list[str]  # ["gardening", "cooking", "church choir"]
    communication_style: str  # "Prefers detailed explanations, takes notes"

    # Health-related context
    primary_motivation: str  # "Wants to stay active for grandchildren"
    barriers: str  # "Limited transportation, fixed income"
    support_system: str  # "Husband very supportive, daughter helps with appointments"
