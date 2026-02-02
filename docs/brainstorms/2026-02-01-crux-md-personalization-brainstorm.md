# Brainstorm: crux.md Physician Personalization System

**Date**: 2026-02-01
**Status**: Ready for planning

## Problem Statement

CruxMD's LLM agent treats all physicians identically — same communication style, same clinical reasoning approach, no memory of preferences or protocols. Physicians have distinct specialties, communication preferences, condition-management protocols, and patient interaction styles that the system should adapt to. Currently the system prompt is a hardcoded template in `agent.py` with no per-user customization.

## Proposed Solution

A **crux.md** personalization layer — a per-physician configuration document (inspired by Claude's `claude.md`) stored as a single JSONB document in PostgreSQL. This document is loaded into the LLM context window for every chat session, augmenting the system prompt with physician-specific guidance.

The system has three tiers of personalization:
1. **Physician-level (crux.md)** — Always loaded. General preferences, role context, condition protocols, patient communication preferences.
2. **Patient-specific semantic memory** — Loaded only when interacting with that patient. Learned preferences, behavioral patterns, care context. Stored in a `patient_memories` table (serializable to FHIR extensions on demand). Shared across all physicians who see the patient.
3. **Recursive learning loop** — A background agent that analyzes feedback signals (thumbs up/down, optional free text) and proposes updates to either physician crux.md or patient semantic memory.

## Key Decisions

- **Single JSONB document per user**: One `physician_preferences` row with a JSONB column. Load wholesale into prompt. Simple, flexible, easy to version by snapshotting.
- **Patient memory as separate table**: `patient_memories` table with structured entries, independent of FHIR resources. Can be serialized to FHIR extensions on demand but table-first for query/lifecycle management. Shared across all physicians (collaborative intelligence).
- **Feedback is low-friction**: Thumbs up/down is one click, no dismissal needed. Optional free text. System collects context about the rated item automatically. Batch analysis later.
- **Edit via structured form + chat + onboarding wizards**: Profile page with structured sections and presets. Chat-driven updates ("add my diabetes protocol"). Onboarding wizards that interview the physician to populate sections — including condition-specific wizards and a scenario-based patient communication trainer.
- **Learning loop is deferred**: MVP does not include automated learning. Feedback collection and the batch learning agent come in later phases.
- **System prompt is immutable**: Base system prompt is locked. crux.md is an additive overlay that cannot override safety constraints or response format.
- **Selective protocol loading**: Condition protocols are matched against (1) patient's active conditions from the knowledge graph and (2) keyword matches in the current user message. General preferences, role context, and patient communication sections always load.

## crux.md Document Structure

```json
{
  "version": 1,
  "general_preferences": {
    "style": "concise",           // preset: concise | detailed | balanced
    "verbosity": "low",           // preset: low | medium | high
    "tone": "clinical",           // preset: clinical | conversational | academic
    "format_preferences": "...",  // free text: "bullet points over paragraphs", etc.
    "custom_directives": "..."    // free text: cross-cutting patterns, interaction preferences
  },
  "role_context": {
    "specialty": "Internal Medicine",
    "sub_specialties": ["Endocrinology"],
    "practice_setting": "Outpatient clinic",
    "panel_size": 2400,
    "years_experience": 15,
    "custom_context": "..."       // free text for anything else
  },
  "condition_protocols": {
    "diabetes_type_2": {
      "diagnosis_criteria": "...",
      "standard_testing": "...",
      "treatment_ladder": "...",
      "referral_triggers": "...",
      "notes": "..."
    },
    "heart_failure": { ... }
  },
  "patient_communication": {
    "messaging_style": "...",
    "reading_level": "...",
    "empathy_approach": "...",
    "explanation_level": "...",
    "cultural_considerations": "...",
    "language_preferences": "...",
    "custom_directives": "..."
  },
  "custom_sections": {
    "key": "value"
  }
}
```

## Profile Page UX

Five sections, accessible from the user's profile:

1. **General Preferences** — How the agent interacts with the physician. Preset dropdowns (style, verbosity, tone) plus free text for cross-cutting directives and interaction patterns. This is "how does the AI work for me."

2. **About Me** — Role context. Structured fields (specialty, sub-specialties, practice setting, panel size, years experience) plus free text for additional context.

3. **Condition Protocols** — List of condition cards, each expandable to show protocol text. "Add condition" button. "Run wizard" button per condition to populate via guided interview. Manual edit always available.

4. **Patient Communication** — How the agent helps the physician communicate with patients. Preferences extracted from the scenario trainer (see below), shown as readable summaries with edit capability. "Run scenario trainer" button. This is "how does the AI help me talk to patients."

5. **Raw View** (optional/advanced) — Full crux.md JSON for power users who want direct control.

## Onboarding Wizards

Wizards are specialized chat sessions with wizard-specific system prompts. They interview the physician, synthesize answers, and produce proposed crux.md sections for review and approval.

### Types
- **General onboarding** — Populates general preferences + role context
- **Condition-specific** — Walks through: diagnostic criteria → initial workup → treatment ladder → monitoring schedule → referral triggers → special considerations
- **Patient communication scenario trainer** — See below

### Patient Communication Scenario Trainer

Instead of asking physicians to self-report their communication style, present clinical scenarios and ask them to write actual patient messages:

**Example scenarios:**
- "A patient with newly diagnosed Type 2 diabetes needs to be told about their diagnosis. Write the message you'd send."
- "A patient missed their follow-up appointment. Write the message."
- "A patient's lab results came back normal. Write the message."
- "You need to discuss a sensitive topic (e.g., weight management) with a patient."

**Adaptive approach:** Start with 3 scenarios. Analyze confidence in extracted patterns (tone, reading level, empathy style, medical jargon usage, message length, structure). If patterns are unclear or vary significantly across scenario types, present additional scenarios (up to ~8). Variation is expected — delivering bad news vs routine follow-up naturally differ.

**Output:** The LLM analyzes all messages and extracts a patient communication profile. The physician reviews the extracted preferences before they're saved to crux.md.

## Patient Memory Model

The `patient_memories` table captures contextual intelligence learned through physician interaction — not clinical facts (those live in FHIR), but behavioral and relational context:

**Examples:**
- "Patient is anxious about medication side effects — lead with reassurance"
- "Patient's daughter is primary caregiver — include her in communication"
- "Patient resistant to insulin — approach gradually, emphasize lifestyle first"
- "Prefers analogies when discussing lab results"

**Key properties:**
- Shared across all physicians who see the patient (collaborative intelligence)
- Loaded into context only when chatting about that patient
- Separate from FHIR data but serializable to FHIR extensions on demand
- Structured entries with: key, value, source (which session/interaction), confidence, timestamps

## Scope

### In Scope (MVP)
- `physician_preferences` table with JSONB `crux_md` column, linked to auth user
- Load crux.md into system prompt context for all chat sessions
- Selective condition protocol loading (active conditions + query keyword match)
- Profile page with 5 sections (general prefs, about me, condition protocols, patient comm, raw view)
- General preferences presets (style, verbosity, tone)
- Role context section (specialty, practice setting, etc.)
- Condition protocol sections (free text per condition, add/remove)
- Patient communication preferences section
- API endpoints for CRUD on crux.md

### In Scope (Phase 2)
- Thumbs up/down feedback collection with optional free text
- Feedback context capture (what message was rated, patient context, etc.)
- `patient_memories` table for patient-specific semantic memory
- Patient memory loaded into context when chatting about that patient
- Chat-driven crux.md updates ("I prefer bullet points" → proposed edit)

### In Scope (Phase 3)
- Onboarding wizards (general + condition-specific + scenario trainer)
- Batch learning agent that analyzes feedback and proposes crux.md updates
- Patient semantic memory learning from interaction patterns
- Version history / audit trail for crux.md changes

### Out of Scope
- Multi-tenant / organization-level preferences
- Sharing protocols between physicians
- Condition protocol marketplace / templates library
- Real-time learning (immediate crux.md mutation on feedback)

## Resolved Design Questions

- **System prompt editability**: Base system prompt is immutable. crux.md is an additive overlay — it can influence style, add protocols, and set preferences, but cannot override safety constraints or response format rules.
- **Condition protocol loading**: Selective. Match protocols against (1) patient's active conditions from the knowledge graph and (2) keyword matches in the current user message. General preferences, role context, and patient communication sections always load.
- **Token budget strategy**: crux.md gets a soft budget of ~2,000 tokens. General prefs/role/patient-comm sections (~400-600 tokens) always load. Condition protocols are selectively loaded and trimmed if over budget, similar to how retrieved context is already managed. Per-section character limits in the UI prevent runaway protocol lengths.
- **Prompt rendering**: crux.md is rendered as structured natural language sections in the system prompt (not raw JSON). The context engine formats it into readable sections the LLM can follow.
- **Patient memory scope**: Shared across all physicians (collaborative intelligence), not scoped to physician-patient pairs.
- **Profile page sections**: General Preferences (agent interaction), About Me (role context), Condition Protocols, Patient Communication, Raw View.

## Open Questions
- What character limits per section are appropriate? (e.g., 2000 chars per condition protocol)
- Should crux.md changes be audited/versioned from day one, or defer to phase 3?
- How should the onboarding wizard handle physicians with no existing preferences — start blank or suggest defaults based on specialty?

## Constraints
- Must work within existing token budget (~12,000 tokens for context). crux.md competes with patient context for space.
- Must integrate with existing BetterAuth user model (link via user_id).
- Frontend is Next.js 15 + shadcn/ui — profile page should follow existing patterns.
- No additional infrastructure — PostgreSQL only, no Redis or separate services.

## Risks
- **Token budget pressure**: Large crux.md + large patient context could exceed budget. Mitigation: Set section size limits, selective loading for condition protocols.
- **Stale preferences**: Without the learning loop, crux.md may go stale if physicians don't manually update. Mitigation: Periodic prompts to review, phase 2 learning loop.
- **Over-personalization**: LLM may over-index on crux.md preferences and miss important clinical nuance. Mitigation: System prompt hierarchy — safety constraints always override preferences.
