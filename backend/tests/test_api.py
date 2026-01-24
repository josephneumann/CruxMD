"""Integration tests for API endpoints.

Tests the full API request/response cycle that require PostgreSQL.
Unit tests for validation, auth, health, and router structure are in
their respective test files (test_fhir.py, test_auth.py, test_health.py,
test_patients.py).

Requires PostgreSQL to be running.
"""

import pytest


@pytest.mark.integration
class TestFhirLoadBundleIntegration:
    """Integration tests for POST /api/fhir/load-bundle endpoint.

    Requires PostgreSQL to be running.
    """

    @pytest.mark.asyncio
    async def test_loads_patient_bundle_successfully(
        self, client, auth_headers, test_engine, sample_patient
    ):
        """Should successfully load a bundle with a Patient resource."""
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        response = await client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Bundle loaded successfully"
        assert data["resources_loaded"] == 1
        assert data["patient_id"] is not None

    @pytest.mark.asyncio
    async def test_loads_bundle_with_multiple_resources(
        self, client, auth_headers, test_engine, sample_patient, sample_condition, sample_medication
    ):
        """Should load bundle with Patient and related resources."""
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {"resource": sample_patient},
                {"resource": sample_condition},
                {"resource": sample_medication},
            ],
        }
        response = await client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resources_loaded"] == 3
        assert data["patient_id"] is not None


@pytest.mark.integration
class TestPatientsApiIntegration:
    """Integration tests for /api/patients endpoints.

    Requires PostgreSQL to be running.
    """

    @pytest.mark.asyncio
    async def test_list_patients_empty(self, client, auth_headers, test_engine):
        """Should return empty list when no patients exist."""
        response = await client.get("/api/patients", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_patients_after_load(
        self, client, auth_headers, test_engine, sample_patient
    ):
        """Should return patients after loading a bundle."""
        # Load a patient first
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        load_response = await client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert load_response.status_code == 200

        # Now list patients
        response = await client.get("/api/patients", headers=auth_headers)
        assert response.status_code == 200
        patients = response.json()
        assert len(patients) >= 1
        # Find our patient
        patient = next(
            (p for p in patients if p["fhir_id"] == sample_patient["id"]), None
        )
        assert patient is not None
        assert patient["data"]["name"][0]["family"] == "Smith"

    @pytest.mark.asyncio
    async def test_get_patient_by_id(
        self, client, auth_headers, test_engine, sample_patient
    ):
        """Should return patient details by ID."""
        # Load a patient first
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        load_response = await client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        patient_id = load_response.json()["patient_id"]

        # Get the patient
        response = await client.get(
            f"/api/patients/{patient_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["fhir_id"] == sample_patient["id"]
        assert data["data"]["resourceType"] == "Patient"

    @pytest.mark.asyncio
    async def test_get_patient_not_found(self, client, auth_headers, test_engine):
        """Should return 404 for nonexistent patient."""
        import uuid
        fake_id = uuid.uuid4()
        response = await client.get(
            f"/api/patients/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Patient not found"
