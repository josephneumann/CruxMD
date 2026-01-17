"""Neo4j Knowledge Graph service for FHIR resource relationships."""

import json
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings


class KnowledgeGraph:
    """
    Neo4j graph service with FHIR-aware node creation.

    Provides verified facts via explicit typed relationships.
    Node labels match FHIR resource types exactly:
    - Patient HAS_CONDITION Condition
    - Patient HAS_MEDICATION_REQUEST MedicationRequest
    - Patient HAS_ALLERGY_INTOLERANCE AllergyIntolerance
    - Patient HAS_OBSERVATION Observation
    - Patient HAS_ENCOUNTER Encounter
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

    async def _upsert_patient(
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
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
                fhir_resource=json.dumps(resource),
            )

    async def _upsert_medication_request(
        self, patient_id: str, resource: dict[str, Any]
    ) -> None:
        """
        Create or update MedicationRequest node and HAS_MEDICATION_REQUEST relationship.

        Uses MERGE for idempotency.
        """
        # Extract medication code
        med_codeable = resource.get("medicationCodeableConcept", {})
        codings = med_codeable.get("coding", [{}])
        first_coding = codings[0] if codings else {}

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

    async def build_from_fhir(
        self, patient_id: str, resources: list[dict[str, Any]]
    ) -> None:
        """
        Build graph nodes and relationships from FHIR resources.

        Creates Patient node first, then related resources with relationships.

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

        # Second pass: create related resources
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
