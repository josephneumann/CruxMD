"""Laboratory reference ranges and HL7 FHIR interpretation code computation.

Provides a lookup table of ~120 common LOINC codes with reference ranges,
sex-aware variants, critical thresholds, and panel grouping. Computes HL7
interpretation codes (N/H/L/HH/LL) from observed values.

Reference values are demo-grade, sourced from standard clinical chemistry
references (Medscape, MCC, Cleveland Clinic, StatPearls). Not for clinical use.
"""

from __future__ import annotations

from typing import Literal

HL7Interpretation = Literal["N", "H", "L", "HH", "LL"]

_INTERPRETATION_DISPLAY: dict[HL7Interpretation, str] = {
    "N": "Normal",
    "H": "High",
    "L": "Low",
    "HH": "Critical high",
    "LL": "Critical low",
}

# ---------------------------------------------------------------------------
# Reference range lookup table
#
# Structure:
#   LOINC code -> {
#       "panel": str,           # Clinical panel grouping
#       "ranges": {
#           "default": {low, high, critical_low, critical_high},
#           "male":    {low, high, critical_low, critical_high},  # optional
#           "female":  {low, high, critical_low, critical_high},  # optional
#       }
#   }
#
# All values in US conventional units matching Synthea fixture data.
# Boundary semantics: exclusive (value > high = H, value < low = L).
# ---------------------------------------------------------------------------

REFERENCE_RANGES: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # CBC (Complete Blood Count)
    # -----------------------------------------------------------------------
    "6690-2": {  # Leukocytes (WBC) [#/volume] in Blood
        "panel": "CBC",
        "ranges": {
            "default": {"low": 4.5, "high": 11.0, "critical_low": 2.0, "critical_high": 30.0},
        },
    },
    "789-8": {  # Erythrocytes (RBC) [#/volume] in Blood
        "panel": "CBC",
        "ranges": {
            "default": {"low": 4.0, "high": 5.5, "critical_low": 2.5, "critical_high": 7.5},
            "male": {"low": 4.5, "high": 5.5, "critical_low": 2.5, "critical_high": 7.5},
            "female": {"low": 4.0, "high": 5.0, "critical_low": 2.5, "critical_high": 7.0},
        },
    },
    "718-7": {  # Hemoglobin [Mass/volume] in Blood
        "panel": "CBC",
        "ranges": {
            "default": {"low": 12.0, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "male": {"low": 13.5, "high": 17.5, "critical_low": 7.0, "critical_high": 20.0},
            "female": {"low": 12.0, "high": 16.0, "critical_low": 7.0, "critical_high": 18.5},
        },
    },
    "4544-3": {  # Hematocrit [Volume Fraction] by Automated count
        "panel": "CBC",
        "ranges": {
            "default": {"low": 36.0, "high": 52.0, "critical_low": 20.0, "critical_high": 60.0},
            "male": {"low": 40.0, "high": 52.0, "critical_low": 20.0, "critical_high": 60.0},
            "female": {"low": 36.0, "high": 46.0, "critical_low": 20.0, "critical_high": 60.0},
        },
    },
    "20570-8": {  # Hematocrit [Volume Fraction] by calculation
        "panel": "CBC",
        "ranges": {
            "default": {"low": 36.0, "high": 52.0, "critical_low": 20.0, "critical_high": 60.0},
            "male": {"low": 40.0, "high": 52.0, "critical_low": 20.0, "critical_high": 60.0},
            "female": {"low": 36.0, "high": 46.0, "critical_low": 20.0, "critical_high": 60.0},
        },
    },
    "787-2": {  # MCV [Entitic mean volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 80.0, "high": 100.0, "critical_low": 60.0, "critical_high": 120.0},
        },
    },
    "785-6": {  # MCH [Entitic mass]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 27.0, "high": 33.0, "critical_low": 18.0, "critical_high": 40.0},
        },
    },
    "786-4": {  # MCHC [Mass/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 32.0, "high": 36.0, "critical_low": 25.0, "critical_high": 40.0},
        },
    },
    "788-0": {  # Erythrocyte distribution width (RDW) — Synthea reports in fL, not %
        "panel": "CBC",
        "ranges": {
            "default": {"low": 35.0, "high": 46.0, "critical_low": 25.0, "critical_high": 60.0},
        },
    },
    "777-3": {  # Platelets [#/volume] in Blood
        "panel": "CBC",
        "ranges": {
            "default": {"low": 150.0, "high": 400.0, "critical_low": 50.0, "critical_high": 1000.0},
        },
    },
    "32207-3": {  # Platelet distribution width — Synthea reports in fL
        "panel": "CBC",
        "ranges": {
            "default": {"low": 150.0, "high": 520.0, "critical_low": 50.0, "critical_high": 700.0},
        },
    },
    "32623-1": {  # Platelet mean volume (MPV)
        "panel": "CBC",
        "ranges": {
            "default": {"low": 7.5, "high": 11.5, "critical_low": 5.0, "critical_high": 14.0},
        },
    },
    # CBC differential
    "770-8": {  # Neutrophils [#/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 1.5, "high": 7.5, "critical_low": 0.5, "critical_high": 20.0},
        },
    },
    "736-9": {  # Lymphocytes [#/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 1.0, "high": 4.0, "critical_low": 0.3, "critical_high": 10.0},
        },
    },
    "742-7": {  # Monocytes [#/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 0.2, "high": 1.0, "critical_low": 0.0, "critical_high": 3.0},
        },
    },
    "711-2": {  # Eosinophils [#/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 0.0, "high": 0.5, "critical_low": 0.0, "critical_high": 5.0},
        },
    },
    "704-7": {  # Basophils [#/volume]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 0.0, "high": 0.1, "critical_low": 0.0, "critical_high": 1.0},
        },
    },
    "731-0": {  # Lymphocytes [%]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 20.0, "high": 40.0, "critical_low": 5.0, "critical_high": 70.0},
        },
    },
    "751-8": {  # Neutrophils [%] in Blood
        "panel": "CBC",
        "ranges": {
            "default": {"low": 40.0, "high": 70.0, "critical_low": 10.0, "critical_high": 90.0},
        },
    },
    "26515-7": {  # Platelets [#/volume] — alternate code
        "panel": "CBC",
        "ranges": {
            "default": {"low": 150.0, "high": 400.0, "critical_low": 50.0, "critical_high": 1000.0},
        },
    },
    "33256-9": {  # Reticulocyte count [%]
        "panel": "CBC",
        "ranges": {
            "default": {"low": 0.5, "high": 2.5, "critical_low": 0.1, "critical_high": 10.0},
        },
    },
    # -----------------------------------------------------------------------
    # BMP (Basic Metabolic Panel)
    # -----------------------------------------------------------------------
    "2345-7": {  # Glucose [Mass/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0},
        },
    },
    "3094-0": {  # BUN (Urea nitrogen) [Mass/volume]
        "panel": "BMP",
        "ranges": {
            "default": {"low": 7.0, "high": 20.0, "critical_low": 2.0, "critical_high": 100.0},
        },
    },
    "2160-0": {  # Creatinine [Mass/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 0.6, "high": 1.2, "critical_low": 0.3, "critical_high": 10.0},
            "male": {"low": 0.7, "high": 1.3, "critical_low": 0.3, "critical_high": 10.0},
            "female": {"low": 0.5, "high": 1.1, "critical_low": 0.3, "critical_high": 10.0},
        },
    },
    "2951-2": {  # Sodium [Moles/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 136.0, "high": 145.0, "critical_low": 120.0, "critical_high": 160.0},
        },
    },
    "2823-3": {  # Potassium [Moles/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 3.5, "high": 5.0, "critical_low": 2.5, "critical_high": 6.5},
        },
    },
    "2075-0": {  # Chloride [Moles/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 98.0, "high": 106.0, "critical_low": 80.0, "critical_high": 120.0},
        },
    },
    "1963-8": {  # Bicarbonate (CO2) [Moles/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 22.0, "high": 29.0, "critical_low": 10.0, "critical_high": 40.0},
        },
    },
    "17861-6": {  # Calcium [Mass/volume] in Serum or Plasma
        "panel": "BMP",
        "ranges": {
            "default": {"low": 8.5, "high": 10.5, "critical_low": 6.0, "critical_high": 13.0},
        },
    },
    "33037-3": {  # Anion gap
        "panel": "BMP",
        "ranges": {
            "default": {"low": 3.0, "high": 12.0, "critical_low": 0.0, "critical_high": 25.0},
        },
    },
    # -----------------------------------------------------------------------
    # CMP additions (beyond BMP)
    # -----------------------------------------------------------------------
    "2885-2": {  # Total Protein [Mass/volume] in Serum or Plasma
        "panel": "CMP",
        "ranges": {
            "default": {"low": 6.0, "high": 8.3, "critical_low": 3.0, "critical_high": 12.0},
        },
    },
    "1751-7": {  # Albumin [Mass/volume] in Serum or Plasma
        "panel": "CMP",
        "ranges": {
            "default": {"low": 3.5, "high": 5.5, "critical_low": 1.5, "critical_high": 7.0},
        },
    },
    "1975-2": {  # Bilirubin total [Mass/volume] in Serum or Plasma
        "panel": "CMP",
        "ranges": {
            "default": {"low": 0.1, "high": 1.2, "critical_low": 0.0, "critical_high": 12.0},
        },
    },
    "1968-7": {  # Bilirubin direct [Mass/volume]
        "panel": "CMP",
        "ranges": {
            "default": {"low": 0.0, "high": 0.3, "critical_low": 0.0, "critical_high": 5.0},
        },
    },
    "6768-6": {  # Alkaline phosphatase [Enzymatic activity/volume]
        "panel": "CMP",
        "ranges": {
            "default": {"low": 44.0, "high": 147.0, "critical_low": 20.0, "critical_high": 500.0},
        },
    },
    "1742-6": {  # ALT (Alanine aminotransferase) [Enzymatic activity/volume]
        "panel": "CMP",
        "ranges": {
            "default": {"low": 7.0, "high": 56.0, "critical_low": 0.0, "critical_high": 1000.0},
        },
    },
    "1920-8": {  # AST (Aspartate aminotransferase) [Enzymatic activity/volume]
        "panel": "CMP",
        "ranges": {
            "default": {"low": 10.0, "high": 40.0, "critical_low": 0.0, "critical_high": 1000.0},
        },
    },
    # -----------------------------------------------------------------------
    # Lipid Panel
    # -----------------------------------------------------------------------
    "2093-3": {  # Total Cholesterol [Mass/volume]
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 0.0, "high": 200.0, "critical_low": 0.0, "critical_high": 400.0},
        },
    },
    "2085-9": {  # HDL Cholesterol [Mass/volume]
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 40.0, "high": 60.0, "critical_low": 20.0, "critical_high": 100.0},
            "male": {"low": 40.0, "high": 60.0, "critical_low": 20.0, "critical_high": 100.0},
            "female": {"low": 50.0, "high": 60.0, "critical_low": 20.0, "critical_high": 100.0},
        },
    },
    "18262-6": {  # LDL Cholesterol [Mass/volume] by Direct assay
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 0.0, "high": 100.0, "critical_low": 0.0, "critical_high": 300.0},
        },
    },
    "2571-8": {  # Triglycerides [Mass/volume]
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 0.0, "high": 150.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "13457-7": {  # LDL Cholesterol (calculated)
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 0.0, "high": 100.0, "critical_low": 0.0, "critical_high": 300.0},
        },
    },
    "9830-1": {  # Total Cholesterol/HDL ratio
        "panel": "Lipid Panel",
        "ranges": {
            "default": {"low": 0.0, "high": 5.0, "critical_low": 0.0, "critical_high": 10.0},
        },
    },
    # -----------------------------------------------------------------------
    # HbA1c / Diabetes
    # -----------------------------------------------------------------------
    "4548-4": {  # Hemoglobin A1c/Hemoglobin total [%]
        "panel": "Diabetes",
        "ranges": {
            "default": {"low": 4.0, "high": 5.6, "critical_low": 3.0, "critical_high": 15.0},
        },
    },
    "2339-0": {  # Glucose [Mass/volume] in Blood
        "panel": "Diabetes",
        "ranges": {
            "default": {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0},
        },
    },
    "14749-6": {  # Glucose [Mass/volume] in Serum or Plasma — fasting
        "panel": "Diabetes",
        "ranges": {
            "default": {"low": 70.0, "high": 100.0, "critical_low": 40.0, "critical_high": 400.0},
        },
    },
    "2340-8": {  # Glucose [Mass/volume] in Blood — post-prandial
        "panel": "Diabetes",
        "ranges": {
            "default": {"low": 70.0, "high": 140.0, "critical_low": 40.0, "critical_high": 400.0},
        },
    },
    # -----------------------------------------------------------------------
    # Thyroid Panel
    # -----------------------------------------------------------------------
    "3016-3": {  # TSH [Units/volume] in Serum or Plasma
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 0.4, "high": 4.0, "critical_low": 0.01, "critical_high": 50.0},
        },
    },
    "3024-7": {  # Free T4 [Mass/volume] in Serum or Plasma
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 0.8, "high": 1.8, "critical_low": 0.3, "critical_high": 5.0},
        },
    },
    "3026-2": {  # Free T3 [Mass/volume] in Serum or Plasma
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 2.3, "high": 4.2, "critical_low": 1.0, "critical_high": 8.0},
        },
    },
    "3053-6": {  # T3 total [Mass/volume]
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 80.0, "high": 200.0, "critical_low": 40.0, "critical_high": 400.0},
        },
    },
    "8098-6": {  # Thyroid peroxidase Ab [Units/volume]
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 0.0, "high": 35.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "11580-8": {  # T4 total [Mass/volume] in Serum or Plasma
        "panel": "Thyroid",
        "ranges": {
            "default": {"low": 5.0, "high": 12.0, "critical_low": 2.0, "critical_high": 20.0},
        },
    },
    # -----------------------------------------------------------------------
    # Liver Panel
    # -----------------------------------------------------------------------
    "2324-2": {  # GGT [Enzymatic activity/volume]
        "panel": "Liver",
        "ranges": {
            "default": {"low": 0.0, "high": 65.0, "critical_low": 0.0, "critical_high": 500.0},
            "male": {"low": 0.0, "high": 65.0, "critical_low": 0.0, "critical_high": 500.0},
            "female": {"low": 0.0, "high": 45.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "2532-0": {  # LDH [Enzymatic activity/volume]
        "panel": "Liver",
        "ranges": {
            "default": {"low": 140.0, "high": 280.0, "critical_low": 50.0, "critical_high": 1000.0},
        },
    },
    "1798-8": {  # Amylase [Enzymatic activity/volume]
        "panel": "Liver",
        "ranges": {
            "default": {"low": 28.0, "high": 100.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "3040-3": {  # Lipase [Enzymatic activity/volume]
        "panel": "Liver",
        "ranges": {
            "default": {"low": 0.0, "high": 160.0, "critical_low": 0.0, "critical_high": 1000.0},
        },
    },
    # -----------------------------------------------------------------------
    # Renal Panel
    # -----------------------------------------------------------------------
    "33914-3": {  # eGFR (CKD-EPI)
        "panel": "Renal",
        "ranges": {
            "default": {"low": 60.0, "high": 120.0, "critical_low": 15.0, "critical_high": 200.0},
        },
    },
    "69405-9": {  # eGFR (CKD-EPI, non-race)
        "panel": "Renal",
        "ranges": {
            "default": {"low": 60.0, "high": 120.0, "critical_low": 15.0, "critical_high": 200.0},
        },
    },
    "14959-1": {  # Microalbumin [Mass/volume] in Urine
        "panel": "Renal",
        "ranges": {
            "default": {"low": 0.0, "high": 30.0, "critical_low": 0.0, "critical_high": 300.0},
        },
    },
    "14958-3": {  # Microalbumin/Creatinine ratio [Mass ratio]
        "panel": "Renal",
        "ranges": {
            "default": {"low": 0.0, "high": 30.0, "critical_low": 0.0, "critical_high": 300.0},
        },
    },
    "3097-3": {  # BUN/Creatinine ratio
        "panel": "Renal",
        "ranges": {
            "default": {"low": 10.0, "high": 20.0, "critical_low": 5.0, "critical_high": 40.0},
        },
    },
    # -----------------------------------------------------------------------
    # Iron Studies
    # -----------------------------------------------------------------------
    "2498-4": {  # Iron [Mass/volume] in Serum or Plasma
        "panel": "Iron Studies",
        "ranges": {
            "default": {"low": 60.0, "high": 170.0, "critical_low": 20.0, "critical_high": 400.0},
            "male": {"low": 65.0, "high": 175.0, "critical_low": 20.0, "critical_high": 400.0},
            "female": {"low": 50.0, "high": 170.0, "critical_low": 20.0, "critical_high": 400.0},
        },
    },
    "2502-3": {  # TIBC [Mass/volume]
        "panel": "Iron Studies",
        "ranges": {
            "default": {"low": 250.0, "high": 370.0, "critical_low": 100.0, "critical_high": 600.0},
        },
    },
    "2276-4": {  # Ferritin [Mass/volume] in Serum or Plasma
        "panel": "Iron Studies",
        "ranges": {
            "default": {"low": 12.0, "high": 300.0, "critical_low": 5.0, "critical_high": 1000.0},
            "male": {"low": 24.0, "high": 336.0, "critical_low": 5.0, "critical_high": 1000.0},
            "female": {"low": 11.0, "high": 307.0, "critical_low": 5.0, "critical_high": 1000.0},
        },
    },
    "2500-7": {  # Transferrin saturation [%]
        "panel": "Iron Studies",
        "ranges": {
            "default": {"low": 20.0, "high": 50.0, "critical_low": 5.0, "critical_high": 80.0},
        },
    },
    # -----------------------------------------------------------------------
    # Coagulation
    # -----------------------------------------------------------------------
    "5902-2": {  # Prothrombin time (PT) [seconds]
        "panel": "Coagulation",
        "ranges": {
            "default": {"low": 11.0, "high": 13.5, "critical_low": 8.0, "critical_high": 30.0},
        },
    },
    "6301-6": {  # INR
        "panel": "Coagulation",
        "ranges": {
            "default": {"low": 0.8, "high": 1.2, "critical_low": 0.5, "critical_high": 5.0},
        },
    },
    "3173-2": {  # aPTT [seconds]
        "panel": "Coagulation",
        "ranges": {
            "default": {"low": 25.0, "high": 35.0, "critical_low": 15.0, "critical_high": 100.0},
        },
    },
    "3255-7": {  # Fibrinogen [Mass/volume]
        "panel": "Coagulation",
        "ranges": {
            "default": {"low": 200.0, "high": 400.0, "critical_low": 100.0, "critical_high": 800.0},
        },
    },
    "48065-7": {  # D-dimer [Mass/volume]
        "panel": "Coagulation",
        "ranges": {
            "default": {"low": 0.0, "high": 0.5, "critical_low": 0.0, "critical_high": 4.0},
        },
    },
    # -----------------------------------------------------------------------
    # Cardiac Markers
    # -----------------------------------------------------------------------
    "10839-9": {  # Troponin I [Mass/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 0.0, "high": 0.04, "critical_low": 0.0, "critical_high": 2.0},
        },
    },
    "6598-7": {  # Troponin T [Mass/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 0.0, "high": 0.01, "critical_low": 0.0, "critical_high": 2.0},
        },
    },
    "30522-7": {  # BNP [Mass/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 0.0, "high": 100.0, "critical_low": 0.0, "critical_high": 5000.0},
        },
    },
    "33762-6": {  # NT-proBNP [Mass/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 0.0, "high": 125.0, "critical_low": 0.0, "critical_high": 10000.0},
        },
    },
    "2157-6": {  # CK (Creatine kinase) [Enzymatic activity/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 30.0, "high": 200.0, "critical_low": 10.0, "critical_high": 2000.0},
            "male": {"low": 55.0, "high": 170.0, "critical_low": 10.0, "critical_high": 2000.0},
            "female": {"low": 30.0, "high": 135.0, "critical_low": 10.0, "critical_high": 2000.0},
        },
    },
    "49563-0": {  # CK-MB [Mass/volume]
        "panel": "Cardiac",
        "ranges": {
            "default": {"low": 0.0, "high": 5.0, "critical_low": 0.0, "critical_high": 25.0},
        },
    },
    # -----------------------------------------------------------------------
    # Inflammatory Markers
    # -----------------------------------------------------------------------
    "1988-5": {  # CRP [Mass/volume] in Serum or Plasma
        "panel": "Inflammatory",
        "ranges": {
            "default": {"low": 0.0, "high": 3.0, "critical_low": 0.0, "critical_high": 50.0},
        },
    },
    "30341-2": {  # ESR [Length/time]
        "panel": "Inflammatory",
        "ranges": {
            "default": {"low": 0.0, "high": 20.0, "critical_low": 0.0, "critical_high": 100.0},
            "male": {"low": 0.0, "high": 15.0, "critical_low": 0.0, "critical_high": 100.0},
            "female": {"low": 0.0, "high": 20.0, "critical_low": 0.0, "critical_high": 100.0},
        },
    },
    "33959-8": {  # Procalcitonin [Mass/volume]
        "panel": "Inflammatory",
        "ranges": {
            "default": {"low": 0.0, "high": 0.1, "critical_low": 0.0, "critical_high": 10.0},
        },
    },
    # -----------------------------------------------------------------------
    # Electrolytes (beyond BMP)
    # -----------------------------------------------------------------------
    "19123-9": {  # Magnesium [Mass/volume] in Serum or Plasma
        "panel": "Electrolytes",
        "ranges": {
            "default": {"low": 1.7, "high": 2.2, "critical_low": 1.0, "critical_high": 4.0},
        },
    },
    "2777-1": {  # Phosphate [Mass/volume] in Serum or Plasma
        "panel": "Electrolytes",
        "ranges": {
            "default": {"low": 2.5, "high": 4.5, "critical_low": 1.0, "critical_high": 8.0},
        },
    },
    "2947-0": {  # Uric acid [Mass/volume] in Serum or Plasma
        "panel": "Electrolytes",
        "ranges": {
            "default": {"low": 3.0, "high": 7.0, "critical_low": 1.0, "critical_high": 12.0},
            "male": {"low": 3.5, "high": 7.2, "critical_low": 1.0, "critical_high": 12.0},
            "female": {"low": 2.6, "high": 6.0, "critical_low": 1.0, "critical_high": 12.0},
        },
    },
    # -----------------------------------------------------------------------
    # Urinalysis
    # -----------------------------------------------------------------------
    "5811-5": {  # Specific gravity [Ratio] in Urine
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 1.005, "high": 1.030, "critical_low": 1.000, "critical_high": 1.040},
        },
    },
    "2756-5": {  # pH in Urine
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 4.5, "high": 8.0, "critical_low": 4.0, "critical_high": 9.0},
        },
    },
    "5770-3": {  # WBC [#/area] in Urine sediment by Microscopy
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 0.0, "high": 5.0, "critical_low": 0.0, "critical_high": 100.0},
        },
    },
    "5794-3": {  # RBC [#/area] in Urine sediment by Microscopy
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 0.0, "high": 3.0, "critical_low": 0.0, "critical_high": 100.0},
        },
    },
    "20454-5": {  # Protein [Mass/volume] in Urine
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 0.0, "high": 14.0, "critical_low": 0.0, "critical_high": 300.0},
        },
    },
    "2349-9": {  # Glucose [Presence] in Urine
        "panel": "Urinalysis",
        "ranges": {
            "default": {"low": 0.0, "high": 15.0, "critical_low": 0.0, "critical_high": 200.0},
        },
    },
    # -----------------------------------------------------------------------
    # Tumor Markers
    # -----------------------------------------------------------------------
    "2857-1": {  # PSA [Mass/volume]
        "panel": "Tumor Markers",
        "ranges": {
            "default": {"low": 0.0, "high": 4.0, "critical_low": 0.0, "critical_high": 20.0},
        },
    },
    "2039-6": {  # CEA [Mass/volume]
        "panel": "Tumor Markers",
        "ranges": {
            "default": {"low": 0.0, "high": 3.0, "critical_low": 0.0, "critical_high": 50.0},
        },
    },
    "1834-1": {  # AFP (Alpha-fetoprotein) [Mass/volume]
        "panel": "Tumor Markers",
        "ranges": {
            "default": {"low": 0.0, "high": 10.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "10334-1": {  # CA-125 [Units/volume]
        "panel": "Tumor Markers",
        "ranges": {
            "default": {"low": 0.0, "high": 35.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    "24108-3": {  # CA 19-9 [Units/volume]
        "panel": "Tumor Markers",
        "ranges": {
            "default": {"low": 0.0, "high": 37.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    # -----------------------------------------------------------------------
    # Vitamins & Nutrition
    # -----------------------------------------------------------------------
    "1989-3": {  # Vitamin D (25-OH) [Mass/volume]
        "panel": "Vitamins",
        "ranges": {
            "default": {"low": 30.0, "high": 100.0, "critical_low": 10.0, "critical_high": 150.0},
        },
    },
    "2132-9": {  # Vitamin B12 [Mass/volume]
        "panel": "Vitamins",
        "ranges": {
            "default": {"low": 200.0, "high": 900.0, "critical_low": 100.0, "critical_high": 2000.0},
        },
    },
    "2284-8": {  # Folate [Mass/volume] in Serum or Plasma
        "panel": "Vitamins",
        "ranges": {
            "default": {"low": 2.7, "high": 17.0, "critical_low": 1.0, "critical_high": 25.0},
        },
    },
    # -----------------------------------------------------------------------
    # Blood Gas (Arterial)
    # -----------------------------------------------------------------------
    "2744-1": {  # pH in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 7.35, "high": 7.45, "critical_low": 7.10, "critical_high": 7.60},
        },
    },
    "2019-8": {  # pCO2 [Partial pressure] in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 35.0, "high": 45.0, "critical_low": 20.0, "critical_high": 70.0},
        },
    },
    "2703-7": {  # pO2 [Partial pressure] in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 80.0, "high": 100.0, "critical_low": 40.0, "critical_high": 150.0},
        },
    },
    "1960-4": {  # Bicarbonate [Moles/volume] in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 22.0, "high": 26.0, "critical_low": 10.0, "critical_high": 40.0},
        },
    },
    "2708-6": {  # Oxygen saturation in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 95.0, "high": 100.0, "critical_low": 85.0, "critical_high": 100.0},
        },
    },
    "1925-7": {  # Base excess in Arterial blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": -2.0, "high": 2.0, "critical_low": -10.0, "critical_high": 10.0},
        },
    },
    "2713-6": {  # Lactate [Moles/volume] in Blood
        "panel": "ABG",
        "ranges": {
            "default": {"low": 0.5, "high": 2.0, "critical_low": 0.0, "critical_high": 10.0},
        },
    },
    # -----------------------------------------------------------------------
    # Endocrine
    # -----------------------------------------------------------------------
    "2986-8": {  # Testosterone [Mass/volume] in Serum or Plasma
        "panel": "Endocrine",
        "ranges": {
            "default": {"low": 10.0, "high": 800.0, "critical_low": 5.0, "critical_high": 1500.0},
            "male": {"low": 300.0, "high": 1000.0, "critical_low": 100.0, "critical_high": 1500.0},
            "female": {"low": 15.0, "high": 70.0, "critical_low": 5.0, "critical_high": 200.0},
        },
    },
    "14715-7": {  # Cortisol [Mass/volume] in Serum or Plasma (AM)
        "panel": "Endocrine",
        "ranges": {
            "default": {"low": 6.0, "high": 23.0, "critical_low": 1.0, "critical_high": 50.0},
        },
    },
    # -----------------------------------------------------------------------
    # Pancreatic
    # -----------------------------------------------------------------------
    "1825-9": {  # Ammonia [Moles/volume]
        "panel": "Pancreatic",
        "ranges": {
            "default": {"low": 15.0, "high": 45.0, "critical_low": 5.0, "critical_high": 200.0},
        },
    },
    # -----------------------------------------------------------------------
    # Infectious Disease
    # -----------------------------------------------------------------------
    "20507-0": {  # HIV 1+2 Ab
        "panel": "Infectious",
        "ranges": {
            "default": {"low": 0.0, "high": 1.0, "critical_low": 0.0, "critical_high": 10.0},
        },
    },
    # -----------------------------------------------------------------------
    # Stool
    # -----------------------------------------------------------------------
    "57905-2": {  # Hemoglobin.gastrointestinal.lower [Presence] in Stool
        "panel": "Stool",
        "ranges": {
            "default": {"low": 0.0, "high": 100.0, "critical_low": 0.0, "critical_high": 500.0},
        },
    },
    # -----------------------------------------------------------------------
    # Vital Signs
    # -----------------------------------------------------------------------
    "8867-4": {  # Heart rate [/min]
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 60.0, "high": 100.0, "critical_low": 40.0, "critical_high": 150.0},
        },
    },
    "9279-1": {  # Respiratory rate [/min]
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 12.0, "high": 20.0, "critical_low": 8.0, "critical_high": 40.0},
        },
    },
    "8310-5": {  # Body temperature [Cel]
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 36.1, "high": 37.2, "critical_low": 34.0, "critical_high": 40.0},
        },
    },
    "8480-6": {  # Systolic blood pressure [mmHg]
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 90.0, "high": 120.0, "critical_low": 70.0, "critical_high": 180.0},
        },
    },
    "8462-4": {  # Diastolic blood pressure [mmHg]
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 60.0, "high": 80.0, "critical_low": 40.0, "critical_high": 120.0},
        },
    },
    "59408-5": {  # SpO2 [%] by Pulse oximetry
        "panel": "Vital Signs",
        "ranges": {
            "default": {"low": 95.0, "high": 100.0, "critical_low": 85.0, "critical_high": 100.0},
        },
    },
    # -----------------------------------------------------------------------
    # Miscellaneous
    # -----------------------------------------------------------------------
    "14804-9": {  # Lactate dehydrogenase (LD) [Enzymatic activity/volume]
        "panel": "Miscellaneous",
        "ranges": {
            "default": {"low": 140.0, "high": 280.0, "critical_low": 50.0, "critical_high": 1000.0},
        },
    },
    "1742-7": {  # Alanine aminotransferase/Aspartate aminotransferase ratio
        "panel": "Liver",
        "ranges": {
            "default": {"low": 0.7, "high": 1.4, "critical_low": 0.0, "critical_high": 5.0},
        },
    },
    "2692-2": {  # Osmolality in Serum/Plasma
        "panel": "Electrolytes",
        "ranges": {
            "default": {"low": 275.0, "high": 295.0, "critical_low": 240.0, "critical_high": 320.0},
        },
    },
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_reference_range(
    loinc_code: str,
    patient_sex: str | None = None,
) -> dict | None:
    """Return reference range for a LOINC code, with sex-aware fallback.

    Args:
        loinc_code: LOINC code (e.g. "718-7").
        patient_sex: "male", "female", or None.

    Returns:
        Dict with keys {low, high, critical_low, critical_high} or None
        if the LOINC code is not in the lookup table.
    """
    entry = REFERENCE_RANGES.get(loinc_code)
    if entry is None:
        return None

    ranges = entry["ranges"]

    # Try sex-specific range first, then fall back to default
    if patient_sex and patient_sex in ranges:
        return ranges[patient_sex]
    return ranges["default"]


def get_panel(loinc_code: str) -> str | None:
    """Return the clinical panel name for a LOINC code, or None."""
    entry = REFERENCE_RANGES.get(loinc_code)
    return entry["panel"] if entry else None


def compute_interpretation(
    value: float,
    reference_range: dict,
) -> HL7Interpretation:
    """Compute HL7 interpretation code from a value and reference range.

    Boundary semantics are exclusive:
      value < critical_low  -> "LL"
      value < low           -> "L"
      value > critical_high -> "HH"
      value > high          -> "H"
      otherwise             -> "N"

    Args:
        value: Numeric observation value.
        reference_range: Dict with {low, high, critical_low, critical_high}.

    Returns:
        HL7 interpretation code.
    """
    if value < reference_range["critical_low"]:
        return "LL"
    if value < reference_range["low"]:
        return "L"
    if value > reference_range["critical_high"]:
        return "HH"
    if value > reference_range["high"]:
        return "H"
    return "N"


def interpret_observation(
    observation: dict,
    patient_sex: str | None = None,
) -> tuple[HL7Interpretation | None, dict | None]:
    """Interpret a FHIR Observation resource.

    Extracts the LOINC code and numeric value, looks up the reference range,
    and computes the HL7 interpretation code.

    Args:
        observation: FHIR Observation resource dict.
        patient_sex: "male", "female", or None.

    Returns:
        Tuple of (interpretation_code, reference_range_dict).
        Returns (None, None) if the observation cannot be interpreted
        (missing LOINC, no numeric value, or LOINC not in lookup table).
    """
    # Extract LOINC code
    coding = observation.get("code", {}).get("coding", [])
    if not coding:
        return None, None
    loinc_code = coding[0].get("code")
    if not loinc_code:
        return None, None

    # Extract numeric value
    value_quantity = observation.get("valueQuantity")
    if not value_quantity or not isinstance(value_quantity, dict):
        return None, None
    value = value_quantity.get("value")
    if value is None or not isinstance(value, (int, float)):
        return None, None

    # Look up reference range
    ref_range = get_reference_range(loinc_code, patient_sex)
    if ref_range is None:
        return None, None

    # Compute interpretation
    interpretation = compute_interpretation(float(value), ref_range)
    return interpretation, ref_range


def build_fhir_interpretation(code: HL7Interpretation) -> list[dict]:
    """Build a FHIR-conformant interpretation field value.

    Returns a list with a single CodeableConcept, conforming to
    FHIR R4 Observation.interpretation structure.
    """
    return [
        {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                    "code": code,
                    "display": _INTERPRETATION_DISPLAY[code],
                }
            ]
        }
    ]


def build_fhir_reference_range(ref_range: dict, unit: str | None = None) -> list[dict]:
    """Build a FHIR-conformant referenceRange field value.

    Returns a list with a single reference range entry, conforming to
    FHIR R4 Observation.referenceRange structure.
    """
    rr: dict = {
        "low": {"value": ref_range["low"]},
        "high": {"value": ref_range["high"]},
    }
    if unit:
        rr["low"]["unit"] = unit
        rr["high"]["unit"] = unit
    return [rr]
