"""Tests for reference range lookup and HL7 interpretation logic."""

import pytest

from app.services.reference_ranges import (
    REFERENCE_RANGES,
    HL7Interpretation,
    _INTERPRETATION_DISPLAY,
    build_fhir_interpretation,
    build_fhir_reference_range,
    compute_interpretation,
    get_panel,
    get_reference_range,
    interpret_observation,
)


# -----------------------------------------------------------------------
# Fixture LOINCs that MUST be present
# -----------------------------------------------------------------------

FIXTURE_LAB_LOINCS = frozenset(
    [
        "718-7",  # Hemoglobin
        "6690-2",  # WBC
        "789-8",  # RBC
        "777-3",  # Platelets
        "4544-3",  # Hematocrit (automated)
        "20570-8",  # Hematocrit (calculated)
        "785-6",  # MCH
        "786-4",  # MCHC
        "787-2",  # MCV
        "788-0",  # RDW
        "32207-3",  # Platelet distribution width
        "32623-1",  # MPV
        "2093-3",  # Total Cholesterol
        "2085-9",  # HDL
        "18262-6",  # LDL
        "2571-8",  # Triglycerides
        "57905-2",  # Stool hemoglobin
    ]
)

VITAL_SIGN_LOINCS = frozenset(
    [
        "8867-4",  # Heart rate
        "9279-1",  # Respiratory rate
        "8310-5",  # Body temperature
        "8480-6",  # Systolic BP
        "8462-4",  # Diastolic BP
    ]
)


class TestReferenceRangesData:
    """Validate the REFERENCE_RANGES dict structure and coverage."""

    def test_minimum_count(self):
        assert len(REFERENCE_RANGES) >= 100

    def test_fixture_lab_loincs_present(self):
        missing = FIXTURE_LAB_LOINCS - set(REFERENCE_RANGES.keys())
        assert not missing, f"Missing fixture LOINCs: {missing}"

    def test_vital_sign_loincs_present(self):
        missing = VITAL_SIGN_LOINCS - set(REFERENCE_RANGES.keys())
        assert not missing, f"Missing vital sign LOINCs: {missing}"

    def test_all_entries_have_panel(self):
        for loinc, entry in REFERENCE_RANGES.items():
            assert "panel" in entry, f"{loinc} missing 'panel'"
            assert isinstance(entry["panel"], str) and entry["panel"]

    def test_all_entries_have_default_range(self):
        for loinc, entry in REFERENCE_RANGES.items():
            assert "ranges" in entry, f"{loinc} missing 'ranges'"
            assert "default" in entry["ranges"], f"{loinc} missing 'default' range"

    def test_range_ordering(self):
        """critical_low <= low < high <= critical_high for all ranges."""
        for loinc, entry in REFERENCE_RANGES.items():
            for sex, r in entry["ranges"].items():
                assert r["critical_low"] <= r["low"], (
                    f"{loinc} ({sex}): critical_low {r['critical_low']} > low {r['low']}"
                )
                assert r["low"] < r["high"], (
                    f"{loinc} ({sex}): low {r['low']} >= high {r['high']}"
                )
                assert r["high"] <= r["critical_high"], (
                    f"{loinc} ({sex}): high {r['high']} > critical_high {r['critical_high']}"
                )

    def test_range_keys_complete(self):
        """Every range dict has all four required keys."""
        required = {"low", "high", "critical_low", "critical_high"}
        for loinc, entry in REFERENCE_RANGES.items():
            for sex, r in entry["ranges"].items():
                assert set(r.keys()) == required, (
                    f"{loinc} ({sex}): unexpected keys {set(r.keys())}"
                )

    def test_sex_specific_ranges_exist(self):
        """At least some entries have sex-specific ranges."""
        sex_entries = [
            loinc
            for loinc, e in REFERENCE_RANGES.items()
            if "male" in e["ranges"] or "female" in e["ranges"]
        ]
        assert len(sex_entries) >= 5, "Expected at least 5 sex-specific entries"

    def test_hemoglobin_sex_specific(self):
        """Hemoglobin must have male/female ranges."""
        hgb = REFERENCE_RANGES["718-7"]
        assert "male" in hgb["ranges"]
        assert "female" in hgb["ranges"]
        assert hgb["ranges"]["male"]["low"] > hgb["ranges"]["female"]["low"]

    def test_known_panel_groupings(self):
        """Spot-check known panel groupings."""
        assert REFERENCE_RANGES["718-7"]["panel"] == "CBC"
        assert REFERENCE_RANGES["2345-7"]["panel"] == "BMP"
        assert REFERENCE_RANGES["2093-3"]["panel"] == "Lipid Panel"
        assert REFERENCE_RANGES["3016-3"]["panel"] == "Thyroid"

    def test_spot_check_hemoglobin_range(self):
        """Verify hemoglobin ranges against published values."""
        hgb = REFERENCE_RANGES["718-7"]
        male = hgb["ranges"]["male"]
        female = hgb["ranges"]["female"]
        # Male: 13.5-17.5 g/dL (Medscape, MCC)
        assert 13.0 <= male["low"] <= 14.0
        assert 17.0 <= male["high"] <= 18.0
        # Female: 12.0-16.0 g/dL
        assert 11.5 <= female["low"] <= 12.5
        assert 15.5 <= female["high"] <= 16.5

    def test_spot_check_wbc_range(self):
        """Verify WBC ranges against published values."""
        wbc = REFERENCE_RANGES["6690-2"]["ranges"]["default"]
        # WBC: 4.5-11.0 × 10³/µL
        assert 4.0 <= wbc["low"] <= 5.0
        assert 10.5 <= wbc["high"] <= 11.5

    def test_spot_check_glucose_range(self):
        """Verify glucose ranges against published values."""
        gluc = REFERENCE_RANGES["2345-7"]["ranges"]["default"]
        # Fasting glucose: 70-100 mg/dL
        assert 65 <= gluc["low"] <= 75
        assert 95 <= gluc["high"] <= 105


class TestGetReferenceRange:
    """Test the get_reference_range() function."""

    def test_known_loinc_returns_range(self):
        result = get_reference_range("718-7")
        assert result is not None
        assert "low" in result and "high" in result

    def test_unknown_loinc_returns_none(self):
        assert get_reference_range("99999-9") is None

    def test_male_gets_male_range(self):
        result = get_reference_range("718-7", "male")
        assert result["low"] == 13.5  # Male-specific

    def test_female_gets_female_range(self):
        result = get_reference_range("718-7", "female")
        assert result["low"] == 12.0  # Female-specific

    def test_unknown_sex_gets_default(self):
        result = get_reference_range("718-7", None)
        default = REFERENCE_RANGES["718-7"]["ranges"]["default"]
        assert result == default

    def test_other_sex_gets_default(self):
        result = get_reference_range("718-7", "other")
        default = REFERENCE_RANGES["718-7"]["ranges"]["default"]
        assert result == default

    def test_sex_on_non_sex_specific_gets_default(self):
        """WBC has no sex-specific ranges — always returns default."""
        result = get_reference_range("6690-2", "male")
        default = REFERENCE_RANGES["6690-2"]["ranges"]["default"]
        assert result == default


class TestGetPanel:
    """Test the get_panel() function."""

    def test_known_loinc(self):
        assert get_panel("718-7") == "CBC"

    def test_unknown_loinc(self):
        assert get_panel("99999-9") is None


class TestComputeInterpretation:
    """Test the compute_interpretation() function."""

    @pytest.fixture()
    def wbc_range(self):
        return {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0}

    def test_normal(self, wbc_range):
        assert compute_interpretation(7.5, wbc_range) == "N"

    def test_high(self, wbc_range):
        assert compute_interpretation(12.0, wbc_range) == "H"

    def test_low(self, wbc_range):
        assert compute_interpretation(3.0, wbc_range) == "L"

    def test_critically_high(self, wbc_range):
        assert compute_interpretation(35.0, wbc_range) == "HH"

    def test_critically_low(self, wbc_range):
        assert compute_interpretation(1.5, wbc_range) == "LL"

    def test_at_high_boundary_is_normal(self, wbc_range):
        """Value exactly at high boundary -> Normal (exclusive)."""
        assert compute_interpretation(11.0, wbc_range) == "N"

    def test_at_low_boundary_is_normal(self, wbc_range):
        """Value exactly at low boundary -> Normal (exclusive)."""
        assert compute_interpretation(4.5, wbc_range) == "N"

    def test_just_above_high(self, wbc_range):
        assert compute_interpretation(11.01, wbc_range) == "H"

    def test_just_below_low(self, wbc_range):
        assert compute_interpretation(4.49, wbc_range) == "L"

    def test_at_critical_high_boundary_is_high(self, wbc_range):
        """Value exactly at critical_high -> High (not Critical High)."""
        assert compute_interpretation(30.0, wbc_range) == "H"

    def test_at_critical_low_boundary_is_low(self, wbc_range):
        """Value exactly at critical_low -> Low (not Critical Low)."""
        assert compute_interpretation(2.0, wbc_range) == "L"

    def test_just_above_critical_high(self, wbc_range):
        assert compute_interpretation(30.01, wbc_range) == "HH"

    def test_just_below_critical_low(self, wbc_range):
        assert compute_interpretation(1.99, wbc_range) == "LL"

    def test_negative_value(self):
        """Negative values (e.g., base excess) should work."""
        ref = {"low": -2.0, "high": 2.0, "critical_low": -10.0, "critical_high": 10.0}
        assert compute_interpretation(-1.5, ref) == "N"
        assert compute_interpretation(-5.0, ref) == "L"
        assert compute_interpretation(5.0, ref) == "H"
        assert compute_interpretation(-11.0, ref) == "LL"

    def test_zero_low_boundary(self):
        """Tests with low=0 (e.g., troponin)."""
        ref = {"low": 0.0, "high": 0.04, "critical_low": 0.0, "critical_high": 2.0}
        assert compute_interpretation(0.02, ref) == "N"
        assert compute_interpretation(0.05, ref) == "H"
        assert compute_interpretation(0.0, ref) == "N"


class TestInterpretObservation:
    """Test the interpret_observation() convenience function."""

    def _make_obs(self, loinc: str, value: float, unit: str = "g/dL") -> dict:
        return {
            "code": {"coding": [{"code": loinc, "display": "Test"}]},
            "valueQuantity": {"value": value, "unit": unit},
        }

    def test_normal_observation(self):
        obs = self._make_obs("718-7", 14.5)
        interp, ref = interpret_observation(obs, "male")
        assert interp == "N"
        assert ref is not None
        assert ref["low"] == 13.5

    def test_high_observation(self):
        obs = self._make_obs("718-7", 18.0)
        interp, ref = interpret_observation(obs, "male")
        assert interp == "H"

    def test_low_observation_female(self):
        obs = self._make_obs("718-7", 11.5)
        interp, ref = interpret_observation(obs, "female")
        assert interp == "L"
        assert ref["low"] == 12.0  # Female range

    def test_no_value_quantity(self):
        obs = {
            "code": {"coding": [{"code": "718-7"}]},
        }
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_value_codeable_concept(self):
        obs = {
            "code": {"coding": [{"code": "72166-2", "display": "Tobacco smoking status"}]},
            "valueCodeableConcept": {
                "coding": [{"display": "Never smoker"}]
            },
        }
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_unknown_loinc(self):
        obs = self._make_obs("99999-9", 5.0)
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_no_coding(self):
        obs = {"code": {}, "valueQuantity": {"value": 5.0}}
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_empty_coding(self):
        obs = {"code": {"coding": []}, "valueQuantity": {"value": 5.0}}
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_non_numeric_value(self):
        obs = {
            "code": {"coding": [{"code": "718-7"}]},
            "valueQuantity": {"value": "high", "unit": "g/dL"},
        }
        interp, ref = interpret_observation(obs)
        assert interp is None
        assert ref is None

    def test_none_sex_uses_default(self):
        obs = self._make_obs("718-7", 14.5)
        interp, ref = interpret_observation(obs, None)
        assert interp == "N"
        default = REFERENCE_RANGES["718-7"]["ranges"]["default"]
        assert ref == default


class TestBuildFhirInterpretation:
    """Test FHIR interpretation builder."""

    def test_structure(self):
        result = build_fhir_interpretation("H")
        assert isinstance(result, list)
        assert len(result) == 1
        coding = result[0]["coding"][0]
        assert coding["code"] == "H"
        assert coding["display"] == "High"
        assert "system" in coding

    def test_all_codes(self):
        for code, display in _INTERPRETATION_DISPLAY.items():
            result = build_fhir_interpretation(code)
            assert result[0]["coding"][0]["code"] == code
            assert result[0]["coding"][0]["display"] == display


class TestBuildFhirReferenceRange:
    """Test FHIR reference range builder."""

    def test_with_unit(self):
        ref = {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0}
        result = build_fhir_reference_range(ref, "10*3/uL")
        assert len(result) == 1
        assert result[0]["low"]["value"] == 4.5
        assert result[0]["high"]["value"] == 11.0
        assert result[0]["low"]["unit"] == "10*3/uL"

    def test_without_unit(self):
        ref = {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0}
        result = build_fhir_reference_range(ref)
        assert "unit" not in result[0]["low"]
        assert "unit" not in result[0]["high"]
