"""Embedding service for FHIR resources using OpenAI text-embedding-3-small."""

import logging
from collections.abc import Callable
from typing import Any

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_MODEL = "text-embedding-3-small"

# Embedding dimension for text-embedding-3-small
EMBEDDING_DIMENSION = 1536

# Maximum texts per batch (OpenAI limit is 2048, but we use a conservative default)
MAX_BATCH_SIZE = 100


# =============================================================================
# FHIR Resource Text Templates
# =============================================================================


def _template_condition(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Condition resource.

    Extracts: display name, clinical status, onset date, verification status.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    clinical_status = ""
    status_obj = resource.get("clinicalStatus", {})
    status_codings = status_obj.get("coding", [])
    if status_codings:
        clinical_status = status_codings[0].get("code", "")

    onset = resource.get("onsetDateTime", "")

    parts = [f"Condition: {display}"]
    if clinical_status:
        parts.append(f"Status: {clinical_status}")
    if onset:
        parts.append(f"Onset: {onset}")

    return ". ".join(parts)


def _template_observation(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Observation resource.

    Extracts: observation name, value with unit, effective date, status.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    # Extract value
    value_str = ""
    if "valueQuantity" in resource:
        vq = resource["valueQuantity"]
        value = vq.get("value", "")
        unit = vq.get("unit", "")
        value_str = f"{value} {unit}".strip()
    elif "valueCodeableConcept" in resource:
        vcc = resource["valueCodeableConcept"]
        vcc_codings = vcc.get("coding", [])
        value_str = vcc_codings[0].get("display", "") if vcc_codings else vcc.get("text", "")
    elif "valueString" in resource:
        value_str = resource["valueString"]
    elif "valueBoolean" in resource:
        value_str = "positive" if resource["valueBoolean"] else "negative"

    effective = resource.get("effectiveDateTime", "")
    status = resource.get("status", "")

    parts = [f"Observation: {display}"]
    if value_str:
        parts.append(f"Value: {value_str}")
    if effective:
        parts.append(f"Date: {effective}")
    if status:
        parts.append(f"Status: {status}")

    return ". ".join(parts)


def _template_medication_request(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR MedicationRequest resource.

    Extracts: medication name, status, dosage instructions, authored date.
    """
    med_code = resource.get("medicationCodeableConcept", {})
    codings = med_code.get("coding", [])
    display = codings[0].get("display", "") if codings else med_code.get("text", "")

    status = resource.get("status", "")
    authored = resource.get("authoredOn", "")

    # Extract dosage instruction if present
    dosage_text = ""
    dosage_list = resource.get("dosageInstruction", [])
    if dosage_list and isinstance(dosage_list, list):
        first_dosage = dosage_list[0]
        dosage_text = first_dosage.get("text", "")

    parts = [f"Medication: {display}"]
    if status:
        parts.append(f"Status: {status}")
    if dosage_text:
        parts.append(f"Dosage: {dosage_text}")
    if authored:
        parts.append(f"Prescribed: {authored}")

    return ". ".join(parts)


def _template_allergy_intolerance(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR AllergyIntolerance resource.

    Extracts: allergen, clinical status, criticality, category, reactions.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    clinical_status = ""
    status_obj = resource.get("clinicalStatus", {})
    status_codings = status_obj.get("coding", [])
    if status_codings:
        clinical_status = status_codings[0].get("code", "")

    criticality = resource.get("criticality", "")
    categories = resource.get("category", [])
    category = categories[0] if categories else ""

    # Extract reaction manifestations
    reactions = []
    for reaction in resource.get("reaction", []):
        for manifestation in reaction.get("manifestation", []):
            man_codings = manifestation.get("coding", [])
            if man_codings:
                reactions.append(man_codings[0].get("display", ""))

    parts = [f"Allergy: {display}"]
    if clinical_status:
        parts.append(f"Status: {clinical_status}")
    if criticality:
        parts.append(f"Criticality: {criticality}")
    if category:
        parts.append(f"Category: {category}")
    if reactions:
        parts.append(f"Reactions: {', '.join(reactions)}")

    return ". ".join(parts)


def _template_procedure(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Procedure resource.

    Extracts: procedure name, status, performed date, body site.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    status = resource.get("status", "")

    # Get performed date (could be dateTime or Period)
    performed = resource.get("performedDateTime", "")
    if not performed:
        period = resource.get("performedPeriod", {})
        performed = period.get("start", "")

    # Body site
    body_site = ""
    body_sites = resource.get("bodySite", [])
    if body_sites:
        site_codings = body_sites[0].get("coding", [])
        if site_codings:
            body_site = site_codings[0].get("display", "")

    parts = [f"Procedure: {display}"]
    if status:
        parts.append(f"Status: {status}")
    if performed:
        parts.append(f"Performed: {performed}")
    if body_site:
        parts.append(f"Body site: {body_site}")

    return ". ".join(parts)


def _template_encounter(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Encounter resource.

    Extracts: encounter type, status, class, period, reason.
    """
    # Type
    type_display = ""
    types = resource.get("type", [])
    if types:
        type_codings = types[0].get("coding", [])
        if type_codings:
            type_display = type_codings[0].get("display", "")

    status = resource.get("status", "")

    # Class
    encounter_class = ""
    class_obj = resource.get("class", {})
    if isinstance(class_obj, dict):
        encounter_class = class_obj.get("code", "")

    # Period
    period = resource.get("period", {})
    period_start = period.get("start", "")

    # Reason
    reason_display = ""
    reasons = resource.get("reasonCode", [])
    if reasons:
        reason_codings = reasons[0].get("coding", [])
        if reason_codings:
            reason_display = reason_codings[0].get("display", "")

    parts = [f"Encounter: {type_display or 'Visit'}"]
    if status:
        parts.append(f"Status: {status}")
    if encounter_class:
        parts.append(f"Class: {encounter_class}")
    if period_start:
        parts.append(f"Date: {period_start}")
    if reason_display:
        parts.append(f"Reason: {reason_display}")

    return ". ".join(parts)


def _template_diagnostic_report(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR DiagnosticReport resource.

    Extracts: report name, status, effective date, conclusion.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    status = resource.get("status", "")
    effective = resource.get("effectiveDateTime", "")
    conclusion = resource.get("conclusion", "")

    # Category
    category_display = ""
    categories = resource.get("category", [])
    if categories:
        cat_codings = categories[0].get("coding", [])
        if cat_codings:
            category_display = cat_codings[0].get("display", "")

    parts = [f"Diagnostic Report: {display}"]
    if category_display:
        parts.append(f"Category: {category_display}")
    if status:
        parts.append(f"Status: {status}")
    if effective:
        parts.append(f"Date: {effective}")
    if conclusion:
        parts.append(f"Conclusion: {conclusion}")

    return ". ".join(parts)


def _template_document_reference(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR DocumentReference resource.

    Extracts: document type, status, date, description, content type.
    """
    # Type
    type_obj = resource.get("type", {})
    type_codings = type_obj.get("coding", [])
    type_display = type_codings[0].get("display", "") if type_codings else type_obj.get("text", "")

    status = resource.get("status", "")
    date = resource.get("date", "")
    description = resource.get("description", "")

    # Category
    category_display = ""
    categories = resource.get("category", [])
    if categories:
        cat_codings = categories[0].get("coding", [])
        if cat_codings:
            category_display = cat_codings[0].get("display", "")

    parts = [f"Document: {type_display or 'Clinical Document'}"]
    if category_display:
        parts.append(f"Category: {category_display}")
    if status:
        parts.append(f"Status: {status}")
    if date:
        parts.append(f"Date: {date}")
    if description:
        parts.append(f"Description: {description}")

    return ". ".join(parts)


def _template_care_plan(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR CarePlan resource.

    Extracts: title, status, intent, period, categories, activities.
    """
    title = resource.get("title", "")
    status = resource.get("status", "")
    intent = resource.get("intent", "")

    # Period
    period = resource.get("period", {})
    period_start = period.get("start", "")

    # Categories
    category_displays = []
    for cat in resource.get("category", []):
        cat_codings = cat.get("coding", [])
        if cat_codings:
            category_displays.append(cat_codings[0].get("display", ""))

    # Activities (extract detail descriptions)
    activity_descriptions = []
    for activity in resource.get("activity", []):
        detail = activity.get("detail", {})
        desc = detail.get("description", "")
        if desc:
            activity_descriptions.append(desc)
        # Also check code
        detail_code = detail.get("code", {})
        detail_codings = detail_code.get("coding", [])
        if detail_codings:
            activity_descriptions.append(detail_codings[0].get("display", ""))

    parts = [f"Care Plan: {title or 'Treatment Plan'}"]
    if status:
        parts.append(f"Status: {status}")
    if intent:
        parts.append(f"Intent: {intent}")
    if period_start:
        parts.append(f"Start: {period_start}")
    if category_displays:
        parts.append(f"Categories: {', '.join(category_displays)}")
    if activity_descriptions:
        # Limit to first 3 activities to avoid overly long text
        activities_str = "; ".join(activity_descriptions[:3])
        parts.append(f"Activities: {activities_str}")

    return ". ".join(parts)


def _template_immunization(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Immunization resource.

    Extracts: vaccine display, status, occurrence date.
    """
    vaccine = resource.get("vaccineCode", {})
    codings = vaccine.get("coding", [])
    display = codings[0].get("display", "") if codings else vaccine.get("text", "")

    status = resource.get("status", "")
    occurrence = resource.get("occurrenceDateTime", "")

    parts = [f"Immunization: {display}"]
    if status:
        parts.append(f"Status: {status}")
    if occurrence:
        parts.append(f"Date: {occurrence}")

    return ". ".join(parts)


def _template_imaging_study(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR ImagingStudy resource.

    Extracts: procedure display, modality, body site, started date.
    """
    # Procedure code
    procedure_display = ""
    procedure_codes = resource.get("procedureCode", [])
    if procedure_codes:
        codings = procedure_codes[0].get("coding", [])
        if codings:
            procedure_display = codings[0].get("display", "")

    # Modality and body site from first series
    modality = ""
    body_site = ""
    series = resource.get("series", [])
    if series:
        first_series = series[0]
        modality_obj = first_series.get("modality", {})
        modality = modality_obj.get("display", "") or modality_obj.get("code", "")
        body_site_obj = first_series.get("bodySite", {})
        body_site = body_site_obj.get("display", "")

    started = resource.get("started", "")

    parts = [f"Imaging Study: {procedure_display or 'Unknown'}"]
    if modality:
        parts.append(f"Modality: {modality}")
    if body_site:
        parts.append(f"Body site: {body_site}")
    if started:
        parts.append(f"Date: {started}")

    return ". ".join(parts)


def _template_medication_administration(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR MedicationAdministration resource.

    Extracts: medication display, status, effective date.
    """
    med_code = resource.get("medicationCodeableConcept", {})
    codings = med_code.get("coding", [])
    display = codings[0].get("display", "") if codings else med_code.get("text", "")

    status = resource.get("status", "")
    effective = resource.get("effectiveDateTime", "")
    if not effective:
        effective_period = resource.get("effectivePeriod", {})
        effective = effective_period.get("start", "")

    parts = [f"Medication Administration: {display}"]
    if status:
        parts.append(f"Status: {status}")
    if effective:
        parts.append(f"Date: {effective}")

    return ". ".join(parts)


def _template_medication(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Medication resource.

    Extracts: code display, status.
    """
    code = resource.get("code", {})
    codings = code.get("coding", [])
    display = codings[0].get("display", "") if codings else code.get("text", "")

    status = resource.get("status", "")

    parts = [f"Medication: {display}"]
    if status:
        parts.append(f"Status: {status}")

    return ". ".join(parts)


def _template_device(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Device resource.

    Extracts: type display, status, manufacture date, expiration date.
    """
    type_obj = resource.get("type", {})
    type_codings = type_obj.get("coding", [])
    display = type_codings[0].get("display", "") if type_codings else type_obj.get("text", "")

    status = resource.get("status", "")
    manufacture_date = resource.get("manufactureDate", "")
    expiration_date = resource.get("expirationDate", "")

    parts = [f"Device: {display}"]
    if status:
        parts.append(f"Status: {status}")
    if manufacture_date:
        parts.append(f"Manufactured: {manufacture_date}")
    if expiration_date:
        parts.append(f"Expires: {expiration_date}")

    return ". ".join(parts)


def _template_care_team(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR CareTeam resource.

    Extracts: reason display, status, period start, participant names.
    """
    # Reason
    reason_display = ""
    reason_codes = resource.get("reasonCode", [])
    if reason_codes:
        codings = reason_codes[0].get("coding", [])
        if codings:
            reason_display = codings[0].get("display", "")

    status = resource.get("status", "")
    period = resource.get("period", {})
    period_start = period.get("start", "")

    # Participant names (first 3)
    participant_names = []
    for p in resource.get("participant", [])[:3]:
        member = p.get("member", {})
        name = member.get("display", "")
        if name:
            participant_names.append(name)

    parts = [f"Care Team: {reason_display or 'Care Team'}"]
    if status:
        parts.append(f"Status: {status}")
    if period_start:
        parts.append(f"Start: {period_start}")
    if participant_names:
        parts.append(f"Members: {', '.join(participant_names)}")

    return ". ".join(parts)


def _template_claim(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Claim resource.

    Extracts: type code, status, created, first item service display.
    """
    type_obj = resource.get("type", {})
    type_codings = type_obj.get("coding", [])
    type_code = type_codings[0].get("code", "") if type_codings else ""

    status = resource.get("status", "")
    created = resource.get("created", "")

    # First item service display
    service_display = ""
    items = resource.get("item", [])
    if items:
        service_obj = items[0].get("productOrService", {})
        service_codings = service_obj.get("coding", [])
        if service_codings:
            service_display = service_codings[0].get("display", "")

    parts = [f"Claim: Type: {type_code}"]
    if status:
        parts.append(f"Status: {status}")
    if created:
        parts.append(f"Created: {created}")
    if service_display:
        parts.append(f"Service: {service_display}")

    return ". ".join(parts)


def _template_explanation_of_benefit(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR ExplanationOfBenefit resource.

    Extracts: type code, status, total amount, payment amount.
    """
    type_obj = resource.get("type", {})
    type_codings = type_obj.get("coding", [])
    type_code = type_codings[0].get("code", "") if type_codings else ""

    status = resource.get("status", "")

    # Total amount
    total_amount = ""
    total_currency = ""
    totals = resource.get("total", [])
    if totals:
        amount_obj = totals[0].get("amount", {})
        total_amount = amount_obj.get("value", "")
        total_currency = amount_obj.get("currency", "USD")

    # Payment amount
    payment_amount = ""
    payment = resource.get("payment", {})
    payment_amount_obj = payment.get("amount", {})
    if payment_amount_obj:
        payment_amount = payment_amount_obj.get("value", "")

    parts = [f"EOB: Type: {type_code}"]
    if status:
        parts.append(f"Status: {status}")
    if total_amount != "":
        parts.append(f"Total: ${total_amount}")
    if payment_amount != "":
        parts.append(f"Payment: ${payment_amount}")

    return ". ".join(parts)


def _template_supply_delivery(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR SupplyDelivery resource.

    Extracts: supplied item display, type display, status, occurrence date.
    """
    # Supplied item
    item_display = ""
    supplied_item = resource.get("suppliedItem", {})
    item_cc = supplied_item.get("itemCodeableConcept", {})
    item_codings = item_cc.get("coding", [])
    if item_codings:
        item_display = item_codings[0].get("display", "")

    # Type
    type_obj = resource.get("type", {})
    type_codings = type_obj.get("coding", [])
    type_display = type_codings[0].get("display", "") if type_codings else ""

    status = resource.get("status", "")
    occurrence = resource.get("occurrenceDateTime", "")

    parts = [f"Supply Delivery: {item_display or 'Supply'}"]
    if type_display:
        parts.append(f"Type: {type_display}")
    if status:
        parts.append(f"Status: {status}")
    if occurrence:
        parts.append(f"Date: {occurrence}")

    return ". ".join(parts)


def _template_patient(resource: dict[str, Any]) -> str:
    """
    Generate embeddable text from a FHIR Patient resource.

    Extracts: name, gender, birth date, marital status.
    """
    # Name
    name_parts = resource.get("name", [{}])[0] if resource.get("name") else {}
    given = " ".join(name_parts.get("given", []))
    family = name_parts.get("family", "")
    full_name = f"{given} {family}".strip()

    gender = resource.get("gender", "")
    birth_date = resource.get("birthDate", "")

    marital_status = ""
    marital_obj = resource.get("maritalStatus", {})
    marital_codings = marital_obj.get("coding", [])
    if marital_codings:
        marital_status = marital_codings[0].get("display", "")

    parts = [f"Patient: {full_name or 'Unknown'}"]
    if gender:
        parts.append(f"Gender: {gender}")
    if birth_date:
        parts.append(f"Birth date: {birth_date}")
    if marital_status:
        parts.append(f"Marital status: {marital_status}")

    return ". ".join(parts)


# Mapping of FHIR resource types to their template functions
RESOURCE_TEMPLATES: dict[str, Callable[[dict[str, Any]], str]] = {
    "Condition": _template_condition,
    "Observation": _template_observation,
    "MedicationRequest": _template_medication_request,
    "AllergyIntolerance": _template_allergy_intolerance,
    "Procedure": _template_procedure,
    "Encounter": _template_encounter,
    "DiagnosticReport": _template_diagnostic_report,
    "DocumentReference": _template_document_reference,
    "CarePlan": _template_care_plan,
    "Immunization": _template_immunization,
    "ImagingStudy": _template_imaging_study,
    "MedicationAdministration": _template_medication_administration,
    "Medication": _template_medication,
    "Device": _template_device,
    "CareTeam": _template_care_team,
    "Claim": _template_claim,
    "ExplanationOfBenefit": _template_explanation_of_benefit,
    "SupplyDelivery": _template_supply_delivery,
    "Patient": _template_patient,
}

# Resource types that support embedding
EMBEDDABLE_TYPES = set(RESOURCE_TEMPLATES.keys())


def resource_to_text(resource: dict[str, Any]) -> str | None:
    """
    Convert a FHIR resource to embeddable text using the appropriate template.

    Args:
        resource: FHIR resource dictionary with 'resourceType' field.

    Returns:
        Text representation suitable for embedding, or None if resource type
        is not supported for embedding.
    """
    resource_type = resource.get("resourceType")
    if resource_type not in RESOURCE_TEMPLATES:
        return None

    template_fn = RESOURCE_TEMPLATES[resource_type]
    return template_fn(resource)


# =============================================================================
# Embedding Service
# =============================================================================


class EmbeddingService:
    """
    Embedding service using OpenAI text-embedding-3-small.

    Provides methods to embed text and FHIR resources, with batch support
    to minimize API calls.

    Example:
        # Production usage
        service = EmbeddingService()
        embeddings = await service.embed_texts(["Hello", "World"])

        # Testing with mock client
        mock_client = MockAsyncOpenAI()
        service = EmbeddingService(client=mock_client)
    """

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str = DEFAULT_MODEL,
    ):
        """
        Initialize EmbeddingService.

        Args:
            client: Optional pre-configured AsyncOpenAI client (for testing).
                   If not provided, creates one from settings.
            model: Embedding model to use. Defaults to text-embedding-3-small.
        """
        if client is not None:
            self._client = client
        else:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        self._model = model

    async def close(self) -> None:
        """Close the OpenAI client connection.

        Note: AsyncOpenAI manages its own connection pool and doesn't strictly
        require explicit cleanup, but this method is provided for consistency
        with other services (e.g., KnowledgeGraph).
        """
        await self._client.close()

    async def embed_texts(
        self,
        texts: list[str],
        batch_size: int = MAX_BATCH_SIZE,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Automatically batches requests to stay within API limits.

        Args:
            texts: List of text strings to embed.
            batch_size: Maximum texts per API call. Defaults to MAX_BATCH_SIZE.

        Returns:
            List of embedding vectors, one per input text.
            Each vector has EMBEDDING_DIMENSION (1536) dimensions.

        Raises:
            ValueError: If texts list is empty.
            openai.APIError: If API call fails.
        """
        if not texts:
            raise ValueError("texts list cannot be empty")

        all_embeddings: list[list[float]] = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            response = await self._client.embeddings.create(
                model=self._model,
                input=batch,
            )

            # Extract embeddings in order
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Convenience method that wraps embed_texts for single-text usage.

        Args:
            text: Text string to embed.

        Returns:
            Embedding vector with EMBEDDING_DIMENSION (1536) dimensions.
        """
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_resource(
        self,
        resource: dict[str, Any],
    ) -> list[float] | None:
        """
        Generate embedding for a FHIR resource.

        Converts the resource to text using the appropriate template,
        then generates an embedding.

        Args:
            resource: FHIR resource dictionary.

        Returns:
            Embedding vector, or None if resource type is not embeddable.
        """
        text = resource_to_text(resource)
        if text is None:
            return None

        return await self.embed_text(text)

    async def embed_resources(
        self,
        resources: list[dict[str, Any]],
        batch_size: int = MAX_BATCH_SIZE,
    ) -> list[tuple[dict[str, Any], list[float]]]:
        """
        Generate embeddings for multiple FHIR resources.

        Filters to embeddable resource types, converts to text, and
        batches API calls for efficiency.

        Args:
            resources: List of FHIR resource dictionaries.
            batch_size: Maximum texts per API call.

        Returns:
            List of (resource, embedding) tuples for resources that were
            successfully embedded. Non-embeddable resources are excluded.
        """
        # Filter and convert to text
        embeddable: list[tuple[dict[str, Any], str]] = []
        for resource in resources:
            text = resource_to_text(resource)
            if text is not None:
                embeddable.append((resource, text))

        if not embeddable:
            return []

        # Extract texts for batch embedding
        texts = [text for _, text in embeddable]

        # Get embeddings
        embeddings = await self.embed_texts(texts, batch_size=batch_size)

        # Pair resources with their embeddings
        return [(resource, embedding) for (resource, _), embedding in zip(embeddable, embeddings)]
