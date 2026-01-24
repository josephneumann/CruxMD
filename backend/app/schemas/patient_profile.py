"""Patient profile schema for non-clinical patient narratives."""

from pydantic import BaseModel


class PatientProfile(BaseModel):
    """Non-clinical narrative about the patient's life.

    Generated during Synthea fixture creation to add personality and context
    that makes demos feel more human. Used by the LLM for personalization.
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
