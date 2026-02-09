# Brainstorm: Lab Reference Ranges Lookup Table

**Date**: 2026-02-08
**Status**: Ready for planning

## Problem Statement

CruxMD has 832 Observations across 5 Synthea patient bundles with 40 unique LOINC codes (17 laboratory, 9 vital-signs, 10 survey, 2 social-history, 2 procedure). None include `referenceRange` or `interpretation` fields. The frontend already has HL7 interpretation code UI (N/H/L/HH/LL with color-coded badges, sparklines, range bars) but consumes hardcoded demo data. There is no backend source of truth for reference ranges or interpretation logic.

## Proposed Solution

Build a Python constants-based reference range lookup table (`backend/app/services/reference_ranges.py`) covering ~100-150 common LOINC codes across standard lab panels. Compute HL7 interpretation codes both at seed time (baked into FHIR JSON) and at runtime (for new/dynamic data).

## Key Decisions

- **Storage**: Python constants in a backend module (not DB table, not inline in fixtures)
- **Interpretation assignment**: Both seed-time (pre-baked into FHIR JSON) and runtime lookup
- **Scope**: ~100-150 LOINCs covering common panels (CBC, BMP, CMP, lipid, A1c, thyroid, liver, renal, urinalysis, coag) — not just the 40 fixture LOINCs
- **Demographics**: Sex-based ranges where clinically relevant (hemoglobin, creatinine, iron, etc.) with a default fallback
- **Critical ranges**: Explicit per-LOINC critical values (HH/LL), not formula-derived
- **Metadata**: Panel grouping included in the lookup (CBC, BMP, etc.); display name and unit come from FHIR data itself
- **Structure**: Flat dict keyed by LOINC code (Approach A)
- **Data sourcing**: LLM-assisted population from established clinical references (Medscape, MCC, Cleveland Clinic, StatPearls), with manual spot-checking of fixture LOINCs. No official LOINC reference range database exists — ranges are lab-specific by design.
- **Units**: US conventional units (mg/dL, g/dL, 10*3/uL, etc.) to match Synthea fixture data

## Data Structure

```python
REFERENCE_RANGES: dict[str, dict] = {
    "718-7": {  # Hemoglobin
        "panel": "CBC",
        "ranges": {
            "default": {"low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "male":    {"low": 13.5, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "female":  {"low": 12.0, "high": 16.0, "critical_low": 7.0, "critical_high": 20.0},
        }
    },
    # ...
}
```

### Interpretation Logic

```
value < critical_low  → "LL" (Critically Low)
value < low           → "L"  (Low)
value > critical_high → "HH" (Critically High)
value > high          → "H"  (High)
otherwise             → "N"  (Normal)
```

Sex-aware fallback: use sex-specific range if patient sex matches ("male"/"female"), else use "default".

## Scope

### In Scope
- Reference range lookup table with ~100-150 LOINCs across standard panels
- Sex-based ranges for clinically relevant tests
- Explicit critical values (HH/LL) per LOINC
- Panel grouping metadata (CBC, BMP, Lipid Panel, etc.)
- Interpretation computation function (value + range → N/H/L/HH/LL)
- Seed-time enrichment: add `referenceRange` and `interpretation` to fixture Observations during `make seed`
- Runtime lookup: compute interpretation on-the-fly for API responses
- Helper to get interpretation given LOINC code, value, and patient sex

### Out of Scope
- Age-based range stratification (pediatric/geriatric)
- Database storage of reference ranges
- Custom/user-defined reference ranges
- Display name overrides (use FHIR display names)
- Unit conversion (assume consistent units per LOINC)

## Fixture Data Summary

40 unique LOINCs across 5 patients, 832 total Observations:

| Category | LOINCs | Examples |
|----------|--------|---------|
| laboratory | 17 | Hemoglobin, WBC, Platelets, Cholesterol, Triglycerides, Hematocrit, MCH, MCHC, MCV, RDW, RBC, LDL, HDL |
| vital-signs | 9 | BP, HR, RR, Temp, Weight, Height, BMI, Pain, BMI percentile |
| survey | 10 | PHQ-2, PHQ-9, GAD-7, AUDIT-C, HARK, DAST-10, Morse Fall Scale, PRAPARE |
| social-history | 2 | Tobacco status, Pregnancy status |
| procedure | 2 | FEV1/FVC, Polyp size |

Notes:
- Units already present in `valueQuantity.unit`
- No panel groupings in Synthea data (no `hasMember`)
- Categories provide coarse grouping but not clinical panel membership

## Open Questions
- Should vital signs also get reference ranges (e.g., BP 90/60-120/80, HR 60-100) or just laboratory tests?
- How to handle component-based observations like blood pressure (85354-9 is a panel with systolic/diastolic components)?
- Should survey scores get interpretation codes (e.g., PHQ-9 >= 10 is "moderate depression")?

## Constraints
- Must conform to HL7 FHIR interpretation code system: N, H, L, HH, LL
- Reference ranges must be clinically reasonable (use standard clinical chemistry references)
- Python constants only — no DB migration
- Must not break existing embedding templates or FHIR pruner

## Risks
- **Clinical accuracy**: Reference ranges vary by lab/method. Mitigation: use widely-accepted textbook ranges, document sources.
- **Maintenance burden**: 100-150 entries is manageable but non-trivial. Mitigation: panel grouping helps organize; well-structured dict is easy to extend.
- **Sex determination**: Synthea patients have `gender` field but it maps to administrative gender, not biological sex. Mitigation: use administrative gender as proxy (standard practice for Synthea data).
