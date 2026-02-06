"""Tests for compiler service.

Tests the pre-computed patient summary functions:
- get_latest_observations_by_category: latest obs per LOINC per category
- compute_observation_trends: trend computation for numeric observations
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.compiler import (
    OBSERVATION_CATEGORIES,
    TREND_THRESHOLD,
    _compute_trend,
    _extract_loinc_code,
    _parse_fhir_datetime,
    compute_observation_trends,
    get_latest_observations_by_category,
)


# =============================================================================
# Helper factories
# =============================================================================


def make_observation(
    loinc_code: str,
    category: str,
    effective_dt: str,
    value: float | None = None,
    unit: str = "mg/dL",
    display: str = "Test Observation",
    fhir_id: str | None = None,
) -> dict:
    """Build a minimal FHIR Observation dict."""
    obs = {
        "resourceType": "Observation",
        "id": fhir_id or f"obs-{loinc_code}-{effective_dt}",
        "code": {
            "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": display}],
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": category,
                    }
                ],
            }
        ],
        "effectiveDateTime": effective_dt,
    }
    if value is not None:
        obs["valueQuantity"] = {"value": value, "unit": unit}
    return obs


# =============================================================================
# Tests for get_latest_observations_by_category
# =============================================================================


class TestGetLatestObservationsByCategory:
    """Tests for fetching latest observations grouped by LOINC + category."""

    @pytest.mark.asyncio
    async def test_returns_latest_per_loinc_per_category(self, db_session: AsyncSession):
        """Should return only the most recent observation per LOINC code per category."""
        patient_id = uuid.uuid4()

        # Two glucose observations — only the latest should appear
        older_glucose = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 95.0)
        newer_glucose = make_observation("2345-7", "laboratory", "2024-06-15T10:00:00Z", 110.0)

        for obs in [older_glucose, newer_glucose]:
            db_session.add(FhirResource(
                fhir_id=obs["id"],
                resource_type="Observation",
                patient_id=patient_id,
                data=obs,
            ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_id)

        assert len(result["laboratory"]) == 1
        assert result["laboratory"][0]["effectiveDateTime"] == "2024-06-15T10:00:00Z"

    @pytest.mark.asyncio
    async def test_separates_categories(self, db_session: AsyncSession):
        """Should group observations into the correct categories."""
        patient_id = uuid.uuid4()

        vitals_obs = make_observation("8867-4", "vital-signs", "2024-06-01T10:00:00Z", 72.0)
        lab_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 95.0)
        survey_obs = make_observation("44249-1", "survey", "2024-06-01T10:00:00Z", 5.0)
        social_obs = make_observation("72166-2", "social-history", "2024-06-01T10:00:00Z")

        for obs in [vitals_obs, lab_obs, survey_obs, social_obs]:
            db_session.add(FhirResource(
                fhir_id=obs["id"],
                resource_type="Observation",
                patient_id=patient_id,
                data=obs,
            ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_id)

        assert len(result["vital-signs"]) == 1
        assert len(result["laboratory"]) == 1
        assert len(result["survey"]) == 1
        assert len(result["social-history"]) == 1

    @pytest.mark.asyncio
    async def test_excludes_unknown_categories(self, db_session: AsyncSession):
        """Observations with categories outside the known set should be excluded."""
        patient_id = uuid.uuid4()

        unknown_obs = make_observation("12345-6", "imaging", "2024-06-01T10:00:00Z", 1.0)
        db_session.add(FhirResource(
            fhir_id=unknown_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=unknown_obs,
        ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_id)

        for cat_list in result.values():
            assert len(cat_list) == 0

    @pytest.mark.asyncio
    async def test_patient_isolation(self, db_session: AsyncSession):
        """Should only return observations for the requested patient."""
        patient_a = uuid.uuid4()
        patient_b = uuid.uuid4()

        obs_a = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 95.0)
        obs_b = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 200.0)

        db_session.add(FhirResource(
            fhir_id=obs_a["id"],
            resource_type="Observation",
            patient_id=patient_a,
            data=obs_a,
        ))
        db_session.add(FhirResource(
            fhir_id=obs_b["id"],
            resource_type="Observation",
            patient_id=patient_b,
            data=obs_b,
        ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_a)

        assert len(result["laboratory"]) == 1
        assert result["laboratory"][0]["valueQuantity"]["value"] == 95.0

    @pytest.mark.asyncio
    async def test_string_patient_id(self, db_session: AsyncSession):
        """Should accept patient_id as a string."""
        patient_id = uuid.uuid4()

        obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 95.0)
        db_session.add(FhirResource(
            fhir_id=obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=obs,
        ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, str(patient_id))

        assert len(result["laboratory"]) == 1

    @pytest.mark.asyncio
    async def test_empty_result_for_no_observations(self, db_session: AsyncSession):
        """Should return empty lists for all categories when no observations exist."""
        patient_id = uuid.uuid4()

        result = await get_latest_observations_by_category(db_session, patient_id)

        for cat in OBSERVATION_CATEGORIES:
            assert result[cat] == []

    @pytest.mark.asyncio
    async def test_multiple_loinc_codes_same_category(self, db_session: AsyncSession):
        """Each LOINC code should get its own latest entry within a category."""
        patient_id = uuid.uuid4()

        glucose = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 95.0)
        creatinine = make_observation("2160-0", "laboratory", "2024-06-01T10:00:00Z", 1.2)

        for obs in [glucose, creatinine]:
            db_session.add(FhirResource(
                fhir_id=obs["id"],
                resource_type="Observation",
                patient_id=patient_id,
                data=obs,
            ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_id)

        assert len(result["laboratory"]) == 2

    @pytest.mark.asyncio
    async def test_includes_non_numeric_observations(self, db_session: AsyncSession):
        """Non-numeric observations (no valueQuantity) should still be returned."""
        patient_id = uuid.uuid4()

        obs = make_observation("72166-2", "social-history", "2024-06-01T10:00:00Z")
        db_session.add(FhirResource(
            fhir_id=obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=obs,
        ))
        await db_session.flush()

        result = await get_latest_observations_by_category(db_session, patient_id)

        assert len(result["social-history"]) == 1
        assert "valueQuantity" not in result["social-history"][0]


# =============================================================================
# Tests for compute_observation_trends
# =============================================================================


class TestComputeObservationTrends:
    """Tests for observation trend computation."""

    @pytest.mark.asyncio
    async def test_rising_trend(self, db_session: AsyncSession):
        """Should detect a rising trend when current > previous by more than 5%."""
        patient_id = uuid.uuid4()

        # Previous observation in the DB
        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        # Current observation to compute trend for
        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert len(result) == 1
        assert "_trend" in result[0]
        assert result[0]["_trend"]["direction"] == "rising"
        assert result[0]["_trend"]["delta"] == 20.0
        assert result[0]["_trend"]["delta_percent"] == 20.0
        assert result[0]["_trend"]["previous_value"] == 100.0

    @pytest.mark.asyncio
    async def test_falling_trend(self, db_session: AsyncSession):
        """Should detect a falling trend when current < previous by more than 5%."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 80.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["direction"] == "falling"
        assert result[0]["_trend"]["delta"] == -20.0
        assert result[0]["_trend"]["delta_percent"] == -20.0

    @pytest.mark.asyncio
    async def test_stable_trend(self, db_session: AsyncSession):
        """Should detect stable when change is within 5% threshold."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        # 3% change — within the 5% threshold
        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 103.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["direction"] == "stable"

    @pytest.mark.asyncio
    async def test_no_trend_for_single_observation(self, db_session: AsyncSession):
        """Should omit _trend when there is no previous observation."""
        patient_id = uuid.uuid4()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 100.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert len(result) == 1
        assert "_trend" not in result[0]

    @pytest.mark.asyncio
    async def test_no_trend_for_non_numeric(self, db_session: AsyncSession):
        """Non-numeric observations should be returned without _trend."""
        patient_id = uuid.uuid4()

        # Observation without valueQuantity (e.g., coded value)
        obs = make_observation("72166-2", "social-history", "2024-06-01T10:00:00Z")

        result = await compute_observation_trends(db_session, patient_id, [obs])

        assert len(result) == 1
        assert "_trend" not in result[0]

    @pytest.mark.asyncio
    async def test_zero_previous_value_nonzero_current(self, db_session: AsyncSession):
        """When previous is zero and current is nonzero, direction should be rising."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 0.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 5.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["direction"] == "rising"
        assert result[0]["_trend"]["delta_percent"] is None

    @pytest.mark.asyncio
    async def test_zero_previous_value_zero_current(self, db_session: AsyncSession):
        """When both previous and current are zero, direction should be stable."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 0.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 0.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["direction"] == "stable"
        assert result[0]["_trend"]["delta"] == 0.0
        assert result[0]["_trend"]["delta_percent"] is None

    @pytest.mark.asyncio
    async def test_timespan_days(self, db_session: AsyncSession):
        """Should compute correct timespan_days between observations."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        # ~152 days later
        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["timespan_days"] == 152

    @pytest.mark.asyncio
    async def test_previous_date_in_trend(self, db_session: AsyncSession):
        """Should include previous_date in trend metadata."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        assert result[0]["_trend"]["previous_date"] == "2024-01-01T10:00:00Z"

    @pytest.mark.asyncio
    async def test_multiple_observations_mixed(self, db_session: AsyncSession):
        """Should handle a mix of observations: some with trends, some without."""
        patient_id = uuid.uuid4()

        # Previous glucose in DB
        prev_glucose = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_glucose["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_glucose,
        ))
        await db_session.flush()

        # Current: glucose (has previous) + creatinine (no previous) + non-numeric
        current_glucose = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)
        current_creatinine = make_observation("2160-0", "laboratory", "2024-06-01T10:00:00Z", 1.2)
        current_social = make_observation("72166-2", "social-history", "2024-06-01T10:00:00Z")

        result = await compute_observation_trends(
            db_session, patient_id, [current_glucose, current_creatinine, current_social]
        )

        assert len(result) == 3
        assert "_trend" in result[0]  # glucose has previous
        assert "_trend" not in result[1]  # creatinine has no previous
        assert "_trend" not in result[2]  # non-numeric

    @pytest.mark.asyncio
    async def test_string_patient_id(self, db_session: AsyncSession):
        """Should accept patient_id as a string."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        result = await compute_observation_trends(db_session, str(patient_id), [current_obs])

        assert "_trend" in result[0]

    @pytest.mark.asyncio
    async def test_does_not_mutate_input(self, db_session: AsyncSession):
        """The original observation dicts should not be mutated."""
        patient_id = uuid.uuid4()

        prev_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_obs["id"],
            resource_type="Observation",
            patient_id=patient_id,
            data=prev_obs,
        ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        await compute_observation_trends(db_session, patient_id, [current_obs])

        # Original should not have _trend
        assert "_trend" not in current_obs

    @pytest.mark.asyncio
    async def test_picks_most_recent_previous(self, db_session: AsyncSession):
        """When multiple prior observations exist, should use the most recent one."""
        patient_id = uuid.uuid4()

        old_obs = make_observation("2345-7", "laboratory", "2023-01-01T10:00:00Z", 80.0)
        recent_obs = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)

        for obs in [old_obs, recent_obs]:
            db_session.add(FhirResource(
                fhir_id=obs["id"],
                resource_type="Observation",
                patient_id=patient_id,
                data=obs,
            ))
        await db_session.flush()

        current_obs = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)

        result = await compute_observation_trends(db_session, patient_id, [current_obs])

        # Should compare against 100.0 (the most recent previous), not 80.0
        assert result[0]["_trend"]["previous_value"] == 100.0
        assert result[0]["_trend"]["delta"] == 20.0


# =============================================================================
# Tests for pure helper functions
# =============================================================================


class TestExtractLoincCode:
    def test_extracts_code(self):
        obs = {"code": {"coding": [{"code": "2345-7"}]}}
        assert _extract_loinc_code(obs) == "2345-7"

    def test_missing_code(self):
        assert _extract_loinc_code({}) is None

    def test_empty_coding(self):
        obs = {"code": {"coding": []}}
        assert _extract_loinc_code(obs) is None


class TestComputeTrend:
    def test_rising(self):
        trend = _compute_trend(120.0, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "rising"
        assert trend["delta"] == 20.0
        assert trend["delta_percent"] == 20.0

    def test_falling(self):
        trend = _compute_trend(80.0, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "falling"
        assert trend["delta"] == -20.0
        assert trend["delta_percent"] == -20.0

    def test_stable_within_threshold(self):
        trend = _compute_trend(103.0, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "stable"

    def test_exact_threshold_is_stable(self):
        # 5% change exactly — should be stable (<=5%)
        trend = _compute_trend(105.0, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "stable"

    def test_just_above_threshold_is_rising(self):
        # 5.1% change — should be rising
        trend = _compute_trend(105.1, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "rising"

    def test_zero_previous_nonzero_current(self):
        trend = _compute_trend(5.0, 0.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "rising"
        assert trend["delta_percent"] is None

    def test_zero_previous_zero_current(self):
        trend = _compute_trend(0.0, 0.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "stable"
        assert trend["delta_percent"] is None

    def test_timespan_computation(self):
        trend = _compute_trend(120.0, 100.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["timespan_days"] == 152


class TestParseFhirDatetime:
    def test_z_suffix(self):
        dt = _parse_fhir_datetime("2024-01-15T10:30:00Z")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_offset_format(self):
        dt = _parse_fhir_datetime("2024-01-15T10:30:00+00:00")
        assert dt.year == 2024

    def test_date_only(self):
        dt = _parse_fhir_datetime("2024-01-15")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
