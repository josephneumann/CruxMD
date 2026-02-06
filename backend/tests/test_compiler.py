"""Tests for compiler service.

Tests the pre-computed patient summary functions:
- get_latest_observations_by_category: latest obs per LOINC per category
- compute_observation_trends: trend computation for numeric observations
- compile_node_context: batch-fetch and prune all connections from a graph node
- fetch_resources_by_fhir_ids: batch Postgres lookup
- prune_and_enrich: prune + attach synthetic fields
- compute_medication_recency: recency signals for medications
- compute_dose_history: dose history for active medications
- infer_medication_condition_links: encounter-inferred med-condition links
"""

import base64
import copy
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph
from app.services.compiler import (
    OBSERVATION_CATEGORIES,
    TREND_THRESHOLD,  # noqa: F401 — used by TestComputeTrend for threshold assertions
    _compute_trend,
    _extract_dosage_text,
    _extract_loinc_code,
    _extract_med_display,
    _parse_fhir_datetime,
    compile_node_context,
    compute_dose_history,
    compute_medication_recency,
    compute_observation_trends,
    fetch_resources_by_fhir_ids,
    get_latest_observations_by_category,
    infer_medication_condition_links,
    prune_and_enrich,
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

    @pytest.mark.asyncio
    async def test_patient_isolation_for_trends(self, db_session: AsyncSession):
        """Trends for patient A should not use patient B's observation history."""
        patient_a = uuid.uuid4()
        patient_b = uuid.uuid4()

        # Patient B has a previous glucose of 200.0
        prev_b = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 200.0)
        db_session.add(FhirResource(
            fhir_id=prev_b["id"] + "-b",
            resource_type="Observation",
            patient_id=patient_b,
            data=prev_b,
        ))

        # Patient A has a previous glucose of 100.0
        prev_a = make_observation("2345-7", "laboratory", "2024-01-01T10:00:00Z", 100.0)
        db_session.add(FhirResource(
            fhir_id=prev_a["id"] + "-a",
            resource_type="Observation",
            patient_id=patient_a,
            data=prev_a,
        ))
        await db_session.flush()

        # Compute trends for patient A with current glucose 120.0
        current_a = make_observation("2345-7", "laboratory", "2024-06-01T10:00:00Z", 120.0)
        result = await compute_observation_trends(db_session, patient_a, [current_a])

        assert len(result) == 1
        assert "_trend" in result[0]
        # Delta should be 20.0 (120 - 100), NOT -80.0 (120 - 200)
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

    def test_zero_previous_negative_current(self):
        trend = _compute_trend(-3.0, 0.0, "2024-06-01T10:00:00Z", "2024-01-01T10:00:00Z")
        assert trend["direction"] == "falling"
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

    def test_non_utc_offset(self):
        dt = _parse_fhir_datetime("2024-01-15T10:30:00+05:30")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15
        assert dt.hour == 10
        assert dt.minute == 30
        assert dt.utcoffset().total_seconds() == 5 * 3600 + 30 * 60

    def test_negative_offset(self):
        dt = _parse_fhir_datetime("2024-01-15T10:30:00-04:00")
        assert dt.year == 2024
        assert dt.hour == 10
        assert dt.utcoffset().total_seconds() == -4 * 3600

    def test_date_only(self):
        dt = _parse_fhir_datetime("2024-01-15")
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15


# =============================================================================
# prune_and_enrich tests
# =============================================================================


class TestPruneAndEnrich:
    """Tests for prune_and_enrich()."""

    def test_prunes_fhir_boilerplate(self):
        """FHIR boilerplate keys like meta and text are stripped."""
        resource = {
            "resourceType": "Condition",
            "id": "cond-1",
            "meta": {"versionId": "1", "lastUpdated": "2024-01-01"},
            "text": {"div": "<div>HTML</div>"},
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": "123", "display": "Hypertension"}],
            },
            "clinicalStatus": {
                "coding": [{"code": "active"}],
            },
        }
        result = prune_and_enrich(resource)
        assert "meta" not in result
        assert "text" not in result
        assert result["resourceType"] == "Condition"
        assert result["id"] == "cond-1"

    def test_attaches_enrichments(self):
        """Enrichment fields are attached to the pruned resource."""
        resource = {
            "resourceType": "Observation",
            "id": "obs-1",
            "code": {"coding": [{"code": "12345", "display": "Glucose"}]},
        }
        enrichments = {
            "_trend": {"direction": "rising", "delta": 10.0},
            "_recency": "new",
        }
        result = prune_and_enrich(resource, enrichments=enrichments)
        assert result["_trend"]["direction"] == "rising"
        assert result["_recency"] == "new"

    def test_no_enrichments(self):
        """Works without enrichments."""
        resource = {
            "resourceType": "Condition",
            "id": "cond-1",
            "code": {"coding": [{"code": "123", "display": "Diabetes"}]},
        }
        result = prune_and_enrich(resource)
        assert result["id"] == "cond-1"
        assert "_trend" not in result

    def test_document_reference_decodes_note(self):
        """DocumentReference base64 content is decoded to clinical_note."""
        note_text = "Patient presents with chest pain and shortness of breath."
        encoded = base64.b64encode(note_text.encode()).decode()
        resource = {
            "resourceType": "DocumentReference",
            "id": "doc-1",
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "data": encoded,
                    }
                }
            ],
        }
        result = prune_and_enrich(resource)
        assert result["clinical_note"] == note_text
        assert "content" not in result  # raw content replaced


# =============================================================================
# fetch_resources_by_fhir_ids tests
# =============================================================================


class TestFetchResourcesByFhirIds:
    """Tests for fetch_resources_by_fhir_ids() with real DB."""

    @pytest.mark.asyncio
    async def test_returns_matching_resources(self, db_session: AsyncSession):
        """Returns resources matching the given fhir_ids."""
        patient_id = uuid.uuid4()
        r1 = FhirResource(
            fhir_id="cond-abc",
            resource_type="Condition",
            patient_id=patient_id,
            data={"resourceType": "Condition", "id": "cond-abc", "code": {"text": "Diabetes"}},
        )
        r2 = FhirResource(
            fhir_id="med-xyz",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data={"resourceType": "MedicationRequest", "id": "med-xyz", "status": "active"},
        )
        db_session.add_all([r1, r2])
        await db_session.flush()

        result = await fetch_resources_by_fhir_ids(
            db_session, ["cond-abc", "med-xyz"], patient_id=patient_id
        )
        assert len(result) == 2
        assert "cond-abc" in result
        assert "med-xyz" in result
        assert result["cond-abc"]["resourceType"] == "Condition"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_matches(self, db_session: AsyncSession):
        """Returns empty dict when no fhir_ids match."""
        result = await fetch_resources_by_fhir_ids(
            db_session, ["nonexistent-id"], patient_id=uuid.uuid4()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self, db_session: AsyncSession):
        """Returns empty dict for empty fhir_ids list."""
        result = await fetch_resources_by_fhir_ids(db_session, [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_patient_scoping(self, db_session: AsyncSession):
        """Only returns resources belonging to the specified patient."""
        patient_a = uuid.uuid4()
        patient_b = uuid.uuid4()
        r1 = FhirResource(
            fhir_id="cond-a",
            resource_type="Condition",
            patient_id=patient_a,
            data={"resourceType": "Condition", "id": "cond-a"},
        )
        r2 = FhirResource(
            fhir_id="cond-b",
            resource_type="Condition",
            patient_id=patient_b,
            data={"resourceType": "Condition", "id": "cond-b"},
        )
        db_session.add_all([r1, r2])
        await db_session.flush()

        result = await fetch_resources_by_fhir_ids(
            db_session, ["cond-a", "cond-b"], patient_id=patient_a
        )
        assert len(result) == 1
        assert "cond-a" in result
        assert "cond-b" not in result

    @pytest.mark.asyncio
    async def test_no_patient_scoping(self, db_session: AsyncSession):
        """Without patient_id, returns all matching resources."""
        patient_a = uuid.uuid4()
        r1 = FhirResource(
            fhir_id="med-shared",
            resource_type="Medication",
            patient_id=None,
            data={"resourceType": "Medication", "id": "med-shared"},
        )
        db_session.add(r1)
        await db_session.flush()

        result = await fetch_resources_by_fhir_ids(db_session, ["med-shared"])
        assert len(result) == 1
        assert "med-shared" in result

    @pytest.mark.asyncio
    async def test_string_patient_id(self, db_session: AsyncSession):
        """Accepts string patient_id and converts to UUID."""
        patient_id = uuid.uuid4()
        r1 = FhirResource(
            fhir_id="obs-1",
            resource_type="Observation",
            patient_id=patient_id,
            data={"resourceType": "Observation", "id": "obs-1"},
        )
        db_session.add(r1)
        await db_session.flush()

        result = await fetch_resources_by_fhir_ids(
            db_session, ["obs-1"], patient_id=str(patient_id)
        )
        assert len(result) == 1


# =============================================================================
# compile_node_context tests (mocked graph + db)
# =============================================================================


class TestCompileNodeContext:
    """Tests for compile_node_context() with mocked graph and db."""

    @pytest.mark.asyncio
    async def test_returns_grouped_connections_for_condition(self):
        """Given a Condition, returns connections grouped by relationship."""
        patient_id = str(uuid.uuid4())

        # Mock graph returns connections
        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "TREATS",
                "direction": "incoming",
                "fhir_id": "med-1",
                "resource_type": "MedicationRequest",
                "name": None,
                "fhir_resource": None,
            },
            {
                "relationship": "ADDRESSES",
                "direction": "incoming",
                "fhir_id": "cp-1",
                "resource_type": "CarePlan",
                "name": None,
                "fhir_resource": None,
            },
        ]

        # Mock db session that returns resources
        med_data = {
            "resourceType": "MedicationRequest",
            "id": "med-1",
            "status": "active",
            "medicationCodeableConcept": {
                "coding": [{"display": "Metformin"}],
            },
        }
        cp_data = {
            "resourceType": "CarePlan",
            "id": "cp-1",
            "status": "active",
        }

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(fhir_id="med-1", data=med_data),
            MagicMock(fhir_id="cp-1", data=cp_data),
        ]
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("cond-1", patient_id, mock_graph, mock_db)

        assert "TREATS" in result
        assert "ADDRESSES" in result
        assert len(result["TREATS"]) == 1
        assert len(result["ADDRESSES"]) == 1
        assert result["TREATS"][0]["id"] == "med-1"
        assert result["ADDRESSES"][0]["id"] == "cp-1"

        mock_graph.get_all_connections.assert_called_once_with(
            "cond-1", patient_id=patient_id
        )

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_connections(self):
        """Returns empty dict when the node has no connections."""
        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = []

        mock_db = AsyncMock(spec=AsyncSession)

        result = await compile_node_context(
            "isolated-node", str(uuid.uuid4()), mock_graph, mock_db
        )
        assert result == {}
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_document_reference_has_decoded_note(self):
        """DocumentReference connections have decoded clinical_note."""
        patient_id = str(uuid.uuid4())
        note_text = "Assessment: Patient stable. Plan: Continue current medications."
        encoded = base64.b64encode(note_text.encode()).decode()

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "DOCUMENTED",
                "direction": "outgoing",
                "fhir_id": "doc-1",
                "resource_type": "DocumentReference",
                "name": None,
                "fhir_resource": None,
            },
        ]

        doc_data = {
            "resourceType": "DocumentReference",
            "id": "doc-1",
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "data": encoded,
                    }
                }
            ],
        }

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(fhir_id="doc-1", data=doc_data),
        ]
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("enc-1", patient_id, mock_graph, mock_db)

        assert "DOCUMENTED" in result
        assert len(result["DOCUMENTED"]) == 1
        assert result["DOCUMENTED"][0]["clinical_note"] == note_text

    @pytest.mark.asyncio
    async def test_resources_are_pruned(self):
        """Resources have FHIR boilerplate stripped."""
        patient_id = str(uuid.uuid4())

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "TREATS",
                "direction": "incoming",
                "fhir_id": "med-1",
                "resource_type": "MedicationRequest",
                "name": None,
                "fhir_resource": None,
            },
        ]

        med_data = {
            "resourceType": "MedicationRequest",
            "id": "med-1",
            "meta": {"versionId": "1", "lastUpdated": "2024-01-01"},
            "text": {"div": "<div>HTML</div>"},
            "status": "active",
        }

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [
            MagicMock(fhir_id="med-1", data=med_data),
        ]
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("cond-1", patient_id, mock_graph, mock_db)

        pruned_med = result["TREATS"][0]
        assert "meta" not in pruned_med
        assert "text" not in pruned_med
        assert pruned_med["status"] == "active"

    @pytest.mark.asyncio
    async def test_batch_fetch_not_n_plus_1(self):
        """All resources fetched in batch, not one-by-one."""
        patient_id = str(uuid.uuid4())

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "TREATS",
                "direction": "incoming",
                "fhir_id": f"med-{i}",
                "resource_type": "MedicationRequest",
                "name": None,
                "fhir_resource": None,
            }
            for i in range(5)
        ]

        resources = [
            MagicMock(
                fhir_id=f"med-{i}",
                data={"resourceType": "MedicationRequest", "id": f"med-{i}", "status": "active"},
            )
            for i in range(5)
        ]

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = resources
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("cond-1", patient_id, mock_graph, mock_db)

        assert len(result["TREATS"]) == 5
        # Single batch query for all resources
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_medication_without_patient_id_fetched(self):
        """Medication nodes (no patient_id) are fetched via OR condition."""
        patient_id = str(uuid.uuid4())

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "TREATS",
                "direction": "incoming",
                "fhir_id": "med-shared",
                "resource_type": "Medication",
                "name": None,
                "fhir_resource": None,
            },
        ]

        med_data = {
            "resourceType": "Medication",
            "id": "med-shared",
            "code": {"coding": [{"display": "Aspirin"}]},
        }

        # Single query returns shared medication (patient_id=NULL matches OR condition)
        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = [MagicMock(fhir_id="med-shared", data=med_data)]
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("cond-1", patient_id, mock_graph, mock_db)

        assert "TREATS" in result
        assert len(result["TREATS"]) == 1
        assert result["TREATS"][0]["id"] == "med-shared"
        # Single DB call with OR condition
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_skips_resource_missing_from_postgres(self):
        """Resources in graph but not in Postgres are skipped."""
        patient_id = str(uuid.uuid4())

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "TREATS",
                "direction": "incoming",
                "fhir_id": "ghost-med",
                "resource_type": "MedicationRequest",
                "name": None,
                "fhir_resource": None,
            },
        ]

        mock_db = AsyncMock(spec=AsyncSession)
        empty_result = MagicMock()
        empty_result.all.return_value = []
        mock_db.execute.return_value = empty_result

        result = await compile_node_context("cond-1", patient_id, mock_graph, mock_db)

        # Ghost resource skipped — no TREATS key since it was the only connection
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_relationship_types(self):
        """Connections are properly grouped by relationship type."""
        patient_id = str(uuid.uuid4())

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            {
                "relationship": "DIAGNOSED",
                "direction": "outgoing",
                "fhir_id": "cond-1",
                "resource_type": "Condition",
                "name": None,
                "fhir_resource": None,
            },
            {
                "relationship": "PRESCRIBED",
                "direction": "outgoing",
                "fhir_id": "med-1",
                "resource_type": "MedicationRequest",
                "name": None,
                "fhir_resource": None,
            },
            {
                "relationship": "DIAGNOSED",
                "direction": "outgoing",
                "fhir_id": "cond-2",
                "resource_type": "Condition",
                "name": None,
                "fhir_resource": None,
            },
        ]

        resources = [
            MagicMock(
                fhir_id="cond-1",
                data={"resourceType": "Condition", "id": "cond-1"},
            ),
            MagicMock(
                fhir_id="med-1",
                data={"resourceType": "MedicationRequest", "id": "med-1", "status": "active"},
            ),
            MagicMock(
                fhir_id="cond-2",
                data={"resourceType": "Condition", "id": "cond-2"},
            ),
        ]

        mock_db = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.all.return_value = resources
        mock_db.execute.return_value = mock_result

        result = await compile_node_context("enc-1", patient_id, mock_graph, mock_db)

        assert len(result["DIAGNOSED"]) == 2
        assert len(result["PRESCRIBED"]) == 1


# =============================================================================
# Tests for compute_medication_recency
# =============================================================================


def _make_med_request(
    fhir_id: str = "med-1",
    display: str = "Lisinopril 10 MG",
    status: str = "active",
    authored_on: str | None = "2025-06-01",
    dosage_text: str | None = None,
    dose_value: float | None = None,
    dose_unit: str | None = None,
) -> dict:
    """Build a minimal FHIR MedicationRequest dict for testing."""
    med: dict = {
        "resourceType": "MedicationRequest",
        "id": fhir_id,
        "status": status,
        "medicationCodeableConcept": {
            "coding": [{"display": display}],
        },
    }
    if authored_on:
        med["authoredOn"] = authored_on
    if dosage_text or dose_value is not None:
        instruction: dict = {}
        if dosage_text:
            instruction["text"] = dosage_text
        if dose_value is not None:
            instruction["doseAndRate"] = [
                {"doseQuantity": {"value": dose_value, "unit": dose_unit or "MG"}}
            ]
        med["dosageInstruction"] = [instruction]
    return med


class TestComputeMedicationRecency:
    """Tests for compute_medication_recency()."""

    def test_new_medication(self):
        """Medication authored <30 days ago should be 'new'."""
        med = _make_med_request(authored_on="2026-01-15")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "new"
        assert result["_duration_days"] == 17

    def test_recent_medication(self):
        """Medication authored 30-180 days ago should be 'recent'."""
        med = _make_med_request(authored_on="2025-09-01")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "recent"
        assert result["_duration_days"] == 153

    def test_established_medication(self):
        """Medication authored >180 days ago should be 'established'."""
        med = _make_med_request(authored_on="2025-01-01")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "established"
        assert result["_duration_days"] == 396

    def test_boundary_new_to_recent(self):
        """At exactly 30 days, should be 'recent' (not 'new')."""
        med = _make_med_request(authored_on="2026-01-02")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "recent"
        assert result["_duration_days"] == 30

    def test_boundary_recent_to_established(self):
        """At exactly 180 days, should be 'recent' (<=180)."""
        med = _make_med_request(authored_on="2025-08-05")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "recent"
        assert result["_duration_days"] == 180

    def test_boundary_181_days_is_established(self):
        """At 181 days, should be 'established'."""
        med = _make_med_request(authored_on="2025-08-04")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "established"
        assert result["_duration_days"] == 181

    def test_missing_authored_on(self):
        """Should return empty dict if authoredOn is missing."""
        med = _make_med_request(authored_on=None)
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result == {}

    def test_unparseable_authored_on(self):
        """Should return empty dict if authoredOn can't be parsed."""
        med = _make_med_request(authored_on="not-a-date")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result == {}

    def test_datetime_format_authored_on(self):
        """Should handle full datetime format for authoredOn."""
        med = _make_med_request(authored_on="2026-01-20T10:30:00Z")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "new"
        assert result["_duration_days"] == 12

    def test_zero_day_duration(self):
        """Same-day medication should be 'new' with 0 duration."""
        med = _make_med_request(authored_on="2026-02-01")
        result = compute_medication_recency(med, date(2026, 2, 1))
        assert result["_recency"] == "new"
        assert result["_duration_days"] == 0


# =============================================================================
# Tests for helper functions: _extract_dosage_text, _extract_med_display
# =============================================================================


class TestExtractDosageText:
    """Tests for _extract_dosage_text()."""

    def test_structured_dose(self):
        med = _make_med_request(dose_value=20, dose_unit="MG")
        assert _extract_dosage_text(med) == "20 MG"

    def test_text_fallback(self):
        med = _make_med_request(dosage_text="Take 2 tablets daily")
        assert _extract_dosage_text(med) == "Take 2 tablets daily"

    def test_structured_preferred_over_text(self):
        med: dict = {
            "dosageInstruction": [
                {
                    "text": "fallback text",
                    "doseAndRate": [
                        {"doseQuantity": {"value": 10, "unit": "MG"}}
                    ],
                }
            ],
        }
        assert _extract_dosage_text(med) == "10 MG"

    def test_no_dosage_instruction(self):
        med: dict = {"resourceType": "MedicationRequest"}
        assert _extract_dosage_text(med) is None

    def test_empty_dosage_instruction(self):
        med: dict = {"dosageInstruction": []}
        assert _extract_dosage_text(med) is None


class TestExtractMedDisplay:
    """Tests for _extract_med_display()."""

    def test_extracts_display(self):
        med = _make_med_request(display="Metformin 500 MG")
        assert _extract_med_display(med) == "Metformin 500 MG"

    def test_no_medication_concept(self):
        med: dict = {"resourceType": "MedicationRequest"}
        assert _extract_med_display(med) is None

    def test_text_fallback(self):
        med: dict = {
            "medicationCodeableConcept": {
                "text": "Aspirin",
            },
        }
        assert _extract_med_display(med) == "Aspirin"


# =============================================================================
# Tests for compute_dose_history
# =============================================================================


class TestComputeDoseHistory:
    """Tests for compute_dose_history() with real DB."""

    @pytest.mark.asyncio
    async def test_returns_prior_records_with_different_dose(self, db_session: AsyncSession):
        """Should return prior MedicationRequests with different dosages."""
        patient_id = uuid.uuid4()

        # Prior med: stopped, different dose
        prior_med = _make_med_request(
            fhir_id="med-old",
            display="Lisinopril 10 MG",
            status="stopped",
            authored_on="2025-01-01",
            dose_value=5,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-old",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=prior_med,
        ))

        # Current active med: different dose
        active_med = _make_med_request(
            fhir_id="med-current",
            display="Lisinopril 10 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=10,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-current",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_id, active_med)

        assert len(result) == 1
        assert result[0]["dose"] == "5 MG"
        assert result[0]["authoredOn"] == "2025-01-01"
        assert result[0]["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_excludes_same_dose_refills(self, db_session: AsyncSession):
        """Same-dose refills should be excluded from dose history."""
        patient_id = uuid.uuid4()

        # Prior med: same dose, completed (refill)
        refill_med = _make_med_request(
            fhir_id="med-refill",
            display="Lisinopril 10 MG",
            status="completed",
            authored_on="2025-03-01",
            dose_value=10,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-refill",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=refill_med,
        ))

        active_med = _make_med_request(
            fhir_id="med-current",
            display="Lisinopril 10 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=10,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-current",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_id, active_med)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_empty_when_no_prior_records(self, db_session: AsyncSession):
        """Should return empty list when no prior records exist."""
        patient_id = uuid.uuid4()

        active_med = _make_med_request(
            fhir_id="med-only",
            display="Metformin 500 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=500,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-only",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_id, active_med)

        assert result == []

    @pytest.mark.asyncio
    async def test_chronological_order(self, db_session: AsyncSession):
        """Dose history should be in chronological (ascending) order."""
        patient_id = uuid.uuid4()

        # Two prior meds with different doses
        old_med = _make_med_request(
            fhir_id="med-old",
            display="Lisinopril 10 MG",
            status="stopped",
            authored_on="2024-01-01",
            dose_value=5,
            dose_unit="MG",
        )
        mid_med = _make_med_request(
            fhir_id="med-mid",
            display="Lisinopril 10 MG",
            status="stopped",
            authored_on="2024-06-01",
            dose_value=15,
            dose_unit="MG",
        )

        for med in [mid_med, old_med]:  # Insert out of order to test sorting
            db_session.add(FhirResource(
                fhir_id=med["id"],
                resource_type="MedicationRequest",
                patient_id=patient_id,
                data=med,
            ))

        active_med = _make_med_request(
            fhir_id="med-current",
            display="Lisinopril 10 MG",
            status="active",
            authored_on="2025-01-01",
            dose_value=20,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-current",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_id, active_med)

        assert len(result) == 2
        assert result[0]["dose"] == "5 MG"
        assert result[1]["dose"] == "15 MG"

    @pytest.mark.asyncio
    async def test_excludes_current_medication(self, db_session: AsyncSession):
        """The active medication itself should not appear in its dose history."""
        patient_id = uuid.uuid4()

        active_med = _make_med_request(
            fhir_id="med-current",
            display="Lisinopril 10 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=10,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-current",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_id, active_med)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_no_display_returns_empty(self, db_session: AsyncSession):
        """Should return empty list if medication has no display name."""
        patient_id = uuid.uuid4()

        med: dict = {
            "resourceType": "MedicationRequest",
            "id": "med-no-display",
            "status": "active",
            "medicationCodeableConcept": {"coding": [{}]},
        }

        result = await compute_dose_history(db_session, patient_id, med)

        assert result == []

    @pytest.mark.asyncio
    async def test_string_patient_id(self, db_session: AsyncSession):
        """Should accept patient_id as a string."""
        patient_id = uuid.uuid4()

        prior_med = _make_med_request(
            fhir_id="med-old",
            display="Metformin 500 MG",
            status="stopped",
            authored_on="2025-01-01",
            dose_value=250,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-old",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=prior_med,
        ))

        active_med = _make_med_request(
            fhir_id="med-current",
            display="Metformin 500 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=500,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-current",
            resource_type="MedicationRequest",
            patient_id=patient_id,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, str(patient_id), active_med)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_patient_isolation(self, db_session: AsyncSession):
        """Dose history should not leak across patients."""
        patient_a = uuid.uuid4()
        patient_b = uuid.uuid4()

        # Patient B has a prior med with different dose
        prior_b = _make_med_request(
            fhir_id="med-b-old",
            display="Lisinopril 10 MG",
            status="stopped",
            authored_on="2025-01-01",
            dose_value=5,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-b-old",
            resource_type="MedicationRequest",
            patient_id=patient_b,
            data=prior_b,
        ))

        active_med = _make_med_request(
            fhir_id="med-a-current",
            display="Lisinopril 10 MG",
            status="active",
            authored_on="2025-06-01",
            dose_value=10,
            dose_unit="MG",
        )
        db_session.add(FhirResource(
            fhir_id="med-a-current",
            resource_type="MedicationRequest",
            patient_id=patient_a,
            data=active_med,
        ))
        await db_session.flush()

        result = await compute_dose_history(db_session, patient_a, active_med)

        assert result == []


# =============================================================================
# Tests for infer_medication_condition_links
# =============================================================================


class TestInferMedicationConditionLinks:
    """Tests for infer_medication_condition_links() with mocked graph."""

    @pytest.mark.asyncio
    async def test_infers_link_via_encounter(self):
        """Should infer med->condition link via PRESCRIBED->encounter->DIAGNOSED->condition."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-1", display="Lisinopril 10 MG")

        mock_graph = AsyncMock(spec=KnowledgeGraph)

        # First call: get_all_connections for med-1 -> returns PRESCRIBED encounter
        # Second call: get_all_connections for enc-1 -> returns DIAGNOSED condition
        mock_graph.get_all_connections.side_effect = [
            # Connections from med-1
            [
                {
                    "relationship": "PRESCRIBED",
                    "direction": "incoming",
                    "fhir_id": "enc-1",
                    "resource_type": "Encounter",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            # Connections from enc-1
            [
                {
                    "relationship": "DIAGNOSED",
                    "direction": "outgoing",
                    "fhir_id": "cond-1",
                    "resource_type": "Condition",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
        ]

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "cond-1" in result
        assert len(result["cond-1"]) == 1
        assert result["cond-1"][0]["_inferred"] is True
        assert result["cond-1"][0]["id"] == "med-1"
        assert "unlinked" not in result

    @pytest.mark.asyncio
    async def test_unlinked_when_no_encounter(self):
        """Meds with no PRESCRIBED encounter should go to 'unlinked' bucket."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-orphan", display="Orphan Drug")

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = [
            # No PRESCRIBED relationships
            {
                "relationship": "TREATS",
                "direction": "outgoing",
                "fhir_id": "cond-99",
                "resource_type": "Condition",
                "name": None,
                "fhir_resource": None,
            },
        ]

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "unlinked" in result
        assert len(result["unlinked"]) == 1
        assert result["unlinked"][0]["id"] == "med-orphan"

    @pytest.mark.asyncio
    async def test_unlinked_when_encounter_has_no_conditions(self):
        """Meds with encounters but no DIAGNOSED conditions should go to 'unlinked'."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-no-diag", display="Generic Med")

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.side_effect = [
            # Med -> encounter via PRESCRIBED
            [
                {
                    "relationship": "PRESCRIBED",
                    "direction": "incoming",
                    "fhir_id": "enc-empty",
                    "resource_type": "Encounter",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            # Encounter has no DIAGNOSED conditions
            [
                {
                    "relationship": "RECORDED",
                    "direction": "outgoing",
                    "fhir_id": "obs-1",
                    "resource_type": "Observation",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
        ]

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "unlinked" in result
        assert len(result["unlinked"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_conditions_from_one_encounter(self):
        """One encounter can diagnose multiple conditions linked to the same med."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-multi", display="Multi Drug")

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.side_effect = [
            # Med connections
            [
                {
                    "relationship": "PRESCRIBED",
                    "direction": "incoming",
                    "fhir_id": "enc-1",
                    "resource_type": "Encounter",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            # Encounter with two diagnosed conditions
            [
                {
                    "relationship": "DIAGNOSED",
                    "direction": "outgoing",
                    "fhir_id": "cond-a",
                    "resource_type": "Condition",
                    "name": None,
                    "fhir_resource": None,
                },
                {
                    "relationship": "DIAGNOSED",
                    "direction": "outgoing",
                    "fhir_id": "cond-b",
                    "resource_type": "Condition",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
        ]

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "cond-a" in result
        assert "cond-b" in result
        assert len(result["cond-a"]) == 1
        assert len(result["cond-b"]) == 1
        assert all(m["_inferred"] is True for m in result["cond-a"])

    @pytest.mark.asyncio
    async def test_med_without_id_goes_to_unlinked(self):
        """A med dict missing 'id' should go to unlinked."""
        patient_id = str(uuid.uuid4())
        med: dict = {"resourceType": "MedicationRequest", "status": "active"}

        mock_graph = AsyncMock(spec=KnowledgeGraph)

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "unlinked" in result
        assert len(result["unlinked"]) == 1
        # Graph should not have been called
        mock_graph.get_all_connections.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_mutate_input(self):
        """Original med dicts should not be mutated."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-1", display="Test Med")
        original = copy.deepcopy(med)

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.side_effect = [
            [
                {
                    "relationship": "PRESCRIBED",
                    "direction": "incoming",
                    "fhir_id": "enc-1",
                    "resource_type": "Encounter",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            [
                {
                    "relationship": "DIAGNOSED",
                    "direction": "outgoing",
                    "fhir_id": "cond-1",
                    "resource_type": "Condition",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
        ]

        await infer_medication_condition_links([med], mock_graph, patient_id)

        # Original should not have _inferred
        assert "_inferred" not in med
        assert med == original

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self):
        """Empty unlinked_meds list should return empty dict."""
        patient_id = str(uuid.uuid4())
        mock_graph = AsyncMock(spec=KnowledgeGraph)

        result = await infer_medication_condition_links([], mock_graph, patient_id)

        assert result == {}
        mock_graph.get_all_connections.assert_not_called()

    @pytest.mark.asyncio
    async def test_mixed_linked_and_unlinked(self):
        """Should properly separate meds with/without encounter links."""
        patient_id = str(uuid.uuid4())
        med_linked = _make_med_request(fhir_id="med-linked", display="Drug A")
        med_unlinked = _make_med_request(fhir_id="med-unlinked", display="Drug B")

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.side_effect = [
            # med-linked -> has PRESCRIBED encounter
            [
                {
                    "relationship": "PRESCRIBED",
                    "direction": "incoming",
                    "fhir_id": "enc-1",
                    "resource_type": "Encounter",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            # enc-1 -> has DIAGNOSED condition
            [
                {
                    "relationship": "DIAGNOSED",
                    "direction": "outgoing",
                    "fhir_id": "cond-1",
                    "resource_type": "Condition",
                    "name": None,
                    "fhir_resource": None,
                },
            ],
            # med-unlinked -> no PRESCRIBED encounters
            [],
        ]

        result = await infer_medication_condition_links(
            [med_linked, med_unlinked], mock_graph, patient_id
        )

        assert "cond-1" in result
        assert result["cond-1"][0]["_inferred"] is True
        assert "unlinked" in result
        assert result["unlinked"][0]["id"] == "med-unlinked"

    @pytest.mark.asyncio
    async def test_no_connections_at_all(self):
        """Med with zero graph connections goes to unlinked."""
        patient_id = str(uuid.uuid4())
        med = _make_med_request(fhir_id="med-isolated", display="Isolated Drug")

        mock_graph = AsyncMock(spec=KnowledgeGraph)
        mock_graph.get_all_connections.return_value = []

        result = await infer_medication_condition_links([med], mock_graph, patient_id)

        assert "unlinked" in result
        assert len(result["unlinked"]) == 1
