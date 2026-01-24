"""Neo4j Knowledge Graph service for FHIR resource relationships."""

import json
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings


def _extract_reference_id(reference: str) -> str | None:
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
    """

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
        except Exception:
            return False

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

    async def _upsert_patient(self, patient_id: str, resource: dict[str, Any]) -> None:
        """
        Create or update Patient node with FHIR data.

        Uses MERGE for idempotency.
        """
        name_parts = resource.get("name", [{}])[0]
        given = name_parts.get("given", [""])[0] if name_parts.get("given") else ""
        family = name_parts.get("family", "")

        async with self._driver.session() as session:
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
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update Condition node and HAS_CONDITION relationship.

        Also stores encounter_fhir_id for later relationship building.

        Uses MERGE for idempotency.
        """
        # Extract condition code (first coding if available)
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Get clinical status
        clinical_status = resource.get("clinicalStatus", {})
        status_codings = clinical_status.get("coding", [{}])
        status_code = status_codings[0].get("code", "") if status_codings else ""

        # Extract encounter reference for later relationship building
        encounter_ref = resource.get("encounter", {}).get("reference")
        encounter_fhir_id = _extract_reference_id(encounter_ref) if encounter_ref else None

        async with self._driver.session() as session:
            await session.run(
                """
                MATCH (p:Patient {id: $patient_id})
                MERGE (c:Condition {fhir_id: $fhir_id})
                SET c.code = $code,
                    c.display = $display,
                    c.system = $system,
                    c.clinical_status = $clinical_status,
                    c.onset_date = $onset_date,
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
                encounter_fhir_id=encounter_fhir_id,
                fhir_resource=json.dumps(resource),
            )

    async def _upsert_medication_request(
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update MedicationRequest node and HAS_MEDICATION_REQUEST relationship.

        Stores encounter_fhir_id and reason_fhir_ids for later relationship building.

        Uses MERGE for idempotency.
        """
        # Extract medication code
        med_codeable = resource.get("medicationCodeableConcept", {})
        codings = med_codeable.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Extract encounter reference
        encounter_ref = resource.get("encounter", {}).get("reference")
        encounter_fhir_id = _extract_reference_id(encounter_ref) if encounter_ref else None

        # Extract reasonReference (conditions this medication treats)
        reason_refs = resource.get("reasonReference", [])
        reason_fhir_ids = [
            _extract_reference_id(ref.get("reference"))
            for ref in reason_refs
            if ref.get("reference")
        ]
        reason_fhir_ids = [r for r in reason_fhir_ids if r]  # Filter None values

        async with self._driver.session() as session:
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
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update AllergyIntolerance node and HAS_ALLERGY_INTOLERANCE relationship.

        Uses MERGE for idempotency.
        """
        # Extract allergy code
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Get clinical status
        clinical_status = resource.get("clinicalStatus", {})
        status_codings = clinical_status.get("coding", [{}])
        status_code = status_codings[0].get("code", "") if status_codings else ""

        async with self._driver.session() as session:
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
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update Observation node and HAS_OBSERVATION relationship.

        Stores encounter_fhir_id for later relationship building.

        Uses MERGE for idempotency.
        """
        # Extract observation code
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Extract value (handle different value types)
        value = None
        value_unit = None
        if "valueQuantity" in resource:
            value = resource["valueQuantity"].get("value")
            value_unit = resource["valueQuantity"].get("unit")
        elif "valueCodeableConcept" in resource:
            value_codings = resource["valueCodeableConcept"].get("coding", [{}])
            value = value_codings[0].get("display") if value_codings else None
        elif "valueString" in resource:
            value = resource["valueString"]

        # Extract encounter reference
        encounter_ref = resource.get("encounter", {}).get("reference")
        encounter_fhir_id = _extract_reference_id(encounter_ref) if encounter_ref else None

        async with self._driver.session() as session:
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
                    o.encounter_fhir_id = $encounter_fhir_id,
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
                encounter_fhir_id=encounter_fhir_id,
            )

    async def _upsert_encounter(
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update Encounter node and HAS_ENCOUNTER relationship.

        Uses MERGE for idempotency.
        """
        # Extract encounter type
        types = resource.get("type", [{}])
        first_type = types[0] if types else {}
        type_codings = first_type.get("coding", [{}])
        first_coding = type_codings[0] if type_codings else {}

        # Extract period
        period = resource.get("period", {})

        async with self._driver.session() as session:
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
            )

    async def _upsert_procedure(
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update Procedure node and HAS_PROCEDURE relationship.

        Stores encounter_fhir_id and reason_fhir_ids for later relationship building.

        Uses MERGE for idempotency.
        """
        # Extract procedure code
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Extract encounter reference
        encounter_ref = resource.get("encounter", {}).get("reference")
        encounter_fhir_id = _extract_reference_id(encounter_ref) if encounter_ref else None

        # Extract reasonReference (conditions this procedure treats)
        reason_refs = resource.get("reasonReference", [])
        reason_fhir_ids = [
            _extract_reference_id(ref.get("reference"))
            for ref in reason_refs
            if ref.get("reference")
        ]
        reason_fhir_ids = [r for r in reason_fhir_ids if r]

        # Extract performed date
        performed = resource.get("performedDateTime") or resource.get("performedPeriod", {}).get("start")

        async with self._driver.session() as session:
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
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update DiagnosticReport node and HAS_DIAGNOSTIC_REPORT relationship.

        Stores encounter_fhir_id and result_fhir_ids for later relationship building.

        Uses MERGE for idempotency.
        """
        # Extract code
        code_obj = resource.get("code", {})
        codings = code_obj.get("coding", [{}])
        first_coding = codings[0] if codings else {}

        # Extract encounter reference
        encounter_ref = resource.get("encounter", {}).get("reference")
        encounter_fhir_id = _extract_reference_id(encounter_ref) if encounter_ref else None

        # Extract result references (observations this report contains)
        result_refs = resource.get("result", [])
        result_fhir_ids = [
            _extract_reference_id(ref.get("reference"))
            for ref in result_refs
            if ref.get("reference")
        ]
        result_fhir_ids = [r for r in result_fhir_ids if r]

        async with self._driver.session() as session:
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

    async def _build_encounter_relationships(self) -> None:
        """
        Build Encounter-centric relationships in second pass.

        Creates relationships:
        - Encounter -[:DIAGNOSED]-> Condition
        - Encounter -[:PRESCRIBED]-> MedicationRequest
        - Encounter -[:RECORDED]-> Observation
        - Encounter -[:PERFORMED]-> Procedure
        - Encounter -[:REPORTED]-> DiagnosticReport
        """
        async with self._driver.session() as session:
            # Encounter -> Condition (DIAGNOSED)
            await session.run(
                """
                MATCH (e:Encounter), (c:Condition)
                WHERE c.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:DIAGNOSED]->(c)
                """
            )

            # Encounter -> MedicationRequest (PRESCRIBED)
            await session.run(
                """
                MATCH (e:Encounter), (m:MedicationRequest)
                WHERE m.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:PRESCRIBED]->(m)
                """
            )

            # Encounter -> Observation (RECORDED)
            await session.run(
                """
                MATCH (e:Encounter), (o:Observation)
                WHERE o.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:RECORDED]->(o)
                """
            )

            # Encounter -> Procedure (PERFORMED)
            await session.run(
                """
                MATCH (e:Encounter), (pr:Procedure)
                WHERE pr.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:PERFORMED]->(pr)
                """
            )

            # Encounter -> DiagnosticReport (REPORTED)
            await session.run(
                """
                MATCH (e:Encounter), (dr:DiagnosticReport)
                WHERE dr.encounter_fhir_id = e.fhir_id
                MERGE (e)-[:REPORTED]->(dr)
                """
            )

    async def _build_clinical_reasoning_relationships(self) -> None:
        """
        Build clinical reasoning relationships in second pass.

        Creates relationships:
        - MedicationRequest -[:TREATS]-> Condition
        - Procedure -[:TREATS]-> Condition
        - DiagnosticReport -[:CONTAINS_RESULT]-> Observation
        """
        async with self._driver.session() as session:
            # MedicationRequest -> Condition (TREATS)
            await session.run(
                """
                MATCH (m:MedicationRequest), (c:Condition)
                WHERE c.fhir_id IN m.reason_fhir_ids
                MERGE (m)-[:TREATS]->(c)
                """
            )

            # Procedure -> Condition (TREATS)
            await session.run(
                """
                MATCH (pr:Procedure), (c:Condition)
                WHERE c.fhir_id IN pr.reason_fhir_ids
                MERGE (pr)-[:TREATS]->(c)
                """
            )

            # DiagnosticReport -> Observation (CONTAINS_RESULT)
            await session.run(
                """
                MATCH (dr:DiagnosticReport), (o:Observation)
                WHERE o.fhir_id IN dr.result_fhir_ids
                MERGE (dr)-[:CONTAINS_RESULT]->(o)
                """
            )

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

    async def get_verified_facts(
        self, patient_id: str
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get all verified clinical facts from graph for a patient.

        Aggregates conditions, medications, and allergies into a single response.

        Args:
            patient_id: The canonical patient UUID.

        Returns:
            Dictionary with 'conditions', 'medications', and 'allergies' keys,
            each containing a list of FHIR resources.
        """
        conditions = await self.get_verified_conditions(patient_id)
        medications = await self.get_verified_medications(patient_id)
        allergies = await self.get_verified_allergies(patient_id)

        return {
            "conditions": conditions,
            "medications": medications,
            "allergies": allergies,
        }

    async def get_encounter_events(
        self, encounter_fhir_id: str
    ) -> dict[str, list[dict[str, Any]]]:
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
            Dictionary with keys for each resource type, containing lists of
            node property dictionaries (not full FHIR resources for performance).
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
                RETURN e, collect(DISTINCT c) as conditions,
                       collect(DISTINCT m) as medications,
                       collect(DISTINCT o) as observations,
                       collect(DISTINCT pr) as procedures,
                       collect(DISTINCT dr) as diagnostic_reports
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
                }

            return {
                "conditions": [dict(c) for c in record["conditions"] if c],
                "medications": [dict(m) for m in record["medications"] if m],
                "observations": [dict(o) for o in record["observations"] if o],
                "procedures": [dict(pr) for pr in record["procedures"] if pr],
                "diagnostic_reports": [dict(dr) for dr in record["diagnostic_reports"] if dr],
            }

    async def get_medications_treating_condition(
        self, condition_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get medications that treat a specific condition.

        Args:
            condition_fhir_id: The FHIR ID of the condition.

        Returns:
            List of MedicationRequest node properties.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {fhir_id: $condition_id})<-[:TREATS]-(m:MedicationRequest)
                RETURN m
                """,
                condition_id=condition_fhir_id,
            )
            medications = []
            async for record in result:
                if record["m"]:
                    medications.append(dict(record["m"]))
            return medications

    async def get_procedures_for_condition(
        self, condition_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get procedures performed for a specific condition.

        Args:
            condition_fhir_id: The FHIR ID of the condition.

        Returns:
            List of Procedure node properties.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (c:Condition {fhir_id: $condition_id})<-[:TREATS]-(pr:Procedure)
                RETURN pr
                """,
                condition_id=condition_fhir_id,
            )
            procedures = []
            async for record in result:
                if record["pr"]:
                    procedures.append(dict(record["pr"]))
            return procedures

    async def get_diagnostic_report_results(
        self, report_fhir_id: str
    ) -> list[dict[str, Any]]:
        """
        Get observations contained in a diagnostic report.

        Args:
            report_fhir_id: The FHIR ID of the diagnostic report.

        Returns:
            List of Observation node properties.
        """
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (dr:DiagnosticReport {fhir_id: $report_id})-[:CONTAINS_RESULT]->(o:Observation)
                RETURN o
                """,
                report_id=report_fhir_id,
            )
            observations = []
            async for record in result:
                if record["o"]:
                    observations.append(dict(record["o"]))
            return observations

    async def build_from_fhir(
        self, patient_id: str, resources: list[dict[str, Any]]
    ) -> None:
        """
        Build graph nodes and relationships from FHIR resources.

        Uses two-pass approach:
        1. First pass: Create all nodes with Patient relationships
        2. Second pass: Build inter-resource relationships (Encounter-centric, TREATS, etc.)

        Args:
            patient_id: The canonical patient UUID (PostgreSQL-generated).
            resources: List of FHIR resources belonging to this patient.
        """
        # First pass: find and create Patient node
        patient_resource = None
        for resource in resources:
            if resource.get("resourceType") == "Patient":
                patient_resource = resource
                break

        if patient_resource:
            await self._upsert_patient(patient_id, patient_resource)

        # First pass: create all resource nodes with Patient relationships
        for resource in resources:
            resource_type = resource.get("resourceType")

            if resource_type == "Condition":
                await self._upsert_condition(patient_id, resource)
            elif resource_type == "MedicationRequest":
                await self._upsert_medication_request(patient_id, resource)
            elif resource_type == "AllergyIntolerance":
                await self._upsert_allergy_intolerance(patient_id, resource)
            elif resource_type == "Observation":
                await self._upsert_observation(patient_id, resource)
            elif resource_type == "Encounter":
                await self._upsert_encounter(patient_id, resource)
            elif resource_type == "Procedure":
                await self._upsert_procedure(patient_id, resource)
            elif resource_type == "DiagnosticReport":
                await self._upsert_diagnostic_report(patient_id, resource)

        # Second pass: build inter-resource relationships
        await self._build_encounter_relationships()
        await self._build_clinical_reasoning_relationships()

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
