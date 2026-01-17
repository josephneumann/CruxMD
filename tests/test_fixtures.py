"""Tests for Synthea fixture generation."""
import json
from pathlib import Path


class TestFixturesExist:
    """Verify that fixtures are present and valid."""

    def test_fixtures_directory_exists(self, fixtures_dir: Path):
        """Fixtures directory should exist."""
        assert fixtures_dir.exists(), f"Fixtures directory not found: {fixtures_dir}"
        assert fixtures_dir.is_dir()

    def test_five_patient_bundles_exist(self, fixtures_dir: Path):
        """Should have exactly 5 patient bundles."""
        bundles = list(fixtures_dir.glob("patient_bundle_*.json"))
        assert len(bundles) == 5, f"Expected 5 bundles, found {len(bundles)}"

    def test_bundles_named_correctly(self, fixtures_dir: Path):
        """Bundles should be named patient_bundle_1.json through patient_bundle_5.json."""
        for i in range(1, 6):
            bundle_path = fixtures_dir / f"patient_bundle_{i}.json"
            assert bundle_path.exists(), f"Missing bundle: {bundle_path}"


class TestBundleStructure:
    """Verify FHIR bundle structure."""

    def test_bundle_is_valid_json(self, sample_bundle: dict):
        """Bundle should be valid JSON (loaded by fixture)."""
        assert sample_bundle is not None
        assert isinstance(sample_bundle, dict)

    def test_bundle_is_fhir_bundle(self, sample_bundle: dict):
        """Bundle should have resourceType Bundle."""
        assert sample_bundle.get("resourceType") == "Bundle"

    def test_bundle_has_entries(self, sample_bundle: dict):
        """Bundle should have entries."""
        entries = sample_bundle.get("entry", [])
        assert len(entries) > 0, "Bundle should have at least one entry"

    def test_bundle_contains_patient(self, sample_bundle: dict):
        """Bundle should contain a Patient resource."""
        entries = sample_bundle.get("entry", [])
        patient_entries = [
            e for e in entries
            if e.get("resource", {}).get("resourceType") == "Patient"
        ]
        assert len(patient_entries) == 1, "Bundle should have exactly one Patient"


class TestAllBundles:
    """Verify all bundles have expected content."""

    def test_all_bundles_are_valid_fhir(self, all_bundles: list[dict]):
        """All bundles should be valid FHIR Bundles."""
        assert len(all_bundles) == 5
        for i, bundle in enumerate(all_bundles):
            assert bundle.get("resourceType") == "Bundle", f"Bundle {i+1} is not a FHIR Bundle"
            assert len(bundle.get("entry", [])) > 0, f"Bundle {i+1} has no entries"

    def test_all_bundles_have_patient(self, all_bundles: list[dict]):
        """Each bundle should contain exactly one Patient resource."""
        for i, bundle in enumerate(all_bundles):
            entries = bundle.get("entry", [])
            patients = [
                e for e in entries
                if e.get("resource", {}).get("resourceType") == "Patient"
            ]
            assert len(patients) == 1, f"Bundle {i+1} should have exactly one Patient"

    def test_all_patients_are_unique(self, all_bundles: list[dict]):
        """All patients should have unique FHIR IDs."""
        patient_ids = set()
        for i, bundle in enumerate(all_bundles):
            entries = bundle.get("entry", [])
            for entry in entries:
                resource = entry.get("resource", {})
                if resource.get("resourceType") == "Patient":
                    patient_id = resource.get("id")
                    assert patient_id not in patient_ids, f"Duplicate patient ID: {patient_id}"
                    patient_ids.add(patient_id)

        assert len(patient_ids) == 5, f"Expected 5 unique patients, found {len(patient_ids)}"

    def test_bundles_have_common_resource_types(self, all_bundles: list[dict]):
        """Bundles should contain typical FHIR resource types."""
        expected_types = {"Patient", "Encounter", "Condition", "Observation"}

        for i, bundle in enumerate(all_bundles):
            entries = bundle.get("entry", [])
            resource_types = {
                e.get("resource", {}).get("resourceType")
                for e in entries
            }

            for expected_type in expected_types:
                assert expected_type in resource_types, (
                    f"Bundle {i+1} missing expected resource type: {expected_type}"
                )
