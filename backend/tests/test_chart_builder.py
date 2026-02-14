"""Tests for chart_builder service — deterministic FHIR → visualization transformers."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.chart_builder import (
    CHART_TYPES,
    _compute_trend_summary,
    _parse_time_range,
    build_chart_for_type,
    build_encounter_timeline,
    build_trend_chart,
)


# =============================================================================
# Fixtures
# =============================================================================

TEST_PATIENT_ID = uuid.uuid4()


def _make_observation(
    loinc_code: str,
    display: str,
    value: float,
    unit: str,
    date: str,
    *,
    category: str = "laboratory",
    fhir_id: str | None = None,
) -> dict:
    """Create a minimal FHIR Observation resource for testing."""
    return {
        "resourceType": "Observation",
        "id": fhir_id or f"obs-{loinc_code}-{date}",
        "status": "final",
        "category": [
            {"coding": [{"code": category}]}
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display,
                }
            ]
        },
        "effectiveDateTime": f"{date}T00:00:00Z",
        "valueQuantity": {"value": value, "unit": unit},
    }


def _make_encounter(
    enc_id: str,
    date: str,
    enc_type: str = "Outpatient visit",
    class_code: str = "AMB",
    *,
    reason: str | None = None,
) -> dict:
    """Create a minimal FHIR Encounter resource for testing."""
    enc: dict = {
        "resourceType": "Encounter",
        "id": enc_id,
        "status": "finished",
        "class": {"code": class_code},
        "type": [
            {"coding": [{"display": enc_type}]}
        ],
        "period": {"start": f"{date}T09:00:00Z", "end": f"{date}T09:30:00Z"},
    }
    if reason:
        enc["reasonCode"] = [{"coding": [{"display": reason}]}]
    return enc


def _make_medication_request(
    drug: str,
    authored_on: str,
    status: str = "active",
) -> dict:
    """Create a minimal FHIR MedicationRequest resource for testing."""
    return {
        "resourceType": "MedicationRequest",
        "id": f"med-{drug[:5]}-{authored_on}",
        "status": status,
        "medicationCodeableConcept": {
            "coding": [{"display": drug}]
        },
        "authoredOn": f"{authored_on}T00:00:00Z",
    }


async def _seed_resources(
    db: AsyncSession,
    patient_id: uuid.UUID,
    resources: list[dict],
) -> None:
    """Insert FHIR resources into the test database."""
    for res in resources:
        fhir_resource = FhirResource(
            fhir_id=res.get("id", str(uuid.uuid4())),
            resource_type=res["resourceType"],
            patient_id=patient_id,
            data=res,
        )
        db.add(fhir_resource)
    await db.flush()


# =============================================================================
# Unit tests for helper functions
# =============================================================================


class TestComputeTrendSummary:
    """Test _compute_trend_summary logic."""

    def test_empty_data_points(self):
        summary, status = _compute_trend_summary([], None)
        assert summary is None
        assert status is None

    def test_single_point_no_range(self):
        points = [{"date": "2024-01-01", "value": 5.0}]
        summary, status = _compute_trend_summary(points, None)
        assert summary is None
        assert status is None

    def test_single_point_normal(self):
        points = [{"date": "2024-01-01", "value": 5.0}]
        ref = {"low": 4.0, "high": 6.0}
        summary, status = _compute_trend_summary(points, ref)
        assert summary == "Within Normal Range"
        assert status == "positive"

    def test_single_point_above(self):
        points = [{"date": "2024-01-01", "value": 7.0}]
        ref = {"low": 4.0, "high": 6.0}
        summary, status = _compute_trend_summary(points, ref)
        assert summary == "Above Normal"
        assert status == "warning"

    def test_single_point_below(self):
        points = [{"date": "2024-01-01", "value": 3.0}]
        ref = {"low": 4.0, "high": 6.0}
        summary, status = _compute_trend_summary(points, ref)
        assert summary == "Below Normal"
        assert status == "warning"

    def test_increasing_trend(self):
        points = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-06-01", "value": 130.0},
        ]
        ref = {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0}
        summary, status = _compute_trend_summary(points, ref)
        assert "\u2191" in summary  # ↑
        assert "30%" in summary
        assert "Above Normal" in summary
        assert status == "warning"

    def test_decreasing_trend(self):
        points = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-06-01", "value": 80.0},
        ]
        ref = {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0}
        summary, status = _compute_trend_summary(points, ref)
        assert "\u2193" in summary  # ↓
        assert "20%" in summary
        assert "Normal" in summary
        assert status == "positive"

    def test_stable_trend(self):
        points = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-06-01", "value": 100.5},
        ]
        ref = {"low": 70.0, "high": 110.0, "critical_low": 40.0, "critical_high": 400.0}
        summary, status = _compute_trend_summary(points, ref)
        assert "\u2192" in summary  # →

    def test_critical_high(self):
        points = [
            {"date": "2024-01-01", "value": 100.0},
            {"date": "2024-06-01", "value": 500.0},
        ]
        ref = {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0}
        summary, status = _compute_trend_summary(points, ref)
        assert "Critical" in summary
        assert status == "critical"


class TestParseTimeRange:
    """Test _parse_time_range helper."""

    def test_years(self):
        result = _parse_time_range("1y")
        assert result is not None

    def test_months(self):
        result = _parse_time_range("6m")
        assert result is not None

    def test_days(self):
        result = _parse_time_range("30d")
        assert result is not None

    def test_invalid(self):
        result = _parse_time_range("invalid")
        assert result is None

    def test_empty(self):
        result = _parse_time_range("")
        assert result is None


# =============================================================================
# Integration tests (require database)
# =============================================================================


@pytest.mark.asyncio
class TestBuildTrendChart:
    """Test build_trend_chart with database queries."""

    async def test_no_data_returns_none(self, db_session: AsyncSession):
        result = await build_trend_chart(
            TEST_PATIENT_ID, db_session, loinc_codes=["4548-4"]
        )
        assert result is None

    async def test_empty_loinc_codes_returns_none(self, db_session: AsyncSession):
        result = await build_trend_chart(
            TEST_PATIENT_ID, db_session, loinc_codes=[]
        )
        assert result is None

    async def test_single_loinc_single_point(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        obs = _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-06-01")
        await _seed_resources(db_session, pid, [obs])

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is not None
        assert result["type"] == "trend_chart"
        assert "Hemoglobin A1c" in result["title"]
        assert len(result["series"]) == 1
        assert len(result["series"][0]["data_points"]) == 1
        assert result["series"][0]["data_points"][0]["value"] == 6.2
        assert result["current_value"] == "6.2 %"

    async def test_single_loinc_multiple_points(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        observations = [
            _make_observation("4548-4", "Hemoglobin A1c", 7.1, "%", "2024-01-15"),
            _make_observation("4548-4", "Hemoglobin A1c", 6.8, "%", "2024-04-15"),
            _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-07-15"),
        ]
        await _seed_resources(db_session, pid, observations)

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is not None
        assert len(result["series"]) == 1
        series = result["series"][0]
        assert len(series["data_points"]) == 3
        # Chronological order (asc)
        assert series["data_points"][0]["value"] == 7.1
        assert series["data_points"][-1]["value"] == 6.2
        # Latest value as current
        assert result["current_value"] == "6.2 %"
        # Trend should show decrease
        assert result["trend_summary"] is not None
        assert "\u2193" in result["trend_summary"]  # ↓

    async def test_hba1c_has_range_bands(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        obs = _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-06-01")
        await _seed_resources(db_session, pid, [obs])

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is not None
        assert result["range_bands"] is not None
        assert len(result["range_bands"]) >= 3  # Normal, Prediabetes, Diabetes
        # range_bands present → no reference_lines
        assert result["reference_lines"] is None

    async def test_lab_without_range_bands_has_reference_lines(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        # Hemoglobin (718-7) has reference ranges but NO range_bands
        obs = _make_observation("718-7", "Hemoglobin", 14.0, "g/dL", "2024-06-01")
        await _seed_resources(db_session, pid, [obs])

        result = await build_trend_chart(pid, db_session, loinc_codes=["718-7"])
        assert result is not None
        assert result["reference_lines"] is not None
        assert len(result["reference_lines"]) == 2  # Low + High
        assert result["range_bands"] is None

    async def test_multiple_loinc_codes(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        observations = [
            _make_observation("2093-3", "Total Cholesterol", 220.0, "mg/dL", "2024-06-01"),
            _make_observation("18262-6", "LDL Cholesterol", 140.0, "mg/dL", "2024-06-01"),
        ]
        await _seed_resources(db_session, pid, observations)

        result = await build_trend_chart(
            pid, db_session, loinc_codes=["2093-3", "18262-6"]
        )
        assert result is not None
        assert len(result["series"]) == 2
        assert "Total Cholesterol" in result["title"]
        assert "LDL Cholesterol" in result["title"]

    async def test_nonexistent_loinc_returns_none(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        obs = _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-06-01")
        await _seed_resources(db_session, pid, [obs])

        result = await build_trend_chart(
            pid, db_session, loinc_codes=["99999-9"]
        )
        assert result is None

    async def test_observations_without_value_skipped(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        # Observation without valueQuantity.value
        obs_no_value = {
            "resourceType": "Observation",
            "id": "obs-no-value",
            "status": "final",
            "code": {"coding": [{"code": "4548-4", "display": "Hemoglobin A1c"}]},
            "effectiveDateTime": "2024-06-01T00:00:00Z",
            "valueQuantity": {"unit": "%"},  # no value
        }
        await _seed_resources(db_session, pid, [obs_no_value])

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is None

    async def test_medication_timeline_included(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        resources = [
            _make_observation("4548-4", "Hemoglobin A1c", 7.1, "%", "2024-01-15"),
            _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-07-15"),
            _make_medication_request("Metformin 500mg", "2024-02-01"),
        ]
        await _seed_resources(db_session, pid, resources)

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is not None
        assert result["medications"] is not None
        assert len(result["medications"]) >= 1
        assert result["medications"][0]["drug"] == "Metformin 500mg"

    async def test_subtitle_shows_date_range(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        observations = [
            _make_observation("4548-4", "Hemoglobin A1c", 7.1, "%", "2024-01-15"),
            _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-07-15"),
        ]
        await _seed_resources(db_session, pid, observations)

        result = await build_trend_chart(pid, db_session, loinc_codes=["4548-4"])
        assert result is not None
        assert result["subtitle"] is not None
        assert "Jan" in result["subtitle"]
        assert "Jul" in result["subtitle"]


@pytest.mark.asyncio
class TestBuildEncounterTimeline:
    """Test build_encounter_timeline with database queries."""

    async def test_no_data_returns_none(self, db_session: AsyncSession):
        result = await build_encounter_timeline(TEST_PATIENT_ID, db_session)
        assert result is None

    async def test_single_encounter(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        enc = _make_encounter("enc-001", "2024-06-01")
        await _seed_resources(db_session, pid, [enc])

        result = await build_encounter_timeline(pid, db_session)
        assert result is not None
        assert result["type"] == "encounter_timeline"
        assert result["title"] == "Encounter Timeline"
        assert len(result["events"]) == 1
        assert result["events"][0]["title"] == "Outpatient visit"
        assert result["events"][0]["category"] == "AMB"

    async def test_multiple_encounters_sorted_desc(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        encounters = [
            _make_encounter("enc-001", "2024-01-15"),
            _make_encounter("enc-002", "2024-06-15", enc_type="Emergency room visit", class_code="EMER"),
            _make_encounter("enc-003", "2024-03-15", enc_type="Inpatient visit", class_code="IMP"),
        ]
        await _seed_resources(db_session, pid, encounters)

        result = await build_encounter_timeline(pid, db_session)
        assert result is not None
        assert len(result["events"]) == 3
        # Most recent first (desc order)
        assert result["events"][0]["category"] == "EMER"
        assert result["events"][1]["category"] == "IMP"
        assert result["events"][2]["category"] == "AMB"

    async def test_encounter_with_reason(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        enc = _make_encounter("enc-reason", "2024-06-01", reason="Hypertension")
        await _seed_resources(db_session, pid, [enc])

        result = await build_encounter_timeline(pid, db_session)
        assert result is not None
        assert result["events"][0]["detail"] == "Hypertension"

    async def test_encounter_without_reason(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        enc = _make_encounter("enc-noreason", "2024-06-01")
        await _seed_resources(db_session, pid, [enc])

        result = await build_encounter_timeline(pid, db_session)
        assert result is not None
        assert result["events"][0]["detail"] is None

    async def test_subtitle_shows_count(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        encounters = [
            _make_encounter("enc-a", "2024-01-15"),
            _make_encounter("enc-b", "2024-03-15"),
        ]
        await _seed_resources(db_session, pid, encounters)

        result = await build_encounter_timeline(pid, db_session)
        assert result is not None
        assert "2 encounters" in result["subtitle"]


@pytest.mark.asyncio
class TestBuildChartForType:
    """Test the dispatcher function."""

    async def test_unknown_type_returns_none(self, db_session: AsyncSession):
        result = await build_chart_for_type("invalid_type", TEST_PATIENT_ID, db_session)
        assert result is None

    async def test_trend_chart_dispatch(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        obs = _make_observation("4548-4", "Hemoglobin A1c", 6.2, "%", "2024-06-01")
        await _seed_resources(db_session, pid, [obs])

        result = await build_chart_for_type(
            "trend_chart", pid, db_session, loinc_codes=["4548-4"]
        )
        assert result is not None
        assert result["type"] == "trend_chart"

    async def test_encounter_timeline_dispatch(self, db_session: AsyncSession):
        pid = uuid.uuid4()
        enc = _make_encounter("enc-dispatch", "2024-06-01")
        await _seed_resources(db_session, pid, [enc])

        result = await build_chart_for_type(
            "encounter_timeline", pid, db_session
        )
        assert result is not None
        assert result["type"] == "encounter_timeline"


class TestChartTypes:
    """Test CHART_TYPES constant."""

    def test_expected_types(self):
        assert CHART_TYPES == {"trend_chart", "encounter_timeline"}
