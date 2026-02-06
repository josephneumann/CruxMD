"""Neo4j Knowledge Graph service for FHIR resource relationships."""

import json
import logging
from typing import Any, NamedTuple, TypedDict

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions for FHIR Parsing (reduces code duplication)
# =============================================================================


def _extract_reference_id(reference: str | None) -> str | None:
    """
    Extract FHIR ID from a reference string.

    Handles both formats:
    - "urn:uuid:abc-123" -> "abc-123"
    - "Patient/abc-123" -> "abc-123"

    Args:
        reference: FHIR reference string

    Returns:
        Extracted ID or None if invalid
    """
    if not reference:
        return None
    if reference.startswith("urn:uuid:"):
        return reference[9:]  # Strip "urn:uuid:" prefix
    elif "/" in reference:
        return reference.split("/")[-1]
    return reference


def _extract_reference_ids(refs: list[dict[str, Any]]) -> list[str]:
    """
    Extract list of FHIR IDs from reference objects.

    Args:
        refs: List of FHIR reference objects with 'reference' keys

    Returns:
        List of extracted IDs (None values filtered out)
    """
    ids = [_extract_reference_id(ref.get("reference")) for ref in refs if ref.get("reference")]
    return [id for id in ids if id]


def _extract_first_coding(codeable_concept: dict[str, Any]) -> dict[str, Any]:
    """
    Extract first coding from a FHIR CodeableConcept.

    Args:
        codeable_concept: FHIR CodeableConcept structure

    Returns:
        First coding dict or empty dict if none
    """
    codings = codeable_concept.get("coding", [])
    return codings[0] if codings else {}


def _extract_clinical_status(resource: dict[str, Any]) -> str:
    """
    Extract clinical status code from FHIR resource.

    Args:
        resource: FHIR resource with clinicalStatus field

    Returns:
        Status code string or empty string
    """
    clinical_status = resource.get("clinicalStatus", {})
    status_codings = clinical_status.get("coding", [])
    return status_codings[0].get("code", "") if status_codings else ""


def _extract_encounter_fhir_id(resource: dict[str, Any]) -> str | None:
    """
    Extract encounter FHIR ID from resource.encounter.reference.

    Args:
        resource: FHIR resource with optional encounter reference

    Returns:
        Encounter FHIR ID or None
    """
    encounter_ref = resource.get("encounter", {}).get("reference")
    return _extract_reference_id(encounter_ref) if encounter_ref else None


def _extract_context_encounter_fhir_id(resource: dict[str, Any]) -> str | None:
    """
    Extract encounter FHIR ID from resource.context.reference (single ref).

    Used by MedicationAdministration where the encounter is in `context`.

    Args:
        resource: FHIR resource with optional context reference

    Returns:
        Encounter FHIR ID or None
    """
    return _extract_reference_id(resource.get("context", {}).get("reference"))


def _extract_doc_ref_encounter_fhir_id(resource: dict[str, Any]) -> str | None:
    """
    Extract encounter FHIR ID from resource.context.encounter[0].reference.

    Used by DocumentReference where encounters are in `context.encounter[]`.

    Args:
        resource: FHIR DocumentReference resource

    Returns:
        Encounter FHIR ID or None
    """
    encounters = resource.get("context", {}).get("encounter", [])
    if encounters:
        return _extract_reference_id(encounters[0].get("reference"))
    return None


def _extract_claim_encounter_fhir_ids(resource: dict[str, Any]) -> list[str]:
    """
    Extract encounter FHIR IDs from Claim item[].encounter[].reference.

    Args:
        resource: FHIR Claim resource

    Returns:
        List of unique encounter FHIR IDs
    """
    ids: set[str] = set()
    for item in resource.get("item", []):
        for enc in item.get("encounter", []):
            eid = _extract_reference_id(enc.get("reference"))
            if eid:
                ids.add(eid)
    return list(ids)


def _extract_claim_diagnosis_fhir_ids(resource: dict[str, Any]) -> list[str]:
    """
    Extract condition FHIR IDs from Claim diagnosis[].diagnosisReference.reference.

    Args:
        resource: FHIR Claim resource

    Returns:
        List of condition FHIR IDs
    """
    ids = []
    for diag in resource.get("diagnosis", []):
        ref = diag.get("diagnosisReference", {}).get("reference")
        fhir_id = _extract_reference_id(ref)
        if fhir_id:
            ids.append(fhir_id)
    return ids


def _extract_observation_value(resource: dict[str, Any]) -> tuple[Any, str | None]:
    """
    Extract value and unit from FHIR Observation.

    Handles valueQuantity, valueCodeableConcept, and valueString.

    Args:
        resource: FHIR Observation resource

    Returns:
        Tuple of (value, unit) where unit may be None
    """
    if "valueQuantity" in resource:
        return resource["valueQuantity"].get("value"), resource["valueQuantity"].get("unit")
    elif "valueCodeableConcept" in resource:
        value_codings = resource["valueCodeableConcept"].get("coding", [])
        return (value_codings[0].get("display") if value_codings else None), None
    elif "valueString" in resource:
        return resource["valueString"], None
    return None, None


# =============================================================================
# Type Definitions
# =============================================================================


class VerifiedFacts(TypedDict):
    """Type for get_verified_facts return value."""

    conditions: list[dict[str, Any]]
    medications: list[dict[str, Any]]
    allergies: list[dict[str, Any]]
    immunizations: list[dict[str, Any]]


class EncounterEvents(TypedDict):
    """Type for get_encounter_events return value."""

    conditions: list[dict[str, Any]]
    medications: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    procedures: list[dict[str, Any]]
    diagnostic_reports: list[dict[str, Any]]
    immunizations: list[dict[str, Any]]
    care_plans: list[dict[str, Any]]
    document_references: list[dict[str, Any]]
    imaging_studies: list[dict[str, Any]]
    care_teams: list[dict[str, Any]]
    medication_administrations: list[dict[str, Any]]


class ConnectionRecord(TypedDict):
    """Single connection returned by get_all_connections."""

    relationship: str
    direction: str
    fhir_id: str
    resource_type: str
    name: str | None
    fhir_resource: str | None


# =============================================================================
# Knowledge Graph Service
# =============================================================================


class KnowledgeGraph:
    """
    Neo4j graph service with FHIR-aware node creation.

    Provides verified facts via explicit typed relationships.

    Patient-centric relationships (ownership):
    - Patient HAS_CONDITION Condition
    - Patient HAS_MEDICATION_REQUEST MedicationRequest
    - Patient HAS_ALLERGY_INTOLERANCE AllergyIntolerance
    - Patient HAS_OBSERVATION Observation
    - Patient HAS_ENCOUNTER Encounter
    - Patient HAS_PROCEDURE Procedure
    - Patient HAS_DIAGNOSTIC_REPORT DiagnosticReport
    - Patient HAS_IMMUNIZATION Immunization
    - Patient HAS_CARE_PLAN CarePlan
    - Patient HAS_DOCUMENT_REFERENCE DocumentReference
    - Patient HAS_IMAGING_STUDY ImagingStudy
    - Patient HAS_DEVICE Device
    - Patient HAS_CARE_TEAM CareTeam
    - Patient HAS_MEDICATION_ADMINISTRATION MedicationAdministration
    - Patient HAS_CLAIM Claim
    - Patient HAS_EOB ExplanationOfBenefit
    - Patient HAS_SUPPLY_DELIVERY SupplyDelivery

    Encounter-centric relationships (temporal context):
    - Encounter DIAGNOSED Condition
    - Encounter PRESCRIBED MedicationRequest
    - Encounter RECORDED Observation
    - Encounter PERFORMED Procedure
    - Encounter REPORTED DiagnosticReport
    - Encounter ADMINISTERED Immunization
    - Encounter CREATED_DURING CarePlan
    - Encounter DOCUMENTED DocumentReference
    - Encounter IMAGED ImagingStudy
    - Encounter ASSEMBLED CareTeam
    - Encounter GIVEN MedicationAdministration

    Clinical reasoning relationships:
    - MedicationRequest TREATS Condition
    - Procedure TREATS Condition
    - DiagnosticReport CONTAINS_RESULT Observation
    - CarePlan ADDRESSES Condition
    - MedicationAdministration TREATS Condition
    - MedicationAdministration USES_MEDICATION Medication
    - Claim BILLED_FOR Encounter
    - Claim CLAIMS_DIAGNOSIS Condition
    - ExplanationOfBenefit EXPLAINS Claim
    """

    class _EncounterRel(NamedTuple):
        node_label: str
        patient_rel: str
        encounter_rel: str
        alias: str

    _ENCOUNTER_RELATIONSHIPS = [
        _EncounterRel("Condition", "HAS_CONDITION", "DIAGNOSED", "c"),
        _EncounterRel("MedicationRequest", "HAS_MEDICATION_REQUEST", "PRESCRIBED", "m"),
        _EncounterRel("Observation", "HAS_OBSERVATION", "RECORDED", "o"),
        _EncounterRel("Procedure", "HAS_PROCEDURE", "PERFORMED", "pr"),
        _EncounterRel("DiagnosticReport", "HAS_DIAGNOSTIC_REPORT", "REPORTED", "dr"),
        _EncounterRel("Immunization", "HAS_IMMUNIZATION", "ADMINISTERED", "im"),
        _EncounterRel("CarePlan", "HAS_CARE_PLAN", "CREATED_DURING", "cp"),
        _EncounterRel("DocumentReference", "HAS_DOCUMENT_REFERENCE", "DOCUMENTED", "docr"),
        _EncounterRel("ImagingStudy", "HAS_IMAGING_STUDY", "IMAGED", "img"),
        _EncounterRel("CareTeam", "HAS_CARE_TEAM", "ASSEMBLED", "ct"),
        _EncounterRel("MedicationAdministration", "HAS_MEDICATION_ADMINISTRATION", "GIVEN", "ma"),
    ]

    # Frozen whitelist for Cypher injection protection: only these values
    # may appear in dynamically constructed Cypher queries.
    _VALID_LABELS = frozenset(
        r.node_label for r in _ENCOUNTER_RELATIONSHIPS
    ) | {"Patient", "Encounter", "Medication", "AllergyIntolerance",
         "Claim", "ExplanationOfBenefit", "SupplyDelivery", "Device"}
    _VALID_RELATIONSHIPS = frozenset(
        r.patient_rel for r in _ENCOUNTER_RELATIONSHIPS
    ) | frozenset(
        r.encounter_rel for r in _ENCOUNTER_RELATIONSHIPS
    ) | {"HAS_ALLERGY_INTOLERANCE", "HAS_ENCOUNTER", "HAS_DEVICE",
         "HAS_CLAIM", "HAS_EOB", "HAS_SUPPLY_DELIVERY"}
    _VALID_DISPLAY_PROPS = frozenset([
        "display", "type_display", "procedure_display", "item_display",
    ])

    def __init__(self, driver: AsyncDriver | None = None):
        """
        Initialize KnowledgeGraph.

        Args:
            driver: Optional pre-configured Neo4j driver (for testing).
                   If not provided, creates one from settings.
        """
        if driver is not None:
            self._driver = driver
            self._owns_driver = False
        else:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_transaction_retry_time=30,  # 30 second timeout
            )
            self._owns_driver = True

    async def close(self) -> None:
        """Close the Neo4j driver connection if we own it."""
        if self._owns_driver and self._driver is not None:
            await self._driver.close()

    async def verify_connectivity(self) -> bool:
        """Verify Neo4j connection is working."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"Neo4j connectivity check failed: {e}")
            return False

    async def ensure_indexes(self) -> None:
        """
        Create Neo4j indexes and constraints for optimal query performance.

        Should be called during application startup or database migrations.
        Creates indexes on:
        - Primary identifiers (fhir_id, id)
        - Foreign key equivalents (encounter_fhir_id)
        - Commonly filtered fields (clinical_status, status)
        """
        async with self._driver.session() as session:
            # Primary node identification (unique constraints also create indexes)
            constraints = [
                ("patient_id_unique", "Patient", "id"),
                ("condition_fhir_id_unique", "Condition", "fhir_id"),
                ("medication_fhir_id_unique", "MedicationRequest", "fhir_id"),
                ("allergy_fhir_id_unique", "AllergyIntolerance", "fhir_id"),
                ("observation_fhir_id_unique", "Observation", "fhir_id"),
                ("encounter_fhir_id_unique", "Encounter", "fhir_id"),
                ("procedure_fhir_id_unique", "Procedure", "fhir_id"),
                ("diagnostic_report_fhir_id_unique", "DiagnosticReport", "fhir_id"),
                ("immunization_fhir_id_unique", "Immunization", "fhir_id"),
                ("careplan_fhir_id_unique", "CarePlan", "fhir_id"),
                ("document_reference_fhir_id_unique", "DocumentReference", "fhir_id"),
                ("imaging_study_fhir_id_unique", "ImagingStudy", "fhir_id"),
                ("device_fhir_id_unique", "Device", "fhir_id"),
                ("care_team_fhir_id_unique", "CareTeam", "fhir_id"),
                ("medication_admin_fhir_id_unique", "MedicationAdministration", "fhir_id"),
                ("medication_catalog_fhir_id_unique", "Medication", "fhir_id"),
                ("claim_fhir_id_unique", "Claim", "fhir_id"),
                ("eob_fhir_id_unique", "ExplanationOfBenefit", "fhir_id"),
                ("supply_delivery_fhir_id_unique", "SupplyDelivery", "fhir_id"),
            ]

            for name, label, prop in constraints:
                try:
                    await session.run(
                        f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
                    )
                except Exception as e:
                    logger.debug(f"Constraint {name} may already exist: {e}")

            # Indexes for relationship building (WHERE clause properties)
            relationship_indexes = [
                ("condition_encounter", "Condition", "encounter_fhir_id"),
                ("medication_encounter", "MedicationRequest", "encounter_fhir_id"),
                ("observation_encounter", "Observation", "encounter_fhir_id"),
                ("procedure_encounter", "Procedure", "encounter_fhir_id"),
                ("diagnostic_report_encounter", "DiagnosticReport", "encounter_fhir_id"),
                ("immunization_encounter", "Immunization", "encounter_fhir_id"),
                ("careplan_encounter", "CarePlan", "encounter_fhir_id"),
                ("document_reference_encounter", "DocumentReference", "encounter_fhir_id"),
                ("imaging_study_encounter", "ImagingStudy", "encounter_fhir_id"),
                ("care_team_encounter", "CareTeam", "encounter_fhir_id"),
                ("medication_admin_encounter", "MedicationAdministration", "encounter_fhir_id"),
            ]

            for name, label, prop in relationship_indexes:
                try:
                    await session.run(
                        f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                    )
                except Exception as e:
                    logger.debug(f"Index {name} may already exist: {e}")

            # Indexes for filtering queries
            filter_indexes = [
                ("condition_status", "Condition", "clinical_status"),
                ("medication_status", "MedicationRequest", "status"),
                ("allergy_status", "AllergyIntolerance", "clinical_status"),
            ]

            for name, label, prop in filter_indexes:
                try:
                    await session.run(
                        f"CREATE INDEX {name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                    )
                except Exception as e:
                    logger.debug(f"Index {name} may already exist: {e}")

    async def patient_exists(self, patient_id: str) -> bool:
        """
        Check if a patient node exists in the graph.

        Args:
            patient_id: The canonical patient UUID (PostgreSQL-generated).

        Returns:
            True if patient node exists, False otherwise.
        """
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (p:Patient {id: $id}) RETURN p LIMIT 1",
                id=patient_id,
            )
            record = await result.single()
            return record is not None

    # =========================================================================
    # Patient Node Upsert
    # =========================================================================

    async def _upsert_patient(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Patient node with FHIR data."""
        name_parts = resource.get("name", [{}])[0]
        given = name_parts.get("given", [""])[0] if name_parts.get("given") else ""
        family = name_parts.get("family", "")

        await session.run(
            """
            MERGE (p:Patient {id: $id})
            SET p.given_name = $given_name,
                p.family_name = $family_name,
                p.birth_date = $birth_date,
                p.gender = $gender,
                p.fhir_id = $fhir_id,
                p.updated_at = datetime()
            """,
            id=patient_id,
            given_name=given,
            family_name=family,
            birth_date=resource.get("birthDate"),
            gender=resource.get("gender"),
            fhir_id=resource.get("id"),
        )

    # =========================================================================
    # Relationship Building (patient-scoped, optimized queries)
    # =========================================================================

    async def _build_encounter_relationships(
        self, session: AsyncSession, patient_id: str
    ) -> None:
        """
        Build Encounter-centric relationships for a specific patient.

        CRITICAL: Scoped to patient to avoid affecting other patients' data
        and to use indexed lookups instead of Cartesian products.

        Creates relationships:
        - Encounter -[:DIAGNOSED]-> Condition
        - Encounter -[:PRESCRIBED]-> MedicationRequest
        - Encounter -[:RECORDED]-> Observation
        - Encounter -[:PERFORMED]-> Procedure
        - Encounter -[:REPORTED]-> DiagnosticReport
        """
        for rel in self._ENCOUNTER_RELATIONSHIPS:
            # Validate against frozen whitelists to prevent Cypher injection
            if rel.node_label not in self._VALID_LABELS:
                raise ValueError(f"Invalid label: {rel.node_label}")
            if rel.patient_rel not in self._VALID_RELATIONSHIPS:
                raise ValueError(f"Invalid rel: {rel.patient_rel}")
            if rel.encounter_rel not in self._VALID_RELATIONSHIPS:
                raise ValueError(f"Invalid rel: {rel.encounter_rel}")

            await session.run(
                f"""
                MATCH (p:Patient {{id: $patient_id}})-[:HAS_ENCOUNTER]->(e:Encounter)
                MATCH (p)-[:{rel.patient_rel}]->({rel.alias}:{rel.node_label})
                WHERE {rel.alias}.encounter_fhir_id IS NOT NULL
                  AND {rel.alias}.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:{rel.encounter_rel}]->({rel.alias})
                """,
                patient_id=patient_id,
            )

    async def _build_clinical_reasoning_relationships(
        self, session: AsyncSession, patient_id: str
    ) -> None:
        """
        Build clinical reasoning relationships for a specific patient.

        CRITICAL: Scoped to patient and uses UNWIND for efficient array lookups.

        Creates relationships:
        - MedicationRequest -[:TREATS]-> Condition
        - Procedure -[:TREATS]-> Condition
        - DiagnosticReport -[:CONTAINS_RESULT]-> Observation
        """
        # MedicationRequest -> Condition (TREATS)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_MEDICATION_REQUEST]->(m:MedicationRequest)
            WHERE m.reason_fhir_ids IS NOT NULL AND size(m.reason_fhir_ids) > 0
            UNWIND m.reason_fhir_ids AS condition_id
            MATCH (p)-[:HAS_CONDITION]->(c:Condition {fhir_id: condition_id})
            MERGE (m)-[:TREATS]->(c)
            """,
            patient_id=patient_id,
        )

        # Procedure -> Condition (TREATS)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_PROCEDURE]->(pr:Procedure)
            WHERE pr.reason_fhir_ids IS NOT NULL AND size(pr.reason_fhir_ids) > 0
            UNWIND pr.reason_fhir_ids AS condition_id
            MATCH (p)-[:HAS_CONDITION]->(c:Condition {fhir_id: condition_id})
            MERGE (pr)-[:TREATS]->(c)
            """,
            patient_id=patient_id,
        )

        # DiagnosticReport -> Observation (CONTAINS_RESULT)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_DIAGNOSTIC_REPORT]->(dr:DiagnosticReport)
            WHERE dr.result_fhir_ids IS NOT NULL AND size(dr.result_fhir_ids) > 0
            UNWIND dr.result_fhir_ids AS obs_id
            MATCH (p)-[:HAS_OBSERVATION]->(o:Observation {fhir_id: obs_id})
            MERGE (dr)-[:CONTAINS_RESULT]->(o)
            """,
            patient_id=patient_id,
        )

        # CarePlan -> Condition (ADDRESSES)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_CARE_PLAN]->(cp:CarePlan)
            WHERE cp.addresses_fhir_ids IS NOT NULL AND size(cp.addresses_fhir_ids) > 0
            UNWIND cp.addresses_fhir_ids AS condition_id
            MATCH (p)-[:HAS_CONDITION]->(c:Condition {fhir_id: condition_id})
            MERGE (cp)-[:ADDRESSES]->(c)
            """,
            patient_id=patient_id,
        )

        # MedicationAdministration -> Condition (TREATS)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_MEDICATION_ADMINISTRATION]->(ma:MedicationAdministration)
            WHERE ma.reason_fhir_ids IS NOT NULL AND size(ma.reason_fhir_ids) > 0
            UNWIND ma.reason_fhir_ids AS condition_id
            MATCH (p)-[:HAS_CONDITION]->(c:Condition {fhir_id: condition_id})
            MERGE (ma)-[:TREATS]->(c)
            """,
            patient_id=patient_id,
        )

        # MedicationAdministration -> Medication (USES_MEDICATION)
        # Only created when medicationReference is present (stored as medication_fhir_id)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_MEDICATION_ADMINISTRATION]->(ma:MedicationAdministration)
            WHERE ma.medication_fhir_id IS NOT NULL
            MATCH (med:Medication {fhir_id: ma.medication_fhir_id})
            MERGE (ma)-[:USES_MEDICATION]->(med)
            """,
            patient_id=patient_id,
        )

        # Claim -> Encounter (BILLED_FOR)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_CLAIM]->(cl:Claim)
            WHERE cl.encounter_fhir_ids IS NOT NULL AND size(cl.encounter_fhir_ids) > 0
            UNWIND cl.encounter_fhir_ids AS enc_id
            MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter {fhir_id: enc_id})
            MERGE (cl)-[:BILLED_FOR]->(e)
            """,
            patient_id=patient_id,
        )

        # Claim -> Condition (CLAIMS_DIAGNOSIS)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_CLAIM]->(cl:Claim)
            WHERE cl.diagnosis_fhir_ids IS NOT NULL AND size(cl.diagnosis_fhir_ids) > 0
            UNWIND cl.diagnosis_fhir_ids AS cond_id
            MATCH (p)-[:HAS_CONDITION]->(c:Condition {fhir_id: cond_id})
            MERGE (cl)-[:CLAIMS_DIAGNOSIS]->(c)
            """,
            patient_id=patient_id,
        )

        # ExplanationOfBenefit -> Claim (EXPLAINS)
        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})-[:HAS_EOB]->(eob:ExplanationOfBenefit)
            WHERE eob.claim_fhir_id IS NOT NULL
            MATCH (p)-[:HAS_CLAIM]->(cl:Claim {fhir_id: eob.claim_fhir_id})
            MERGE (eob)-[:EXPLAINS]->(cl)
            """,
            patient_id=patient_id,
        )

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def get_verified_conditions(self, patient_id: str) -> list[dict[str, Any]]:
        """
        Get FHIR Condition resources for graph-verified active conditions.

        Returns actual FHIR resources, not extracted fields.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            List of FHIR Condition resources with active clinical status
            (active, recurrence, or relapse).
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
                WHERE c.clinical_status IN ['active', 'recurrence', 'relapse']
                RETURN c.fhir_resource as resource
                """,
                patient_id=patient_id,
            )
            resources = []
            async for record in result:
                resource_json = record["resource"]
                if resource_json:
                    resources.append(json.loads(resource_json))
            return resources

    async def get_verified_medications(self, patient_id: str) -> list[dict[str, Any]]:
        """
        Get FHIR MedicationRequest resources for active medications.

        Returns actual FHIR resources, not extracted fields.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            List of FHIR MedicationRequest resources with status in ['active', 'on-hold'].
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_MEDICATION_REQUEST]->(m:MedicationRequest)
                WHERE m.status IN ['active', 'on-hold']
                RETURN m.fhir_resource as resource
                """,
                patient_id=patient_id,
            )
            resources = []
            async for record in result:
                resource_json = record["resource"]
                if resource_json:
                    resources.append(json.loads(resource_json))
            return resources

    async def get_verified_allergies(self, patient_id: str) -> list[dict[str, Any]]:
        """
        Get FHIR AllergyIntolerance resources for known allergies.

        Returns actual FHIR resources, not extracted fields.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            List of FHIR AllergyIntolerance resources with active clinical status
            (active, recurrence, or relapse).
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_ALLERGY_INTOLERANCE]->(a:AllergyIntolerance)
                WHERE a.clinical_status IN ['active', 'recurrence', 'relapse']
                RETURN a.fhir_resource as resource
                """,
                patient_id=patient_id,
            )
            resources = []
            async for record in result:
                resource_json = record["resource"]
                if resource_json:
                    resources.append(json.loads(resource_json))
            return resources

    async def get_verified_immunizations(self, patient_id: str) -> list[dict[str, Any]]:
        """
        Get FHIR Immunization resources for completed immunizations.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            List of FHIR Immunization resources with status = 'completed'.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_IMMUNIZATION]->(im:Immunization)
                WHERE im.status = 'completed'
                RETURN im.fhir_resource as resource
                """,
                patient_id=patient_id,
            )
            resources = []
            async for record in result:
                resource_json = record["resource"]
                if resource_json:
                    resources.append(json.loads(resource_json))
            return resources

    async def get_verified_facts(self, patient_id: str) -> VerifiedFacts:
        """
        Get all verified clinical facts from graph for a patient.

        Aggregates conditions, medications, allergies, and immunizations.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            TypedDict with 'conditions', 'medications', 'allergies', and
            'immunizations' keys, each containing a list of FHIR resources.
        """
        conditions = await self.get_verified_conditions(patient_id)
        medications = await self.get_verified_medications(patient_id)
        allergies = await self.get_verified_allergies(patient_id)
        immunizations = await self.get_verified_immunizations(patient_id)

        return {
            "conditions": conditions,
            "medications": medications,
            "allergies": allergies,
            "immunizations": immunizations,
        }

    async def get_encounter_events(self, encounter_fhir_id: str) -> EncounterEvents:
        """
        Get all clinical events that occurred during an encounter.

        Traverses Encounter-centric relationships to find:
        - Conditions diagnosed during the encounter
        - Medications prescribed during the encounter
        - Observations recorded during the encounter
        - Procedures performed during the encounter
        - Diagnostic reports from the encounter

        Args:
            encounter_fhir_id: The FHIR ID of the encounter.

        Returns:
            TypedDict with keys for each resource type, containing lists of
            parsed FHIR resources.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Encounter {fhir_id: $encounter_id})
                OPTIONAL MATCH (e)-[:DIAGNOSED]->(c:Condition)
                OPTIONAL MATCH (e)-[:PRESCRIBED]->(m:MedicationRequest)
                OPTIONAL MATCH (e)-[:RECORDED]->(o:Observation)
                OPTIONAL MATCH (e)-[:PERFORMED]->(pr:Procedure)
                OPTIONAL MATCH (e)-[:REPORTED]->(dr:DiagnosticReport)
                OPTIONAL MATCH (e)-[:ADMINISTERED]->(im:Immunization)
                OPTIONAL MATCH (e)-[:CREATED_DURING]->(cp:CarePlan)
                OPTIONAL MATCH (e)-[:DOCUMENTED]->(docr:DocumentReference)
                OPTIONAL MATCH (e)-[:IMAGED]->(img:ImagingStudy)
                OPTIONAL MATCH (e)-[:ASSEMBLED]->(ct:CareTeam)
                OPTIONAL MATCH (e)-[:GIVEN]->(ma:MedicationAdministration)
                RETURN e, collect(DISTINCT c) as conditions,
                       collect(DISTINCT m) as medications,
                       collect(DISTINCT o) as observations,
                       collect(DISTINCT pr) as procedures,
                       collect(DISTINCT dr) as diagnostic_reports,
                       collect(DISTINCT im) as immunizations,
                       collect(DISTINCT cp) as care_plans,
                       collect(DISTINCT docr) as document_references,
                       collect(DISTINCT img) as imaging_studies,
                       collect(DISTINCT ct) as care_teams,
                       collect(DISTINCT ma) as medication_administrations
                """,
                encounter_id=encounter_fhir_id,
            )
            record = await result.single()

            if not record:
                return {
                    "conditions": [],
                    "medications": [],
                    "observations": [],
                    "procedures": [],
                    "diagnostic_reports": [],
                    "immunizations": [],
                    "care_plans": [],
                    "document_references": [],
                    "imaging_studies": [],
                    "care_teams": [],
                    "medication_administrations": [],
                }

            def _parse_fhir_nodes(nodes: list) -> list[dict[str, Any]]:
                return [
                    json.loads(n["fhir_resource"])
                    for n in nodes
                    if n and n.get("fhir_resource")
                ]

            return {
                "conditions": _parse_fhir_nodes(record["conditions"]),
                "medications": _parse_fhir_nodes(record["medications"]),
                "observations": _parse_fhir_nodes(record["observations"]),
                "procedures": _parse_fhir_nodes(record["procedures"]),
                "diagnostic_reports": _parse_fhir_nodes(record["diagnostic_reports"]),
                "immunizations": _parse_fhir_nodes(record["immunizations"]),
                "care_plans": _parse_fhir_nodes(record["care_plans"]),
                "document_references": _parse_fhir_nodes(record["document_references"]),
                "imaging_studies": _parse_fhir_nodes(record["imaging_studies"]),
                "care_teams": _parse_fhir_nodes(record["care_teams"]),
                "medication_administrations": _parse_fhir_nodes(record["medication_administrations"]),
            }

    async def get_medications_treating_condition(
        self, condition_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get medications that treat a specific condition.

        Args:
            condition_fhir_id: The FHIR ID of the condition.

        Returns:
            List of parsed FHIR MedicationRequest resources.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {fhir_id: $condition_id})<-[:TREATS]-(m:MedicationRequest)
                RETURN m.fhir_resource as resource
                """,
                condition_id=condition_fhir_id,
            )
            medications = []
            async for record in result:
                if record["resource"]:
                    medications.append(json.loads(record["resource"]))
            return medications

    async def get_procedures_for_condition(
        self, condition_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get procedures performed for a specific condition.

        Args:
            condition_fhir_id: The FHIR ID of the condition.

        Returns:
            List of parsed FHIR Procedure resources.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {fhir_id: $condition_id})<-[:TREATS]-(pr:Procedure)
                RETURN pr.fhir_resource as resource
                """,
                condition_id=condition_fhir_id,
            )
            procedures = []
            async for record in result:
                if record["resource"]:
                    procedures.append(json.loads(record["resource"]))
            return procedures

    async def get_care_plans_for_condition(
        self, condition_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get care plans that address a specific condition.

        Args:
            condition_fhir_id: The FHIR ID of the condition.

        Returns:
            List of parsed FHIR CarePlan resources.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {fhir_id: $condition_id})<-[:ADDRESSES]-(cp:CarePlan)
                RETURN cp.fhir_resource as resource
                """,
                condition_id=condition_fhir_id,
            )
            care_plans = []
            async for record in result:
                if record["resource"]:
                    care_plans.append(json.loads(record["resource"]))
            return care_plans

    async def search_nodes_by_name(
        self,
        patient_id: str,
        query_terms: list[str],
        resource_types: list[str] | None = None,
    ) -> list[dict[str, str]]:
        """
        Fuzzy search graph nodes by display name for a patient.

        Performs case-insensitive substring matching of query terms against
        node display properties. Returns matched nodes with their encounter
        context for downstream traversal.

        Args:
            patient_id: The canonical patient UUID.
            query_terms: List of search terms to match against display names.
            resource_types: Optional list of FHIR resource types to filter
                (e.g. ["Condition", "MedicationRequest"]). If None, searches all.

        Returns:
            List of dicts with 'fhir_id', 'resource_type', and
            'encounter_fhir_id' keys. For Encounter nodes,
            encounter_fhir_id equals the node's own fhir_id.
        """
        # All searchable node types with their patient relationship and display property
        searchable = [
            ("Condition", "HAS_CONDITION", "display"),
            ("MedicationRequest", "HAS_MEDICATION_REQUEST", "display"),
            ("AllergyIntolerance", "HAS_ALLERGY_INTOLERANCE", "display"),
            ("Observation", "HAS_OBSERVATION", "display"),
            ("Procedure", "HAS_PROCEDURE", "display"),
            ("DiagnosticReport", "HAS_DIAGNOSTIC_REPORT", "display"),
            ("Encounter", "HAS_ENCOUNTER", "type_display"),
            ("Immunization", "HAS_IMMUNIZATION", "display"),
            ("CarePlan", "HAS_CARE_PLAN", "display"),
            ("DocumentReference", "HAS_DOCUMENT_REFERENCE", "type_display"),
            ("ImagingStudy", "HAS_IMAGING_STUDY", "procedure_display"),
            ("Device", "HAS_DEVICE", "type_display"),
            ("CareTeam", "HAS_CARE_TEAM", "display"),
            ("MedicationAdministration", "HAS_MEDICATION_ADMINISTRATION", "display"),
            ("SupplyDelivery", "HAS_SUPPLY_DELIVERY", "item_display"),
        ]

        if resource_types:
            searchable = [s for s in searchable if s[0] in resource_types]

        lower_terms = [t.lower() for t in query_terms if t]
        if not lower_terms and not resource_types:
            return []

        results: list[dict[str, str]] = []
        async with self._driver.session() as session:
            for label, rel, display_prop in searchable:
                # Validate against frozen whitelists to prevent Cypher injection
                if label not in self._VALID_LABELS:
                    raise ValueError(f"Invalid label: {label}")
                if rel not in self._VALID_RELATIONSHIPS:
                    raise ValueError(f"Invalid rel: {rel}")
                if display_prop not in self._VALID_DISPLAY_PROPS:
                    raise ValueError(f"Invalid prop: {display_prop}")

                params: dict[str, Any] = {"patient_id": patient_id}

                # Build WHERE clause: if terms present, filter by display name
                if lower_terms:
                    conditions = " OR ".join(
                        f"toLower(n.{display_prop}) CONTAINS $term_{i}"
                        for i in range(len(lower_terms))
                    )
                    for i, term in enumerate(lower_terms):
                        params[f"term_{i}"] = term
                    where_clause = f"WHERE {conditions}"
                else:
                    # No terms but resource_types filter — return all of type
                    where_clause = ""

                # Encounter nodes don't have encounter_fhir_id (they ARE encounters)
                encounter_return = (
                    "n.fhir_id as encounter_fhir_id"
                    if label == "Encounter"
                    else "n.encounter_fhir_id as encounter_fhir_id"
                )

                result = await session.run(
                    f"""
                    MATCH (p:Patient {{id: $patient_id}})-[:{rel}]->(n:{label})
                    {where_clause}
                    RETURN n.fhir_id as fhir_id, {encounter_return}
                    """,
                    **params,
                )
                async for record in result:
                    if record["fhir_id"]:
                        results.append({
                            "fhir_id": record["fhir_id"],
                            "resource_type": label,
                            "encounter_fhir_id": record["encounter_fhir_id"],
                        })

        return results

    async def search_observations_by_category(
        self, patient_id: str, categories: list[str]
    ) -> list[dict[str, str]]:
        """Return Observation nodes matching given category codes.

        Args:
            patient_id: The canonical patient UUID.
            categories: List of Observation category codes (e.g. "laboratory", "vital-signs").

        Returns:
            List of dicts with 'fhir_id', 'resource_type', and 'encounter_fhir_id' keys.
        """
        if not categories:
            return []

        results: list[dict[str, str]] = []
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_OBSERVATION]->(o:Observation)
                WHERE o.category IN $categories
                RETURN o.fhir_id as fhir_id, o.encounter_fhir_id as encounter_fhir_id
                """,
                patient_id=patient_id,
                categories=categories,
            )
            async for record in result:
                if record["fhir_id"]:
                    results.append({
                        "fhir_id": record["fhir_id"],
                        "resource_type": "Observation",
                        "encounter_fhir_id": record["encounter_fhir_id"],
                    })

        return results

    async def get_patient_encounters(
        self,
        patient_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get encounters for a patient, optionally filtered by date range.

        Args:
            patient_id: The canonical patient UUID.
            start_date: Optional ISO date string for range start (inclusive).
            end_date: Optional ISO date string for range end (inclusive).

        Returns:
            List of dicts with fhir_id, type_display, period_start, period_end.
            Ordered by period_start descending.
        """
        where_clauses = []
        params: dict[str, Any] = {"patient_id": patient_id}

        if start_date:
            where_clauses.append("e.period_start >= $start_date")
            params["start_date"] = start_date
        if end_date:
            where_clauses.append("e.period_start <= $end_date")
            params["end_date"] = end_date

        where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        async with self._driver.session() as session:
            result = await session.run(
                f"""
                MATCH (p:Patient {{id: $patient_id}})-[:HAS_ENCOUNTER]->(e:Encounter)
                {where}
                RETURN e.fhir_id as fhir_id, e.type_display as type_display,
                       e.period_start as period_start, e.period_end as period_end
                ORDER BY e.period_start DESC
                """,
                **params,
            )
            return [record.data() async for record in result]

    async def get_all_connections(
        self,
        fhir_id: str,
        patient_id: str | None = None,
        limit: int = 100,
    ) -> list[ConnectionRecord]:
        """
        Get all graph connections from a node, excluding Patient nodes.

        Generic traversal that returns every edge from a node regardless of
        resource type. Useful for discovering relationships without knowing
        the schema in advance.

        Args:
            fhir_id: The FHIR ID of the node to traverse from.
            patient_id: Optional patient UUID to scope the query. When provided,
                the source node must be owned by this patient (connected via a
                HAS_* relationship) or have no patient ownership (e.g. Medication).
            limit: Maximum number of connections to return (default 100).

        Returns:
            List of ConnectionRecord dicts with relationship, direction,
            fhir_id, resource_type, name, and fhir_resource for each
            connected node. Ordered by relationship type, then resource_type.
        """
        if patient_id:
            query = """
                MATCH (n {fhir_id: $fhir_id})
                WHERE EXISTS {
                    MATCH (p:Patient {id: $patient_id})-[]->(n)
                } OR NOT EXISTS {
                    MATCH (:Patient)-[]->(n)
                }
                WITH n
                MATCH (n)-[r]-(m)
                WHERE NOT m:Patient
                RETURN type(r) as relationship,
                       CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction,
                       m.fhir_id as fhir_id,
                       labels(m)[0] as resource_type,
                       m.name as name,
                       m.fhir_resource as fhir_resource
                ORDER BY relationship, resource_type
                LIMIT $limit
            """
            params = {"fhir_id": fhir_id, "patient_id": patient_id, "limit": limit}
        else:
            query = """
                MATCH (n {fhir_id: $fhir_id})-[r]-(m)
                WHERE NOT m:Patient
                RETURN type(r) as relationship,
                       CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction,
                       m.fhir_id as fhir_id,
                       labels(m)[0] as resource_type,
                       m.name as name,
                       m.fhir_resource as fhir_resource
                ORDER BY relationship, resource_type
                LIMIT $limit
            """
            params = {"fhir_id": fhir_id, "limit": limit}

        async with self._driver.session() as session:
            result = await session.run(query, **params)
            connections: list[ConnectionRecord] = []
            async for record in result:
                connections.append({
                    "relationship": record["relationship"],
                    "direction": record["direction"],
                    "fhir_id": record["fhir_id"],
                    "resource_type": record["resource_type"],
                    "name": record["name"],
                    "fhir_resource": record["fhir_resource"],
                })
            return connections

    # =========================================================================
    # Batch Property Extractors — prep FHIR resources for UNWIND queries.
    # Each returns a dict of Neo4j-ready params for one resource.
    # =========================================================================

    @staticmethod
    def _extract_condition_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "clinical_status": _extract_clinical_status(resource),
            "onset_date": resource.get("onsetDateTime"),
            "abatement_date": resource.get("abatementDateTime"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_medication_request_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("medicationCodeableConcept", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "authored_on": resource.get("authoredOn"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "reason_fhir_ids": _extract_reference_ids(resource.get("reasonReference", [])),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_allergy_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "clinical_status": _extract_clinical_status(resource),
            "category": resource.get("category", [None])[0],
            "criticality": resource.get("criticality"),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_observation_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        value, value_unit = _extract_observation_value(resource)
        category_coding = _extract_first_coding(
            resource.get("category", [{}])[0] if resource.get("category") else {}
        )
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "effective_date": resource.get("effectiveDateTime"),
            "value": value,
            "value_unit": value_unit,
            "category": category_coding.get("code"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_encounter_params(resource: dict[str, Any]) -> dict[str, Any]:
        types = resource.get("type", [{}])
        first_type = types[0] if types else {}
        first_coding = _extract_first_coding(first_type)
        period = resource.get("period", {})
        reason_coding = _extract_first_coding(
            resource.get("reasonCode", [{}])[0] if resource.get("reasonCode") else {}
        )
        return {
            "fhir_id": resource.get("id"),
            "type_code": first_coding.get("code"),
            "type_display": first_coding.get("display"),
            "status": resource.get("status"),
            "class_code": resource.get("class", {}).get("code"),
            "period_start": period.get("start"),
            "period_end": period.get("end"),
            "reason_display": reason_coding.get("display"),
            "reason_code": reason_coding.get("code"),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_procedure_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        performed = resource.get("performedDateTime") or resource.get("performedPeriod", {}).get("start")
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "performed_date": performed,
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "reason_fhir_ids": _extract_reference_ids(resource.get("reasonReference", [])),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_diagnostic_report_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "effective_date": resource.get("effectiveDateTime"),
            "issued": resource.get("issued"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "result_fhir_ids": _extract_reference_ids(resource.get("result", [])),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_immunization_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("vaccineCode", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "occurrence_date": resource.get("occurrenceDateTime"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_careplan_params(resource: dict[str, Any]) -> dict[str, Any]:
        display = resource.get("title")
        if not display:
            for cat in resource.get("category", []):
                coding = _extract_first_coding(cat)
                if coding.get("display"):
                    display = coding["display"]
                    break
        period = resource.get("period", {})
        return {
            "fhir_id": resource.get("id"),
            "display": display,
            "status": resource.get("status"),
            "period_start": period.get("start"),
            "period_end": period.get("end"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "addresses_fhir_ids": _extract_reference_ids(resource.get("addresses", [])),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_document_reference_params(resource: dict[str, Any]) -> dict[str, Any]:
        type_coding = _extract_first_coding(resource.get("type", {}))
        category_coding = _extract_first_coding(
            resource.get("category", [{}])[0] if resource.get("category") else {}
        )
        return {
            "fhir_id": resource.get("id"),
            "type_code": type_coding.get("code"),
            "type_display": type_coding.get("display"),
            "status": resource.get("status"),
            "date": resource.get("date"),
            "description": resource.get("description"),
            "category": category_coding.get("display"),
            "encounter_fhir_id": _extract_doc_ref_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_imaging_study_params(resource: dict[str, Any]) -> dict[str, Any]:
        procedure_display = ""
        procedure_codes = resource.get("procedureCode", [])
        if procedure_codes:
            coding = _extract_first_coding(procedure_codes[0])
            procedure_display = coding.get("display", "")
        modality = ""
        body_site = ""
        series = resource.get("series", [])
        if series:
            first_series = series[0]
            modality_obj = first_series.get("modality", {})
            modality = modality_obj.get("display", "") or modality_obj.get("code", "")
            body_site_obj = first_series.get("bodySite", {})
            body_site = body_site_obj.get("display", "")
        return {
            "fhir_id": resource.get("id"),
            "status": resource.get("status"),
            "started": resource.get("started"),
            "procedure_display": procedure_display,
            "modality": modality,
            "body_site": body_site,
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_device_params(resource: dict[str, Any]) -> dict[str, Any]:
        type_coding = _extract_first_coding(resource.get("type", {}))
        return {
            "fhir_id": resource.get("id"),
            "type_code": type_coding.get("code"),
            "type_display": type_coding.get("display"),
            "status": resource.get("status"),
            "manufacture_date": resource.get("manufactureDate"),
            "expiration_date": resource.get("expirationDate"),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_care_team_params(resource: dict[str, Any]) -> dict[str, Any]:
        reason_coding = _extract_first_coding(
            resource.get("reasonCode", [{}])[0] if resource.get("reasonCode") else {}
        )
        period = resource.get("period", {})
        return {
            "fhir_id": resource.get("id"),
            "status": resource.get("status"),
            "display": reason_coding.get("display"),
            "period_start": period.get("start"),
            "period_end": period.get("end"),
            "encounter_fhir_id": _extract_encounter_fhir_id(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_medication_administration_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("medicationCodeableConcept", {}))
        effective = resource.get("effectiveDateTime")
        if not effective:
            effective = resource.get("effectivePeriod", {}).get("start")
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "effective_date": effective,
            "encounter_fhir_id": _extract_context_encounter_fhir_id(resource),
            "reason_fhir_ids": _extract_reference_ids(resource.get("reasonReference", [])),
            "medication_fhir_id": _extract_reference_id(
                resource.get("medicationReference", {}).get("reference")
            ),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_medication_params(resource: dict[str, Any]) -> dict[str, Any]:
        first_coding = _extract_first_coding(resource.get("code", {}))
        return {
            "fhir_id": resource.get("id"),
            "code": first_coding.get("code"),
            "display": first_coding.get("display"),
            "system": first_coding.get("system"),
            "status": resource.get("status"),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_claim_params(resource: dict[str, Any]) -> dict[str, Any]:
        type_coding = _extract_first_coding(resource.get("type", {}))
        primary_service_display = ""
        items = resource.get("item", [])
        if items:
            service_coding = _extract_first_coding(items[0].get("productOrService", {}))
            primary_service_display = service_coding.get("display", "")
        period = resource.get("billablePeriod", {})
        return {
            "fhir_id": resource.get("id"),
            "status": resource.get("status"),
            "type_code": type_coding.get("code"),
            "use": resource.get("use"),
            "created": resource.get("created"),
            "billable_period_start": period.get("start"),
            "billable_period_end": period.get("end"),
            "primary_service_display": primary_service_display,
            "encounter_fhir_ids": _extract_claim_encounter_fhir_ids(resource),
            "diagnosis_fhir_ids": _extract_claim_diagnosis_fhir_ids(resource),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_eob_params(resource: dict[str, Any]) -> dict[str, Any]:
        type_coding = _extract_first_coding(resource.get("type", {}))
        total_amount = None
        total_currency = None
        totals = resource.get("total", [])
        if totals:
            amount_obj = totals[0].get("amount", {})
            total_amount = amount_obj.get("value")
            total_currency = amount_obj.get("currency")
        payment_amount = None
        payment = resource.get("payment", {})
        payment_amount_obj = payment.get("amount", {})
        if payment_amount_obj:
            payment_amount = payment_amount_obj.get("value")
        return {
            "fhir_id": resource.get("id"),
            "status": resource.get("status"),
            "type_code": type_coding.get("code"),
            "use": resource.get("use"),
            "created": resource.get("created"),
            "total_amount": total_amount,
            "total_currency": total_currency,
            "payment_amount": payment_amount,
            "claim_fhir_id": _extract_reference_id(resource.get("claim", {}).get("reference")),
            "fhir_resource": json.dumps(resource),
        }

    @staticmethod
    def _extract_supply_delivery_params(resource: dict[str, Any]) -> dict[str, Any]:
        type_coding = _extract_first_coding(resource.get("type", {}))
        supplied_item = resource.get("suppliedItem", {})
        item_coding = _extract_first_coding(supplied_item.get("itemCodeableConcept", {}))
        return {
            "fhir_id": resource.get("id"),
            "status": resource.get("status"),
            "type_code": type_coding.get("code"),
            "type_display": type_coding.get("display"),
            "item_code": item_coding.get("code"),
            "item_display": item_coding.get("display"),
            "occurrence_date": resource.get("occurrenceDateTime"),
            "fhir_resource": json.dumps(resource),
        }

    # =========================================================================
    # Batch UNWIND Queries — one query per resource type, processes all
    # resources of that type in a single round trip to Neo4j.
    # =========================================================================

    # Maps resource type -> (extractor, UNWIND Cypher query)
    _BATCH_QUERIES: dict[str, tuple[Any, str]] = {
        "Condition": (_extract_condition_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Condition {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.clinical_status = r.clinical_status, n.onset_date = r.onset_date,
                n.abatement_date = r.abatement_date, n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_CONDITION]->(n)
        """),
        "MedicationRequest": (_extract_medication_request_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:MedicationRequest {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.authored_on = r.authored_on,
                n.encounter_fhir_id = r.encounter_fhir_id, n.reason_fhir_ids = r.reason_fhir_ids,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_MEDICATION_REQUEST]->(n)
        """),
        "AllergyIntolerance": (_extract_allergy_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:AllergyIntolerance {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.clinical_status = r.clinical_status, n.category = r.category,
                n.criticality = r.criticality,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_ALLERGY_INTOLERANCE]->(n)
        """),
        "Observation": (_extract_observation_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Observation {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.effective_date = r.effective_date,
                n.value = r.value, n.value_unit = r.value_unit, n.category = r.category,
                n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_OBSERVATION]->(n)
        """),
        "Encounter": (_extract_encounter_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Encounter {fhir_id: r.fhir_id})
            SET n.type_code = r.type_code, n.type_display = r.type_display,
                n.status = r.status, n.class_code = r.class_code,
                n.period_start = r.period_start, n.period_end = r.period_end,
                n.reason_display = r.reason_display, n.reason_code = r.reason_code,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_ENCOUNTER]->(n)
        """),
        "Procedure": (_extract_procedure_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Procedure {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.performed_date = r.performed_date,
                n.encounter_fhir_id = r.encounter_fhir_id, n.reason_fhir_ids = r.reason_fhir_ids,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_PROCEDURE]->(n)
        """),
        "DiagnosticReport": (_extract_diagnostic_report_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:DiagnosticReport {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.effective_date = r.effective_date, n.issued = r.issued,
                n.encounter_fhir_id = r.encounter_fhir_id, n.result_fhir_ids = r.result_fhir_ids,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_DIAGNOSTIC_REPORT]->(n)
        """),
        "Immunization": (_extract_immunization_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Immunization {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.occurrence_date = r.occurrence_date,
                n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_IMMUNIZATION]->(n)
        """),
        "CarePlan": (_extract_careplan_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:CarePlan {fhir_id: r.fhir_id})
            SET n.display = r.display, n.status = r.status,
                n.period_start = r.period_start, n.period_end = r.period_end,
                n.encounter_fhir_id = r.encounter_fhir_id,
                n.addresses_fhir_ids = r.addresses_fhir_ids,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_CARE_PLAN]->(n)
        """),
        "DocumentReference": (_extract_document_reference_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:DocumentReference {fhir_id: r.fhir_id})
            SET n.type_code = r.type_code, n.type_display = r.type_display,
                n.status = r.status, n.date = r.date, n.description = r.description,
                n.category = r.category, n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_DOCUMENT_REFERENCE]->(n)
        """),
        "ImagingStudy": (_extract_imaging_study_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:ImagingStudy {fhir_id: r.fhir_id})
            SET n.status = r.status, n.started = r.started,
                n.procedure_display = r.procedure_display, n.modality = r.modality,
                n.body_site = r.body_site, n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_IMAGING_STUDY]->(n)
        """),
        "Device": (_extract_device_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Device {fhir_id: r.fhir_id})
            SET n.type_code = r.type_code, n.type_display = r.type_display,
                n.status = r.status, n.manufacture_date = r.manufacture_date,
                n.expiration_date = r.expiration_date,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_DEVICE]->(n)
        """),
        "CareTeam": (_extract_care_team_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:CareTeam {fhir_id: r.fhir_id})
            SET n.status = r.status, n.display = r.display,
                n.period_start = r.period_start, n.period_end = r.period_end,
                n.encounter_fhir_id = r.encounter_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_CARE_TEAM]->(n)
        """),
        "MedicationAdministration": (_extract_medication_administration_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:MedicationAdministration {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status, n.effective_date = r.effective_date,
                n.encounter_fhir_id = r.encounter_fhir_id,
                n.reason_fhir_ids = r.reason_fhir_ids,
                n.medication_fhir_id = r.medication_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_MEDICATION_ADMINISTRATION]->(n)
        """),
        "Medication": (_extract_medication_params, """
            UNWIND $batch AS r
            MERGE (n:Medication {fhir_id: r.fhir_id})
            SET n.code = r.code, n.display = r.display, n.system = r.system,
                n.status = r.status,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
        """),
        "Claim": (_extract_claim_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:Claim {fhir_id: r.fhir_id})
            SET n.status = r.status, n.type_code = r.type_code, n.use = r.use,
                n.created = r.created, n.billable_period_start = r.billable_period_start,
                n.billable_period_end = r.billable_period_end,
                n.primary_service_display = r.primary_service_display,
                n.encounter_fhir_ids = r.encounter_fhir_ids,
                n.diagnosis_fhir_ids = r.diagnosis_fhir_ids,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_CLAIM]->(n)
        """),
        "ExplanationOfBenefit": (_extract_eob_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:ExplanationOfBenefit {fhir_id: r.fhir_id})
            SET n.status = r.status, n.type_code = r.type_code, n.use = r.use,
                n.created = r.created, n.total_amount = r.total_amount,
                n.total_currency = r.total_currency, n.payment_amount = r.payment_amount,
                n.claim_fhir_id = r.claim_fhir_id,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_EOB]->(n)
        """),
        "SupplyDelivery": (_extract_supply_delivery_params, """
            UNWIND $batch AS r
            MATCH (p:Patient {id: $patient_id})
            MERGE (n:SupplyDelivery {fhir_id: r.fhir_id})
            SET n.status = r.status, n.type_code = r.type_code,
                n.type_display = r.type_display, n.item_code = r.item_code,
                n.item_display = r.item_display, n.occurrence_date = r.occurrence_date,
                n.fhir_resource = r.fhir_resource, n.updated_at = datetime()
            MERGE (p)-[:HAS_SUPPLY_DELIVERY]->(n)
        """),
    }

    # =========================================================================
    # Main Entry Points
    # =========================================================================

    async def build_from_fhir(
        self, patient_id: str, resources: list[dict[str, Any]]
    ) -> None:
        """
        Build graph nodes and relationships from FHIR resources.

        Uses batched UNWIND queries for performance: resources are grouped by type
        and each group is processed in a single Cypher query instead of individual
        MERGE statements per resource.

        Two-pass approach within an explicit write transaction for atomicity:
        1. First pass: Batch-create all nodes with Patient relationships (UNWIND)
        2. Second pass: Build inter-resource relationships (Encounter-centric, TREATS, etc.)

        The explicit transaction ensures all-or-nothing semantics — if any write
        fails, the entire patient's graph changes are rolled back.

        Args:
            patient_id: The canonical patient UUID (PostgreSQL-generated).
            resources: List of FHIR resources belonging to this patient.
        """
        async with self._driver.session() as session:
            tx = await session.begin_transaction()
            try:
                # First pass: find and create Patient node
                patient_resource = None
                for resource in resources:
                    if resource.get("resourceType") == "Patient":
                        patient_resource = resource
                        break

                if patient_resource:
                    await self._upsert_patient(tx, patient_id, patient_resource)

                # Group resources by type for batch processing
                grouped: dict[str, list[dict[str, Any]]] = {}
                for resource in resources:
                    rtype = resource.get("resourceType")
                    if rtype and rtype != "Patient" and rtype in self._BATCH_QUERIES:
                        grouped.setdefault(rtype, []).append(resource)

                # Batch upsert: one UNWIND query per resource type
                for rtype, rtype_resources in grouped.items():
                    extractor, query = self._BATCH_QUERIES[rtype]
                    batch = [extractor(r) for r in rtype_resources]
                    await tx.run(query, patient_id=patient_id, batch=batch)

                # Second pass: build inter-resource relationships (patient-scoped)
                await self._build_encounter_relationships(tx, patient_id)
                await self._build_clinical_reasoning_relationships(tx, patient_id)

                await tx.commit()
            except Exception:
                await tx.rollback()
                raise

    async def clear_patient_graph(self, patient_id: str) -> None:
        """
        Remove all nodes and relationships for a patient.

        Useful for testing and rebuilding graphs.
        """
        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (p:Patient {id: $patient_id})
                OPTIONAL MATCH (p)-[r]->(n)
                DETACH DELETE p, n
                """,
                patient_id=patient_id,
            )

    async def clear_all(self) -> None:
        """
        Remove all nodes and relationships from the database.

        Use with caution - primarily for testing.
        """
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
