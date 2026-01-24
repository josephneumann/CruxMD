"""Generate LLM-based patient profiles from Synthea FHIR bundles.

This script reads Synthea patient bundles and uses GPT-4o to generate
rich narrative profiles that bring clinical data to life.

Usage:
    uv run python -m app.scripts.generate_patient_profiles

Output:
    - fixtures/synthea/patient_bundle_N.profile.json (individual profiles)
    - fixtures/synthea/patient_profiles.json (combined file keyed by patient ID)
"""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.config import settings
from app.schemas.patient_profile import PatientProfile


PROFILE_PROMPT = """Based on this patient's clinical data, create a rich, believable personal profile.

PATIENT DATA:
{patient_summary}

CLINICAL CONTEXT:
- Age: {age}
- Gender: {gender}
- Active Conditions: {conditions}
- Recent Encounters: {encounters}

Create a profile that:
1. Feels like a real person with a coherent life story
2. Has interests and motivations that feel natural for their demographics
3. Includes health motivations connected to their personal life
4. Has realistic barriers and support systems
5. Shows personality in how they might interact with healthcare

The profile should subtly reflect their clinical situation:
- A diabetic patient might mention dietary challenges
- Someone with chronic pain might have adapted hobbies
- An elderly patient might mention family support structures

Output a JSON object with these exact fields (populate with values appropriate for this patient):
{{
    "preferred_name": "Short name or nickname they prefer to be called",
    "pronouns": "he/him, she/her, or they/them",
    "occupation": "Current or former occupation",
    "living_situation": "Who they live with and housing type",
    "family_summary": "Brief family description",
    "hobbies": ["List", "of", "hobbies"],
    "communication_style": "How they prefer to communicate with healthcare providers",
    "primary_motivation": "What motivates them to manage their health",
    "barriers": "Challenges they face in healthcare",
    "support_system": "Who supports them"
}}
"""


def extract_patient_resource(bundle: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the Patient resource from a FHIR bundle."""
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def extract_patient_id(bundle: dict[str, Any]) -> str | None:
    """Extract the patient ID from a FHIR bundle."""
    patient = extract_patient_resource(bundle)
    return patient.get("id") if patient else None


def extract_conditions(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract all Condition resources from a FHIR bundle."""
    conditions = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Condition":
            conditions.append(resource)
    return conditions


def extract_recent_encounters(
    bundle: dict[str, Any], limit: int = 5
) -> list[dict[str, Any]]:
    """Extract recent Encounter resources from a FHIR bundle."""
    encounters = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Encounter":
            encounters.append(resource)

    # Sort by period start date, most recent first
    encounters.sort(
        key=lambda e: e.get("period", {}).get("start", ""),
        reverse=True,
    )
    return encounters[:limit]


def calculate_age(patient: dict[str, Any]) -> int:
    """Calculate patient age from birthDate."""
    birth_date_str = patient.get("birthDate")
    if not birth_date_str:
        return 0
    birth_date = date.fromisoformat(birth_date_str)
    today = date.today()
    return (
        today.year
        - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )


def format_patient_summary(patient: dict[str, Any]) -> str:
    """Format patient demographics into a readable summary."""
    name_info = patient.get("name", [{}])[0]
    given_names = " ".join(name_info.get("given", []))
    family_name = name_info.get("family", "")
    full_name = f"{given_names} {family_name}".strip()

    gender = patient.get("gender", "unknown")
    birth_date = patient.get("birthDate", "unknown")

    address_info = patient.get("address", [{}])[0]
    city = address_info.get("city", "")
    state = address_info.get("state", "")
    location = f"{city}, {state}" if city else "unknown"

    marital = patient.get("maritalStatus", {}).get("text", "unknown")

    # Extract race/ethnicity from extensions
    race = "unknown"
    ethnicity = "unknown"
    birthplace = "unknown"
    for ext in patient.get("extension", []):
        url = ext.get("url", "")
        if "us-core-race" in url:
            for sub_ext in ext.get("extension", []):
                if sub_ext.get("url") == "text":
                    race = sub_ext.get("valueString", race)
        elif "us-core-ethnicity" in url:
            for sub_ext in ext.get("extension", []):
                if sub_ext.get("url") == "text":
                    ethnicity = sub_ext.get("valueString", ethnicity)
        elif "patient-birthPlace" in url:
            bp = ext.get("valueAddress", {})
            bp_city = bp.get("city", "")
            bp_country = bp.get("country", "")
            if bp_city or bp_country:
                birthplace = f"{bp_city}, {bp_country}".strip(", ")

    # Language
    comm = patient.get("communication", [{}])[0]
    language = comm.get("language", {}).get("text", "English")

    return f"""Name: {full_name}
Gender: {gender}
Birth Date: {birth_date}
Race: {race}
Ethnicity: {ethnicity}
Birthplace: {birthplace}
Location: {location}
Marital Status: {marital}
Primary Language: {language}"""


def format_conditions(conditions: list[dict[str, Any]]) -> str:
    """Format conditions list into readable text."""
    if not conditions:
        return "No conditions recorded"

    formatted = []
    for cond in conditions[:10]:  # Limit to 10 for context
        code_info = cond.get("code", {}).get("coding", [{}])[0]
        display = code_info.get("display", "Unknown condition")
        onset = cond.get("onsetDateTime", "")[:10] if cond.get("onsetDateTime") else ""
        if onset:
            formatted.append(f"- {display} (onset: {onset})")
        else:
            formatted.append(f"- {display}")

    return "\n".join(formatted)


def format_encounters(encounters: list[dict[str, Any]]) -> str:
    """Format encounters list into readable text."""
    if not encounters:
        return "No recent encounters"

    formatted = []
    for enc in encounters:
        enc_type = enc.get("type", [{}])[0].get("text", "Unknown visit type")
        period = enc.get("period", {})
        start = period.get("start", "")[:10] if period.get("start") else "unknown date"
        formatted.append(f"- {enc_type} ({start})")

    return "\n".join(formatted)


async def generate_profile_for_patient(
    client: AsyncOpenAI,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    """Generate a narrative profile from Synthea FHIR data."""
    patient = extract_patient_resource(bundle)
    if not patient:
        raise ValueError("Bundle does not contain a Patient resource")

    conditions = extract_conditions(bundle)
    encounters = extract_recent_encounters(bundle)

    patient_summary = format_patient_summary(patient)
    age = calculate_age(patient)
    gender = patient.get("gender", "unknown")

    prompt = PROFILE_PROMPT.format(
        patient_summary=patient_summary,
        age=age,
        gender=gender,
        conditions=format_conditions(conditions),
        encounters=format_encounters(encounters),
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,  # Some creativity for varied profiles
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty response from LLM")

    profile_data = json.loads(content)

    # Validate against schema
    PatientProfile.model_validate(profile_data)

    return profile_data


async def generate_all_profiles(fixtures_dir: Path) -> dict[str, dict[str, Any]]:
    """Generate profiles for all patient fixtures."""
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Configure the API key before running this script."
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    profiles: dict[str, dict[str, Any]] = {}

    bundle_files = sorted(fixtures_dir.glob("patient_bundle_*.json"))
    if not bundle_files:
        print(f"No patient bundles found in {fixtures_dir}")
        return profiles

    print(f"Found {len(bundle_files)} patient bundles")

    for bundle_path in bundle_files:
        with open(bundle_path) as f:
            bundle = json.load(f)

        patient_id = extract_patient_id(bundle)
        if not patient_id:
            print(f"  Skipping {bundle_path.name}: no patient ID found")
            continue

        print(f"Generating profile for {bundle_path.name}...")

        profile = await generate_profile_for_patient(client, bundle)
        profiles[patient_id] = profile

        # Save individual profile alongside the bundle
        profile_path = bundle_path.with_suffix(".profile.json")
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)
        print(f"  Saved: {profile_path.name}")

    # Save combined profiles file
    combined_path = fixtures_dir / "patient_profiles.json"
    with open(combined_path, "w") as f:
        json.dump(profiles, f, indent=2)
    print(f"\nSaved combined profiles: {combined_path}")

    print(f"\nGenerated {len(profiles)} patient profiles")
    return profiles


def main() -> None:
    """Main entry point for the script."""
    # Resolve fixtures directory relative to repo root
    repo_root = Path(__file__).parent.parent.parent.parent
    fixtures_dir = repo_root / "fixtures" / "synthea"

    if not fixtures_dir.exists():
        print(f"Fixtures directory not found: {fixtures_dir}")
        print("Run Synthea fixture generation first (Story 4.1)")
        return

    asyncio.run(generate_all_profiles(fixtures_dir))


if __name__ == "__main__":
    main()
