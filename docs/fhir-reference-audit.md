# FHIR Inter-Resource References Audit

**Task**: CruxMD-7y6
**Date**: 2026-01-24
**Purpose**: Map inter-resource relationships in Synthea FHIR bundles for Neo4j graph enrichment

## Overview

This audit analyzes FHIR resources in the `fixtures/synthea/*.json` bundles to identify reference fields that link resources together. These references are candidates for modeling as edges in the Neo4j knowledge graph.

**Data Source**: 5 Synthea patient bundles containing 3,843 total resources

## Executive Summary

The most clinically meaningful relationships for graph queries like "What happened during this encounter?" center on the **Encounter** resource as a temporal hub. Almost all clinical resources reference back to an Encounter, making it the natural organizing principle for clinical events.

### Priority 1: Core Clinical Graph (Encounter-Centric)

| Source | Reference Field | Target | Count | Coverage | Semantic Meaning |
|--------|----------------|--------|-------|----------|------------------|
| Condition | encounter | Encounter | 166 | 100% | Diagnosed during |
| MedicationRequest | encounter | Encounter | 177 | 100% | Prescribed during |
| Observation | encounter | Encounter | 832 | 100% | Measured during |
| Procedure | encounter | Encounter | 820 | 100% | Performed during |
| DiagnosticReport | encounter | Encounter | 371 | 100% | Reported during |
| Immunization | encounter | Encounter | 73 | 100% | Administered during |
| ImagingStudy | encounter | Encounter | 22 | 100% | Captured during |
| DocumentReference | context.encounter | Encounter | 210 | 100% | Authored during |

### Priority 2: Clinical Reasoning Links

| Source | Reference Field | Target | Count | Coverage | Semantic Meaning |
|--------|----------------|--------|-------|----------|------------------|
| MedicationRequest | reasonReference | Condition | 145 | 82% | Treats condition |
| Procedure | reasonReference | Condition | 295 | 36% | Performed for condition |
| DiagnosticReport | result | Observation | 324 | 87% | Contains results |
| CarePlan | addresses | Condition | 8 | 62% | Addresses condition |
| CarePlan | activity.detail.reasonReference | Condition | 23 | 177%* | Activity targets condition |
| MedicationAdministration | reasonReference | Condition | 5 | 33% | Given for condition |

*>100% indicates multiple references per resource

### Priority 3: Coordination & Context

| Source | Reference Field | Target | Count | Coverage | Semantic Meaning |
|--------|----------------|--------|-------|----------|------------------|
| CarePlan | careTeam | CareTeam | 13 | 100% | Managed by team |
| CarePlan | encounter | Encounter | 13 | 100% | Created during |
| CareTeam | encounter | Encounter | 13 | 100% | Formed during |
| MedicationRequest | medicationReference | Medication | 15 | 8% | References medication |

### Priority 4: Financial/Administrative Links

| Source | Reference Field | Target | Count | Coverage | Semantic Meaning |
|--------|----------------|--------|-------|----------|------------------|
| Claim | item.encounter | Encounter | 387 | 100% | Billed for encounter |
| Claim | diagnosis.diagnosisReference | Condition | 166 | 43% | Claims diagnosis |
| Claim | prescription | MedicationRequest | 177 | 46% | Claims prescription |
| Claim | procedure.procedureReference | Procedure | 820 | 212%* | Claims procedure |
| ExplanationOfBenefit | claim | Claim | 387 | 100% | Explains claim |
| ExplanationOfBenefit | item.encounter | Encounter | 387 | 100% | Covers encounter |

## Detailed Analysis by Resource Type

### Encounter (210 resources)

The temporal hub for clinical events. Every encounter belongs to a patient.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 210 | Patient visited |

**Graph Pattern**: Already implemented as `Patient -[:HAS_ENCOUNTER]-> Encounter`

### Condition (166 resources)

Clinical diagnoses/problems. All link to both patient and encounter.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 166 | Patient has |
| encounter | Encounter | 166 | Diagnosed during |

**Graph Pattern**:
- Current: `Patient -[:HAS_CONDITION]-> Condition`
- **Proposed**: `Encounter -[:DIAGNOSED]-> Condition`

### MedicationRequest (177 resources)

Prescriptions and medication orders. Rich linking to encounters and conditions.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 177 | Prescribed to |
| encounter | Encounter | 177 | Ordered during |
| reasonReference | Condition | 145 | Treats |
| medicationReference | Medication | 15 | References |

**Graph Pattern**:
- Current: `Patient -[:HAS_MEDICATION_REQUEST]-> MedicationRequest`
- **Proposed**:
  - `Encounter -[:PRESCRIBED]-> MedicationRequest`
  - `MedicationRequest -[:TREATS]-> Condition`

### Observation (832 resources)

Clinical measurements (vitals, labs, assessments). Most numerous resource type.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 832 | Measured from |
| encounter | Encounter | 832 | Recorded during |

**Graph Pattern**:
- Current: `Patient -[:HAS_OBSERVATION]-> Observation`
- **Proposed**: `Encounter -[:RECORDED]-> Observation`

### Procedure (820 resources)

Clinical procedures performed. Strong link to conditions via reasonReference.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 820 | Performed on |
| encounter | Encounter | 820 | Performed during |
| reasonReference | Condition | 295 | Performed for |

**Graph Pattern**:
- **Proposed**:
  - `Encounter -[:PERFORMED]-> Procedure`
  - `Procedure -[:TREATS]-> Condition`

### DiagnosticReport (371 resources)

Lab reports and diagnostic summaries. Links observations together.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 371 | Reported for |
| encounter | Encounter | 371 | Reported during |
| result | Observation | 324 | Contains |

**Graph Pattern**:
- **Proposed**:
  - `Encounter -[:REPORTED]-> DiagnosticReport`
  - `DiagnosticReport -[:CONTAINS_RESULT]-> Observation`

### Immunization (73 resources)

Vaccinations administered.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| patient | Patient | 73 | Given to |
| encounter | Encounter | 73 | Administered during |

**Graph Pattern**:
- **Proposed**: `Encounter -[:ADMINISTERED]-> Immunization`

### CarePlan (13 resources)

Treatment plans addressing conditions.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 13 | Created for |
| encounter | Encounter | 13 | Created during |
| careTeam | CareTeam | 13 | Managed by |
| addresses | Condition | 8 | Addresses |
| activity.detail.reasonReference | Condition | 23 | Activity targets |

**Graph Pattern**:
- **Proposed**:
  - `Encounter -[:CREATED]-> CarePlan`
  - `CarePlan -[:ADDRESSES]-> Condition`
  - `CarePlan -[:MANAGED_BY]-> CareTeam`

### CareTeam (13 resources)

Care coordination teams.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 13 | Cares for |
| encounter | Encounter | 13 | Formed during |
| participant.member | Patient | 13 | Includes patient |

**Graph Pattern**:
- **Proposed**: `Encounter -[:FORMED]-> CareTeam`

### ImagingStudy (22 resources)

Radiology and imaging exams.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 22 | Imaged |
| encounter | Encounter | 22 | Captured during |

**Graph Pattern**:
- **Proposed**: `Encounter -[:CAPTURED]-> ImagingStudy`

### MedicationAdministration (15 resources)

Record of medication being given (vs. just ordered).

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 15 | Administered to |
| context | Encounter | 15 | Administered during |
| reasonReference | Condition | 5 | Given for |

**Graph Pattern**:
- **Proposed**:
  - `Encounter -[:ADMINISTERED]-> MedicationAdministration`
  - `MedicationAdministration -[:TREATS]-> Condition`

### DocumentReference (210 resources)

Clinical documents (notes, summaries).

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| subject | Patient | 210 | Authored for |
| context.encounter | Encounter | 210 | Authored during |

**Graph Pattern**:
- **Proposed**: `Encounter -[:DOCUMENTED]-> DocumentReference`

### Device (33 resources)

Medical devices associated with patient.

| Field | Target | Count | Semantic |
|-------|--------|-------|----------|
| patient | Patient | 33 | Associated with |

**Graph Pattern**:
- **Proposed**: `Patient -[:HAS_DEVICE]-> Device`

## Recommended Graph Schema

### Node Types (Priority Order)

1. **Patient** - Central entity
2. **Encounter** - Temporal hub for clinical events
3. **Condition** - Diagnoses/problems
4. **MedicationRequest** - Prescriptions
5. **Observation** - Measurements/results
6. **Procedure** - Clinical procedures
7. **DiagnosticReport** - Lab reports
8. **Immunization** - Vaccinations
9. **CarePlan** - Treatment plans
10. **CareTeam** - Care coordination
11. **ImagingStudy** - Radiology
12. **DocumentReference** - Clinical notes
13. **Device** - Medical devices

### Relationship Types (Priority Order)

#### Tier 1: Essential (implement first)
```
Patient -[:HAS_ENCOUNTER]-> Encounter
Patient -[:HAS_CONDITION]-> Condition  (existing)
Patient -[:HAS_MEDICATION_REQUEST]-> MedicationRequest  (existing)
Patient -[:HAS_OBSERVATION]-> Observation  (existing)
Encounter -[:DIAGNOSED]-> Condition
Encounter -[:PRESCRIBED]-> MedicationRequest
Encounter -[:RECORDED]-> Observation
Encounter -[:PERFORMED]-> Procedure
```

#### Tier 2: Clinical Reasoning (high value)
```
MedicationRequest -[:TREATS]-> Condition
Procedure -[:TREATS]-> Condition
DiagnosticReport -[:CONTAINS_RESULT]-> Observation
Encounter -[:REPORTED]-> DiagnosticReport
```

#### Tier 3: Extended Clinical
```
Encounter -[:ADMINISTERED]-> Immunization
CarePlan -[:ADDRESSES]-> Condition
CarePlan -[:MANAGED_BY]-> CareTeam
Encounter -[:DOCUMENTED]-> DocumentReference
Encounter -[:CAPTURED]-> ImagingStudy
```

#### Tier 4: Administrative
```
Claim -[:BILLS]-> Encounter
Claim -[:BILLS_PROCEDURE]-> Procedure
ExplanationOfBenefit -[:EXPLAINS]-> Claim
```

## Sample Queries Enabled

With the proposed graph schema, these queries become trivial:

**"What happened during this encounter?"**
```cypher
MATCH (e:Encounter {fhir_id: $encounter_id})
OPTIONAL MATCH (e)-[:DIAGNOSED]->(c:Condition)
OPTIONAL MATCH (e)-[:PRESCRIBED]->(m:MedicationRequest)
OPTIONAL MATCH (e)-[:RECORDED]->(o:Observation)
OPTIONAL MATCH (e)-[:PERFORMED]->(p:Procedure)
RETURN e, collect(c), collect(m), collect(o), collect(p)
```

**"What medications treat this condition?"**
```cypher
MATCH (c:Condition {fhir_id: $condition_id})<-[:TREATS]-(m:MedicationRequest)
RETURN m
```

**"What observations support this diagnosis?"**
```cypher
MATCH (c:Condition)<-[:DIAGNOSED]-(e:Encounter)-[:REPORTED]->(dr:DiagnosticReport)-[:CONTAINS_RESULT]->(o:Observation)
WHERE c.fhir_id = $condition_id
RETURN o
```

**"Show me the patient's clinical timeline"**
```cypher
MATCH (p:Patient {id: $patient_id})-[:HAS_ENCOUNTER]->(e:Encounter)
OPTIONAL MATCH (e)-[r]->(resource)
RETURN e, type(r), resource
ORDER BY e.period_start DESC
```

## Implementation Notes

### Current State (graph.py)

The existing `KnowledgeGraph` class implements:
- Patient nodes with demographic properties
- Condition, MedicationRequest, AllergyIntolerance, Observation, Encounter nodes
- Only `Patient -[:HAS_*]->` relationships (patient-centric)

### Gaps to Address

1. **Missing Encounter-centric relationships**: All clinical resources have `encounter` references that aren't being modeled
2. **Missing clinical reasoning links**: `reasonReference` fields link meds/procedures to conditions
3. **Missing DiagnosticReport->Observation links**: Critical for lab result aggregation
4. **Missing resource types**: DiagnosticReport, Immunization, CarePlan, CareTeam, etc.

### Migration Strategy

1. Add new relationship types to existing `_upsert_*` methods
2. Add new `_upsert_*` methods for missing resource types
3. Store encounter FHIR ID on clinical resources for linking
4. Build inter-resource relationships in a second pass after all resources exist
