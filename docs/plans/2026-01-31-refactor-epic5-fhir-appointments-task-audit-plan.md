---
title: "refactor: FHIR-native Appointments + Task model audit"
type: refactor
date: 2026-01-31
---

# Refactor: FHIR-Native Appointments + Task Model Audit

## Overview

Epic 5 (Task & Session Infrastructure) built three data concepts:

| Concept | Current State | Decision |
|---------|--------------|----------|
| **Session** | Custom SQLAlchemy model | Keep as-is (internal app concept, no FHIR equivalent) |
| **Task** | FHIR-native (FhirResource + TaskProjection + serializer) | Audit field mappings, ensure easy FHIR serialization |
| **Appointment** | Planned as custom JSON fixtures | Convert to FHIR Appointment resources |

This plan audits the Task model's FHIR alignment and implements Appointments as native FHIR resources using the same projection pattern that Tasks use.

## Problem Statement

Story 5.3 (Demo Fixtures) originally planned appointments as app-specific JSON. But FHIR R4 has a robust Appointment resource, and our architecture already has a proven pattern for FHIR-native storage with projections. Appointments should follow that pattern for consistency and to demonstrate FHIR interoperability.

The Task model is already FHIR-native but was built quickly. An audit ensures the field mappings are clean and the on-the-fly FHIR serialization is spec-compliant.

## Proposed Solution

### Part A: Task FHIR Audit

Review and tighten the existing Task → FHIR mapping in the serializer/extractors. No schema changes expected — this is a code review + minor fixes pass.

**Current mapping (from `TaskFhirSerializer.to_fhir()`):**

| CruxMD Field | FHIR Task Field | Status |
|---|---|---|
| title | description | OK |
| status | status | OK (via `get_fhir_status()` with deferred extension) |
| priority | priority | OK (routine/urgent/asap/stat matches FHIR) |
| type | code.coding[0] (custom system) | OK — custom codes are valid FHIR |
| category | code.coding[1] (custom system) | Review — should this be a separate `category` field? |
| patient_id | for.reference | OK |
| focus_resource_id | focus.reference | OK |
| due_on | restriction.period.end | OK |
| description | note[0].text | OK |
| priority_score | extension (valueInteger) | OK — no FHIR equivalent, extension correct |
| provenance | extension (valueString/JSON) | OK |
| context_config | extension (valueString/JSON) | OK |
| session_id | extension (valueString) | OK |

**Audit items:**
- Verify `intent` field is set correctly (currently hardcoded to "order")
- Check if `category` should use FHIR's `code` field vs a separate coding — current dual-coding approach in `code` is reasonable but could use FHIR `businessStatus` instead
- Confirm `authoredOn` / `lastModified` are populated
- Ensure `for` reference format is `Patient/{fhir_id}` not `Patient/{uuid}`
- Review the legacy `tasks` SQLAlchemy model in `models/task.py` — if unused, consider removing or documenting its migration-only purpose

### Part B: FHIR Appointment Resource

Implement Appointments as FHIR Appointment resources following the existing Task pattern.

#### FHIR R4 Appointment Fields We Need

| FHIR Field | Our Use | Required |
|---|---|---|
| status | booked, arrived, fulfilled, cancelled, noshow | Yes (1..1) |
| start | Appointment start time | Yes (for booked) |
| end | Appointment end time | Yes (for booked) |
| minutesDuration | Duration | No |
| description | Short summary ("Annual physical", "Diabetes follow-up") | No |
| appointmentType | New patient / follow-up / urgent / routine | No |
| serviceType | Office visit / telehealth / procedure | No |
| specialty | Internal medicine / cardiology / etc. | No |
| priority | 0-9 integer (iCal convention) | No |
| participant | Array of {actor, type, status} — Patient + Practitioner | Yes (1..*) |
| comment | Internal notes | No |
| reasonReference | Link to Condition driving the visit | No |

#### CruxMD Extensions (stored as FHIR extensions)

| Extension | Purpose |
|---|---|
| `visit_context` | Pre-visit prep notes, AI-generated agenda |
| `linked_task_id` | Reference to CruxMD Task that surfaced this appointment |

#### Projection Fields (for indexed queries)

| Column | Extracted From | Index |
|---|---|---|
| status | `status` | Yes |
| start_time | `start` | Yes |
| end_time | `end` | No |
| duration_minutes | `minutesDuration` | No |
| description | `description` | No |
| appointment_type | `appointmentType.coding[0].code` | Yes |
| service_type | `serviceType[0].coding[0].code` | Yes |
| patient_fhir_id | `participant[].actor` (where type=Patient) | Yes |
| practitioner_name | `participant[].actor` (where type=Practitioner) | No |

#### Files to Create/Modify (following Task pattern exactly)

| File | Purpose |
|---|---|
| `projections/serializers/appointment.py` | NEW — AppointmentFhirSerializer (to_fhir, update_fhir_data) |
| `projections/extractors/appointment.py` | NEW — Field extractors for projection sync |
| `projections/constants.py` | MODIFY — Add appointment-specific system URLs and extension names |
| `models/projections/appointment.py` | NEW — AppointmentProjection SQLAlchemy model |
| `repositories/appointment.py` | NEW — AppointmentRepository (CRUD via FhirRepository + projection) |
| `schemas/appointment.py` | NEW — AppointmentCreate, AppointmentResponse, etc. |
| `routes/appointments.py` | NEW — CRUD endpoints + /fhir raw endpoint |
| `alembic/versions/xxx_add_appointment_projection.py` | NEW — Migration for appointment_projections table |

### Part C: Revised Demo Fixtures (Story 5.3)

With Appointments as FHIR resources, the demo fixture approach changes:

| Fixture Type | Format | Loaded Via |
|---|---|---|
| **Tasks** | FHIR Task JSON (via TaskFhirSerializer) | seed_database.py → FhirRepository |
| **Appointments** | FHIR Appointment JSON (via AppointmentFhirSerializer) | seed_database.py → FhirRepository |
| **Sessions** | Direct SQLAlchemy inserts | seed_database.py (custom model, not FHIR) |

Fixture files would be proper FHIR resources:
- `fixtures/demo/tasks.json` — Array of FHIR Task resources
- `fixtures/demo/appointments.json` — Array of FHIR Appointment resources
- `fixtures/demo/sessions.json` — Array of Session objects (app-specific)

### Part D: Clean Up Legacy Task Table

The standalone `tasks` SQLAlchemy model in `models/task.py` coexists with the FHIR-native path. If the `tasks` table is truly unused (all queries go through `FhirResource` + `TaskProjection`), we should:

1. Generate a migration to drop the `tasks` table and its 4 enum types
2. Remove `models/task.py`
3. Keep the enums in `schemas/task.py` (still used by Pydantic schemas)

## Task Decomposition

### Story 5.3a: Task FHIR Audit
- Review and fix Task serializer FHIR field mappings
- Verify `intent`, `authoredOn`, reference formats
- Add `lastModified` to serializer output
- Document any remaining gaps between CruxMD Task and FHIR Task
- Consider whether legacy `tasks` table should be dropped (separate migration task)

### Story 5.3b: FHIR Appointment — Projection Infrastructure
- Create AppointmentProjection model
- Create AppointmentFhirSerializer
- Create appointment field extractors
- Register in ProjectionRegistry
- Add Alembic migration for `appointment_projections` table
- Add constants to `projections/constants.py`

### Story 5.3c: FHIR Appointment — Repository, Schemas, Routes
- Create Pydantic schemas (AppointmentCreate, AppointmentUpdate, AppointmentResponse)
- Create AppointmentRepository
- Create routes (GET list, GET by id, GET /fhir, POST, PATCH, DELETE)
- Wire into FastAPI app
- Depends on: 5.3b

### Story 5.3d: Demo Fixtures (Revised)
- Create FHIR Task fixture JSON for clinical scenarios
- Create FHIR Appointment fixture JSON (8-12 today, 4-6 tomorrow)
- Create Session fixture data
- Update seed_database.py to load all fixtures through FhirRepository
- Patient references must match existing Synthea fixtures
- Depends on: 5.3b, 5.3c

### Story 5.3e (optional): Drop Legacy Tasks Table
- Generate migration to drop `tasks` table and enum types
- Remove `models/task.py`
- Verify no code references the old model
- Depends on: 5.3a confirming it's unused

## Acceptance Criteria

- [ ] Task serializer produces valid FHIR R4 Task resources (verify with field audit)
- [ ] Appointments stored as FHIR Appointment resources in `fhir_resources` table
- [ ] AppointmentProjection enables indexed queries (by date, status, patient, type)
- [ ] `/api/appointments` CRUD endpoints work
- [ ] `/api/appointments/{id}/fhir` returns raw FHIR Appointment JSON
- [ ] Demo fixtures load through FhirRepository (not direct SQL)
- [ ] seed_database.py loads tasks, appointments, and sessions
- [ ] All existing Task tests still pass

## References

- FHIR R4 Task: https://hl7.org/fhir/R4/task.html
- FHIR R4 Appointment: https://hl7.org/fhir/R4/appointment.html
- Existing Task serializer: `backend/app/projections/serializers/task.py`
- Existing Task projection: `backend/app/models/projections/task.py`
- Existing Task repository: `backend/app/repositories/task.py`
- ProjectionRegistry: `backend/app/projections/registry.py`
