---
title: "feat: Lab Reference Ranges Lookup Table"
type: feat
date: 2026-02-08
---

# feat: Lab Reference Ranges Lookup Table

## Overview

Build a Python constants-based reference range lookup table for clinical lab results with HL7 FHIR interpretation code computation (N/H/L/HH/LL). Covers ~100-150 common LOINC codes across standard panels (CBC, BMP, CMP, lipid, A1c, thyroid, liver, renal, urinalysis, coag). Enriches FHIR Observations at seed time and provides runtime interpretation for dynamic data.

## Problem Statement

CruxMD has 832 Observations across 5 Synthea patient bundles. None include `referenceRange` or `interpretation` fields. The frontend already renders HL7 interpretation badges, sparklines, and range bars — but with hardcoded demo data. The LLM agent formats observations into a markdown table with a "Ref Range" column that is always empty. There is no backend source of truth for what's normal vs abnormal.

## Proposed Solution

### New Module: `backend/app/services/reference_ranges.py`

Single flat dict keyed by LOINC code with sex-aware ranges and panel grouping:

```python
from typing import Literal

HL7Interpretation = Literal["N", "H", "L", "HH", "LL"]

REFERENCE_RANGES: dict[str, dict] = {
    "718-7": {  # Hemoglobin
        "panel": "CBC",
        "ranges": {
            "default": {"low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "male":    {"low": 13.5, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "female":  {"low": 12.0, "high": 16.0, "critical_low": 7.0, "critical_high": 20.0},
        },
    },
    "6690-2": {  # WBC
        "panel": "CBC",
        "ranges": {
            "default": {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0},
        },
    },
    # ... ~100-150 entries
}
```

### Helper Functions

```python
def get_reference_range(
    loinc_code: str,
    patient_sex: str | None = None,
) -> dict | None:
    """Return {low, high, critical_low, critical_high} for a LOINC code.

    Sex-aware fallback: tries patient_sex key first, then "default".
    Returns None if LOINC not in table.
    """

def compute_interpretation(
    value: float,
    reference_range: dict,
) -> HL7Interpretation:
    """Compute HL7 interpretation from value and range.

    Boundary semantics (exclusive):
      value < critical_low  → "LL"
      value < low           → "L"
      value > critical_high → "HH"
      value > high          → "H"
      otherwise             → "N"
    """

def interpret_observation(
    observation: dict,
    patient_sex: str | None = None,
) -> tuple[HL7Interpretation | None, dict | None]:
    """Interpret a FHIR Observation resource.

    Returns (interpretation_code, reference_range_dict) or (None, None)
    if LOINC not in table or no numeric value.
    """
```

### Seed-Time Enrichment

In `fhir_loader.py`, after `_clean_patient_names()` and before storing:

```python
if resource.get("resourceType") == "Observation":
    patient_sex = _extract_patient_sex(entries)  # from Patient resource in bundle
    interp, ref_range = interpret_observation(resource, patient_sex)
    if interp:
        resource["interpretation"] = [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": interp,
                "display": _INTERPRETATION_DISPLAY[interp],
            }]
        }]
        resource["referenceRange"] = [{
            "low": {"value": ref_range["low"], "unit": _get_obs_unit(resource)},
            "high": {"value": ref_range["high"], "unit": _get_obs_unit(resource)},
        }]
```

This conforms to FHIR R4 Observation structure so the agent pruner, embeddings, and API all work automatically.

### Runtime Interpretation

In the compiler's `prune_and_enrich()` path, if an Observation lacks `interpretation`, compute on-the-fly:

```python
if resource_type == "Observation" and "interpretation" not in resource.get("data", {}):
    interp, ref_range = interpret_observation(resource["data"], patient_sex)
    if interp:
        enrichment["_interpretation"] = interp
        enrichment["_reference_range"] = f"{ref_range['low']}-{ref_range['high']}"
```

## Technical Considerations

### Scope Boundaries

**In scope (interpret):**
- Laboratory category observations (17 fixture LOINCs + ~80-130 common panel LOINCs)
- Simple vital signs with adult ranges: HR (8867-4), RR (9279-1), Temp (8310-5)
- Blood pressure components: Systolic (8480-6), Diastolic (8462-4) — NOT the panel (85354-9)

**Out of scope (skip):**
- Survey scores (PHQ-9, GAD-7, etc.) — different semantics, not lab ranges
- Social history (tobacco, pregnancy) — qualitative, no numeric interpretation
- Procedure observations (FEV1/FVC, polyp size) — specialist context needed
- BMI, height, weight — not clinically "abnormal" in range sense
- BP panel observation (85354-9) — component-based, interpret components instead
- Age-based stratification, unit conversion, manual overrides

### Edge Case Handling

| Edge Case | Behavior |
|-----------|----------|
| LOINC not in lookup table | Skip — no interpretation field added |
| No `valueQuantity` (qualitative) | Skip — no numeric value to interpret |
| Value at range boundary | Normal (exclusive boundaries: `>` and `<`) |
| Gender unknown/other | Use "default" range; skip if no default exists |
| Component observation (BP panel) | Skip panel, interpret individual components |
| Observation with mismatched unit | Skip — no unit normalization |

### Pruner Interaction

The FHIR pruner in `agent.py` will:
- **Preserve** `referenceRange` (contains `value`/`unit`, no stripped keys)
- **Simplify** `interpretation` CodeableConcept to display string (e.g., "High")
- The agent's observation table already has a "Ref Range" column that reads `referenceRange[0].low.value` - `referenceRange[0].high.value`
- No pruner changes needed

### Backfill Strategy

No separate migration needed. `make seed` re-ingests all fixture bundles through `fhir_loader.py`. After implementing seed-time enrichment, running `make seed` backfills all existing Observations.

## Acceptance Criteria

- [ ] `reference_ranges.py` module with REFERENCE_RANGES dict covering all 17 fixture lab LOINCs + common panel LOINCs (~100-150 total)
- [ ] Sex-based ranges for clinically relevant tests (hemoglobin, creatinine, RBC, hematocrit at minimum)
- [ ] Explicit critical values (HH/LL thresholds) for all entries
- [ ] Panel grouping metadata (CBC, BMP, CMP, Lipid, Thyroid, Liver, Renal, Coag, etc.)
- [ ] `get_reference_range()` function with sex-aware fallback
- [ ] `compute_interpretation()` function returning N/H/L/HH/LL
- [ ] `interpret_observation()` convenience function for FHIR Observations
- [ ] Seed-time enrichment in `fhir_loader.py` — adds FHIR-conformant `interpretation` and `referenceRange` to Observations
- [ ] Runtime interpretation fallback in compiler enrichment path
- [ ] `make seed` produces Observations with populated `interpretation` and `referenceRange` fields
- [ ] Agent's observation markdown table shows populated "Ref Range" column
- [ ] Unit tests for interpretation logic (boundary cases, sex fallback, missing LOINC)
- [ ] Unit tests for seed-time enrichment
- [ ] All existing tests continue to pass

## Success Metrics

- 100% of fixture lab Observations have interpretation codes after `make seed`
- Agent observation tables show reference ranges for all lab results
- Frontend can consume real interpretation data instead of hardcoded demo values

## Dependencies & Risks

**Dependencies:**
- None — new module, no external packages needed

**Risks:**
- **Clinical accuracy**: Reference ranges vary by lab. Mitigation: use widely-accepted textbook ranges from Medscape, MCC, Cleveland Clinic; document that these are demo-grade, not clinical-grade.
- **LLM-assisted data population**: Range values generated by LLM need spot-checking. Mitigation: verify all 17 fixture LOINCs manually against published references.

## Implementation Phases

### Phase 1: Lookup Table & Helpers
- Create `reference_ranges.py` with REFERENCE_RANGES dict
- Populate ~100-150 LOINC entries with ranges, critical values, panel grouping
- Implement `get_reference_range()`, `compute_interpretation()`, `interpret_observation()`
- Unit tests for all helper functions

### Phase 2: Seed-Time Enrichment
- Modify `fhir_loader.py` to enrich Observations during bundle loading
- Extract patient sex from Patient resource in bundle
- Add FHIR-conformant `interpretation` and `referenceRange` to Observation resources
- Unit tests for enrichment logic
- Verify with `make seed` + spot-check database

### Phase 3: Runtime Interpretation
- Add fallback interpretation in compiler enrichment path
- Ensure observations without stored interpretation get computed on-the-fly
- Integration test: observation without stored interpretation gets runtime interpretation

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/services/reference_ranges.py` | **NEW** — lookup table + helper functions |
| `backend/app/services/fhir_loader.py` | Add seed-time enrichment for Observations |
| `backend/app/services/compiler.py` | Add runtime interpretation fallback in enrichment |
| `backend/tests/test_reference_ranges.py` | **NEW** — unit tests for lookup + interpretation |
| `backend/tests/test_fhir_loader.py` | Add tests for seed-time enrichment |

## Files NOT Modified

| File | Why |
|------|-----|
| `backend/app/services/agent.py` | Pruner already handles these fields correctly |
| `backend/app/routes/data.py` | Returns raw JSONB — enriched data flows through automatically |
| `backend/app/services/embeddings.py` | Optional enhancement — defer to follow-up |
| `backend/app/models.py` | No schema changes — JSONB stores everything |
| Frontend | Already has HL7 UI — will consume real data once connected |

## References

- Brainstorm: `docs/brainstorms/2026-02-08-lab-reference-ranges-brainstorm.md`
- HL7 Interpretation Codes: `http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation`
- FHIR R4 Observation: `https://hl7.org/fhir/R4/observation.html`
- Clinical references: Medscape Lab Values, MCC Normal Lab Values, Cleveland Clinic CBC Reference Ranges
- Frontend design: `frontend/app/design/components/table/page.tsx` (HL7 badge/sparkline implementation)
