"""Tests for query concept extraction module."""

from app.services.query_parser import (
    ConceptMatch,
    SynonymExpansion,
    expand_synonyms,
    extract_concepts,
    generate_bigrams,
    remove_stop_words,
    tokenize,
)


# ── Tokenization ─────────────────────────────────────────────────────────


class TestTokenize:
    def test_basic(self):
        assert tokenize("Hello World") == ["hello", "world"]

    def test_punctuation_stripped(self):
        assert tokenize("What's the patient's BP?") == ["whats", "the", "patients", "bp"]

    def test_preserves_hyphens(self):
        assert tokenize("type-2 diabetes") == ["type-2", "diabetes"]

    def test_empty_string(self):
        assert tokenize("") == []

    def test_whitespace_only(self):
        assert tokenize("   ") == []


# ── Stop word removal ────────────────────────────────────────────────────


class TestRemoveStopWords:
    def test_removes_common_words(self):
        tokens = ["what", "are", "the", "lab", "results"]
        assert remove_stop_words(tokens) == ["lab", "results"]

    def test_removes_clinical_filler(self):
        tokens = ["show", "me", "recent", "medications"]
        assert remove_stop_words(tokens) == ["medications"]

    def test_preserves_clinical_terms(self):
        tokens = ["diabetes", "blood", "pressure"]
        assert remove_stop_words(tokens) == ["diabetes", "blood", "pressure"]

    def test_empty_list(self):
        assert remove_stop_words([]) == []

    def test_all_stop_words(self):
        assert remove_stop_words(["the", "is", "a"]) == []


# ── Bigrams ──────────────────────────────────────────────────────────────


class TestGenerateBigrams:
    def test_basic(self):
        assert generate_bigrams(["blood", "pressure"]) == ["blood pressure"]

    def test_multiple(self):
        assert generate_bigrams(["heart", "rate", "monitor"]) == [
            "heart rate",
            "rate monitor",
        ]

    def test_single_token(self):
        assert generate_bigrams(["diabetes"]) == []

    def test_empty(self):
        assert generate_bigrams([]) == []


# ── Concept extraction ───────────────────────────────────────────────────


class TestExtractConcepts:
    SAMPLE_NODES = [
        ("Diabetes mellitus type 2", "Condition"),
        ("Hypertension", "Condition"),
        ("Blood Pressure", "Observation"),
        ("Heart Rate", "Observation"),
        ("Lisinopril 10 MG Oral Tablet", "MedicationRequest"),
        ("Metformin 500 MG", "MedicationRequest"),
        ("Complete Blood Count", "DiagnosticReport"),
    ]

    def test_single_term_match(self):
        matches = extract_concepts("Tell me about diabetes", self.SAMPLE_NODES)
        terms = [m.term for m in matches]
        assert "Diabetes mellitus type 2" in terms

    def test_bigram_match(self):
        matches = extract_concepts("What is the blood pressure?", self.SAMPLE_NODES)
        terms = [m.term for m in matches]
        assert "Blood Pressure" in terms

    def test_case_insensitive(self):
        matches = extract_concepts("HYPERTENSION treatment", self.SAMPLE_NODES)
        terms = [m.term for m in matches]
        assert "Hypertension" in terms

    def test_resource_type_hint(self):
        matches = extract_concepts("diabetes", self.SAMPLE_NODES)
        diabetes_match = next(m for m in matches if "Diabetes" in m.term)
        assert diabetes_match.resource_type_hint == "Condition"

    def test_no_match(self):
        matches = extract_concepts("appendectomy surgery", self.SAMPLE_NODES)
        assert matches == []

    def test_empty_query(self):
        assert extract_concepts("", self.SAMPLE_NODES) == []

    def test_whitespace_query(self):
        assert extract_concepts("   ", self.SAMPLE_NODES) == []

    def test_empty_nodes(self):
        assert extract_concepts("diabetes", []) == []

    def test_all_stop_words_query(self):
        assert extract_concepts("what is the", self.SAMPLE_NODES) == []

    def test_multiple_matches(self):
        matches = extract_concepts(
            "diabetes and hypertension", self.SAMPLE_NODES
        )
        terms = [m.term for m in matches]
        assert "Diabetes mellitus type 2" in terms
        assert "Hypertension" in terms

    def test_no_duplicates(self):
        matches = extract_concepts("blood blood pressure", self.SAMPLE_NODES)
        blood_pressure_matches = [m for m in matches if m.term == "Blood Pressure"]
        assert len(blood_pressure_matches) == 1

    def test_medication_match(self):
        matches = extract_concepts("metformin dose", self.SAMPLE_NODES)
        terms = [m.term for m in matches]
        assert "Metformin 500 MG" in terms

    def test_frozen_dataclass(self):
        match = ConceptMatch(term="Test", resource_type_hint="Condition")
        assert match.term == "Test"
        assert match.resource_type_hint == "Condition"


# ── Synonym expansion ──────────────────────────────────────────────────


class TestExpandSynonyms:
    def test_single_category_synonym(self):
        result = expand_synonyms(["labs"])
        assert result.categories == ["laboratory"]
        assert result.resource_types == []
        assert result.remaining_terms == []

    def test_single_resource_type_synonym(self):
        result = expand_synonyms(["meds"])
        assert result.resource_types == ["MedicationRequest"]
        assert result.categories == []
        assert result.remaining_terms == []

    def test_mixed_query(self):
        result = expand_synonyms(["labs", "vitals"])
        assert "laboratory" in result.categories
        assert "vital-signs" in result.categories
        assert result.remaining_terms == []

    def test_non_synonym_passthrough(self):
        result = expand_synonyms(["diabetes", "management"])
        assert result.resource_types == []
        assert result.categories == []
        assert result.remaining_terms == ["diabetes", "management"]

    def test_bigram_synonym(self):
        result = expand_synonyms(["blood", "work"])
        assert result.categories == ["laboratory"]
        assert result.remaining_terms == []

    def test_bigram_vital_signs(self):
        result = expand_synonyms(["vital", "signs"])
        assert result.categories == ["vital-signs"]
        assert result.remaining_terms == []

    def test_bigram_care_plans(self):
        result = expand_synonyms(["care", "plans"])
        assert result.resource_types == ["CarePlan"]
        assert result.remaining_terms == []

    def test_mixed_synonym_and_terms(self):
        result = expand_synonyms(["meds", "diabetes"])
        assert result.resource_types == ["MedicationRequest"]
        assert result.remaining_terms == ["diabetes"]

    def test_multiple_resource_types(self):
        result = expand_synonyms(["allergies", "meds"])
        assert "AllergyIntolerance" in result.resource_types
        assert "MedicationRequest" in result.resource_types

    def test_empty_input(self):
        result = expand_synonyms([])
        assert result == SynonymExpansion()

    def test_immunization_synonyms(self):
        result = expand_synonyms(["shots"])
        assert result.resource_types == ["Immunization"]

    def test_procedures_synonym(self):
        result = expand_synonyms(["surgeries"])
        assert result.resource_types == ["Procedure"]

    def test_diagnoses_synonym(self):
        result = expand_synonyms(["diagnoses"])
        assert result.resource_types == ["Condition"]
