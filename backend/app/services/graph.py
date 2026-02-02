"""Neo4j Knowledge Graph service for FHIR resource relationships."""

import json
import logging
from typing import Any, TypedDict

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

    Encounter-centric relationships (temporal context):
    - Encounter DIAGNOSED Condition
    - Encounter PRESCRIBED MedicationRequest
    - Encounter RECORDED Observation
    - Encounter PERFORMED Procedure
    - Encounter REPORTED DiagnosticReport

    Clinical reasoning relationships:
    - MedicationRequest TREATS Condition
    - Procedure TREATS Condition
    - DiagnosticReport CONTAINS_RESULT Observation
    - CarePlan ADDRESSES Condition
    """

    # Relationship configuration for encounter-centric edges
    # Format: (node_label, patient_relationship, encounter_relationship, alias)
    _ENCOUNTER_RELATIONSHIPS = [
        ("Condition", "HAS_CONDITION", "DIAGNOSED", "c"),
        ("MedicationRequest", "HAS_MEDICATION_REQUEST", "PRESCRIBED", "m"),
        ("Observation", "HAS_OBSERVATION", "RECORDED", "o"),
        ("Procedure", "HAS_PROCEDURE", "PERFORMED", "pr"),
        ("DiagnosticReport", "HAS_DIAGNOSTIC_REPORT", "REPORTED", "dr"),
        ("Immunization", "HAS_IMMUNIZATION", "ADMINISTERED", "im"),
        ("CarePlan", "HAS_CARE_PLAN", "CREATED_DURING", "cp"),
    ]

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
    # Node Upsert Methods (with session parameter for batching)
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

    async def _upsert_condition(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Condition node and HAS_CONDITION relationship."""
        first_coding = _extract_first_coding(resource.get("code", {}))
        status_code = _extract_clinical_status(resource)
        encounter_fhir_id = _extract_encounter_fhir_id(resource)

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (c:Condition {fhir_id: $fhir_id})
            SET c.code = $code,
                c.display = $display,
                c.system = $system,
                c.clinical_status = $clinical_status,
                c.onset_date = $onset_date,
                c.abatement_date = $abatement_date,
                c.encounter_fhir_id = $encounter_fhir_id,
                c.fhir_resource = $fhir_resource,
                c.updated_at = datetime()
            MERGE (p)-[:HAS_CONDITION]->(c)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            clinical_status=status_code,
            onset_date=resource.get("onsetDateTime"),
            abatement_date=resource.get("abatementDateTime"),
            encounter_fhir_id=encounter_fhir_id,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_medication_request(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update MedicationRequest node and HAS_MEDICATION_REQUEST relationship."""
        first_coding = _extract_first_coding(resource.get("medicationCodeableConcept", {}))
        encounter_fhir_id = _extract_encounter_fhir_id(resource)
        reason_fhir_ids = _extract_reference_ids(resource.get("reasonReference", []))

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (m:MedicationRequest {fhir_id: $fhir_id})
            SET m.code = $code,
                m.display = $display,
                m.system = $system,
                m.status = $status,
                m.authored_on = $authored_on,
                m.encounter_fhir_id = $encounter_fhir_id,
                m.reason_fhir_ids = $reason_fhir_ids,
                m.fhir_resource = $fhir_resource,
                m.updated_at = datetime()
            MERGE (p)-[:HAS_MEDICATION_REQUEST]->(m)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            status=resource.get("status"),
            authored_on=resource.get("authoredOn"),
            encounter_fhir_id=encounter_fhir_id,
            reason_fhir_ids=reason_fhir_ids,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_allergy_intolerance(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update AllergyIntolerance node and HAS_ALLERGY_INTOLERANCE relationship."""
        first_coding = _extract_first_coding(resource.get("code", {}))
        status_code = _extract_clinical_status(resource)

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (a:AllergyIntolerance {fhir_id: $fhir_id})
            SET a.code = $code,
                a.display = $display,
                a.system = $system,
                a.clinical_status = $clinical_status,
                a.category = $category,
                a.criticality = $criticality,
                a.fhir_resource = $fhir_resource,
                a.updated_at = datetime()
            MERGE (p)-[:HAS_ALLERGY_INTOLERANCE]->(a)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            clinical_status=status_code,
            category=resource.get("category", [None])[0],
            criticality=resource.get("criticality"),
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_observation(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Observation node and HAS_OBSERVATION relationship."""
        first_coding = _extract_first_coding(resource.get("code", {}))
        value, value_unit = _extract_observation_value(resource)
        encounter_fhir_id = _extract_encounter_fhir_id(resource)
        category_coding = _extract_first_coding(
            resource.get("category", [{}])[0] if resource.get("category") else {}
        )

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (o:Observation {fhir_id: $fhir_id})
            SET o.code = $code,
                o.display = $display,
                o.system = $system,
                o.status = $status,
                o.effective_date = $effective_date,
                o.value = $value,
                o.value_unit = $value_unit,
                o.category = $category,
                o.encounter_fhir_id = $encounter_fhir_id,
                o.fhir_resource = $fhir_resource,
                o.updated_at = datetime()
            MERGE (p)-[:HAS_OBSERVATION]->(o)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            status=resource.get("status"),
            effective_date=resource.get("effectiveDateTime"),
            value=value,
            value_unit=value_unit,
            category=category_coding.get("code"),
            encounter_fhir_id=encounter_fhir_id,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_encounter(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Encounter node and HAS_ENCOUNTER relationship."""
        types = resource.get("type", [{}])
        first_type = types[0] if types else {}
        first_coding = _extract_first_coding(first_type)
        period = resource.get("period", {})
        reason_coding = _extract_first_coding(
            resource.get("reasonCode", [{}])[0] if resource.get("reasonCode") else {}
        )

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (e:Encounter {fhir_id: $fhir_id})
            SET e.type_code = $type_code,
                e.type_display = $type_display,
                e.status = $status,
                e.class_code = $class_code,
                e.period_start = $period_start,
                e.period_end = $period_end,
                e.reason_display = $reason_display,
                e.reason_code = $reason_code,
                e.fhir_resource = $fhir_resource,
                e.updated_at = datetime()
            MERGE (p)-[:HAS_ENCOUNTER]->(e)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            type_code=first_coding.get("code"),
            type_display=first_coding.get("display"),
            status=resource.get("status"),
            class_code=resource.get("class", {}).get("code"),
            period_start=period.get("start"),
            period_end=period.get("end"),
            reason_display=reason_coding.get("display"),
            reason_code=reason_coding.get("code"),
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_procedure(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Procedure node and HAS_PROCEDURE relationship."""
        first_coding = _extract_first_coding(resource.get("code", {}))
        encounter_fhir_id = _extract_encounter_fhir_id(resource)
        reason_fhir_ids = _extract_reference_ids(resource.get("reasonReference", []))
        performed = resource.get("performedDateTime") or resource.get("performedPeriod", {}).get("start")

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (pr:Procedure {fhir_id: $fhir_id})
            SET pr.code = $code,
                pr.display = $display,
                pr.system = $system,
                pr.status = $status,
                pr.performed_date = $performed_date,
                pr.encounter_fhir_id = $encounter_fhir_id,
                pr.reason_fhir_ids = $reason_fhir_ids,
                pr.fhir_resource = $fhir_resource,
                pr.updated_at = datetime()
            MERGE (p)-[:HAS_PROCEDURE]->(pr)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            status=resource.get("status"),
            performed_date=performed,
            encounter_fhir_id=encounter_fhir_id,
            reason_fhir_ids=reason_fhir_ids,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_diagnostic_report(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update DiagnosticReport node and HAS_DIAGNOSTIC_REPORT relationship."""
        first_coding = _extract_first_coding(resource.get("code", {}))
        encounter_fhir_id = _extract_encounter_fhir_id(resource)
        result_fhir_ids = _extract_reference_ids(resource.get("result", []))

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (dr:DiagnosticReport {fhir_id: $fhir_id})
            SET dr.code = $code,
                dr.display = $display,
                dr.system = $system,
                dr.status = $status,
                dr.effective_date = $effective_date,
                dr.issued = $issued,
                dr.encounter_fhir_id = $encounter_fhir_id,
                dr.result_fhir_ids = $result_fhir_ids,
                dr.fhir_resource = $fhir_resource,
                dr.updated_at = datetime()
            MERGE (p)-[:HAS_DIAGNOSTIC_REPORT]->(dr)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            status=resource.get("status"),
            effective_date=resource.get("effectiveDateTime"),
            issued=resource.get("issued"),
            encounter_fhir_id=encounter_fhir_id,
            result_fhir_ids=result_fhir_ids,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_immunization(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update Immunization node and HAS_IMMUNIZATION relationship."""
        first_coding = _extract_first_coding(resource.get("vaccineCode", {}))
        encounter_fhir_id = _extract_encounter_fhir_id(resource)

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (im:Immunization {fhir_id: $fhir_id})
            SET im.code = $code,
                im.display = $display,
                im.system = $system,
                im.status = $status,
                im.occurrence_date = $occurrence_date,
                im.encounter_fhir_id = $encounter_fhir_id,
                im.fhir_resource = $fhir_resource,
                im.updated_at = datetime()
            MERGE (p)-[:HAS_IMMUNIZATION]->(im)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            code=first_coding.get("code"),
            display=first_coding.get("display"),
            system=first_coding.get("system"),
            status=resource.get("status"),
            occurrence_date=resource.get("occurrenceDateTime"),
            encounter_fhir_id=encounter_fhir_id,
            fhir_resource=json.dumps(resource),
        )

    async def _upsert_careplan(
        self, session: AsyncSession, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """Create or update CarePlan node and HAS_CARE_PLAN relationship."""
        display = resource.get("title")
        if not display:
            for cat in resource.get("category", []):
                coding = _extract_first_coding(cat)
                if coding.get("display"):
                    display = coding["display"]
                    break

        encounter_fhir_id = _extract_encounter_fhir_id(resource)
        period = resource.get("period", {})
        addresses_fhir_ids = _extract_reference_ids(resource.get("addresses", []))

        await session.run(
            """
            MATCH (p:Patient {id: $patient_id})
            MERGE (cp:CarePlan {fhir_id: $fhir_id})
            SET cp.display = $display,
                cp.status = $status,
                cp.period_start = $period_start,
                cp.period_end = $period_end,
                cp.encounter_fhir_id = $encounter_fhir_id,
                cp.addresses_fhir_ids = $addresses_fhir_ids,
                cp.fhir_resource = $fhir_resource,
                cp.updated_at = datetime()
            MERGE (p)-[:HAS_CARE_PLAN]->(cp)
            """,
            patient_id=patient_id,
            fhir_id=resource.get("id"),
            display=display,
            status=resource.get("status"),
            period_start=period.get("start"),
            period_end=period.get("end"),
            encounter_fhir_id=encounter_fhir_id,
            addresses_fhir_ids=addresses_fhir_ids,
            fhir_resource=json.dumps(resource),
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
        for node_label, patient_rel, encounter_rel, alias in self._ENCOUNTER_RELATIONSHIPS:
            # Optimized query: starts from patient, uses indexed encounter_fhir_id
            await session.run(
                f"""
                MATCH (p:Patient {{id: $patient_id}})-[:HAS_ENCOUNTER]->(e:Encounter)
                MATCH (p)-[:{patient_rel}]->({alias}:{node_label})
                WHERE {alias}.encounter_fhir_id IS NOT NULL
                  AND {alias}.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:{encounter_rel}]->({alias})
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
            List of FHIR Condition resources with clinical_status = 'active'.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
                WHERE c.clinical_status = 'active'
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
            List of FHIR AllergyIntolerance resources with clinical_status = 'active'.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (p:Patient {id: $patient_id})-[:HAS_ALLERGY_INTOLERANCE]->(a:AllergyIntolerance)
                WHERE a.clinical_status = 'active'
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
                RETURN e, collect(DISTINCT c) as conditions,
                       collect(DISTINCT m) as medications,
                       collect(DISTINCT o) as observations,
                       collect(DISTINCT pr) as procedures,
                       collect(DISTINCT dr) as diagnostic_reports,
                       collect(DISTINCT im) as immunizations,
                       collect(DISTINCT cp) as care_plans
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

    async def get_diagnostic_report_results(
        self, report_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get observations contained in a diagnostic report.

        Args:
            report_fhir_id: The FHIR ID of the diagnostic report.

        Returns:
            List of parsed FHIR Observation resources.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (dr:DiagnosticReport {fhir_id: $report_id})-[:CONTAINS_RESULT]->(o:Observation)
                RETURN o.fhir_resource as resource
                """,
                report_id=report_fhir_id,
            )
            observations = []
            async for record in result:
                if record["resource"]:
                    observations.append(json.loads(record["resource"]))
            return observations

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
        ]

        if resource_types:
            searchable = [s for s in searchable if s[0] in resource_types]

        lower_terms = [t.lower() for t in query_terms if t]
        if not lower_terms and not resource_types:
            return []

        results: list[dict[str, str]] = []
        async with self._driver.session() as session:
            for label, rel, display_prop in searchable:
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

    # =========================================================================
    # Main Entry Points
    # =========================================================================

    async def build_from_fhir(
        self, patient_id: str, resources: list[dict[str, Any]]
    ) -> None:
        """
        Build graph nodes and relationships from FHIR resources.

        Uses two-pass approach within an explicit write transaction for atomicity:
        1. First pass: Create all nodes with Patient relationships
        2. Second pass: Build inter-resource relationships (Encounter-centric, TREATS, etc.)

        The explicit transaction ensures all-or-nothing semantics — if any write
        fails, the entire patient's graph changes are rolled back. This prevents
        partially-seeded graphs that cause missing data in queries.

        All operations are scoped to the specific patient for correctness
        and performance (avoids global graph scans).

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

                # First pass: create all resource nodes with Patient relationships
                for resource in resources:
                    resource_type = resource.get("resourceType")

                    if resource_type == "Condition":
                        await self._upsert_condition(tx, patient_id, resource)
                    elif resource_type == "MedicationRequest":
                        await self._upsert_medication_request(tx, patient_id, resource)
                    elif resource_type == "AllergyIntolerance":
                        await self._upsert_allergy_intolerance(tx, patient_id, resource)
                    elif resource_type == "Observation":
                        await self._upsert_observation(tx, patient_id, resource)
                    elif resource_type == "Encounter":
                        await self._upsert_encounter(tx, patient_id, resource)
                    elif resource_type == "Procedure":
                        await self._upsert_procedure(tx, patient_id, resource)
                    elif resource_type == "DiagnosticReport":
                        await self._upsert_diagnostic_report(tx, patient_id, resource)
                    elif resource_type == "Immunization":
                        await self._upsert_immunization(tx, patient_id, resource)
                    elif resource_type == "CarePlan":
                        await self._upsert_careplan(tx, patient_id, resource)

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
