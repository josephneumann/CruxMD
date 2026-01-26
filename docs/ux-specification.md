# CruxMD UX Specification

> **Version:** 1.0
> **Date:** January 2026
> **Status:** Draft — Pending Implementation
> **Authors:** Joe Neumann, Claude (BigBoy)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Design Philosophy](#design-philosophy)
3. [Design Principles](#design-principles)
4. [Information Architecture](#information-architecture)
5. [Layout System](#layout-system)
6. [Core Experiences](#core-experiences)
7. [Navigation & Keyboard Model](#navigation--keyboard-model)
8. [Task Model](#task-model)
9. [Session Model](#session-model)
10. [Context Engine](#context-engine)
11. [Component Specifications](#component-specifications)
12. [Agent Delegation Model](#agent-delegation-model)
13. [Data Requirements](#data-requirements)
14. [Conflicts with Existing Plan](#conflicts-with-existing-plan)
15. [Implementation Priorities](#implementation-priorities)

---

## Executive Summary

CruxMD is a **clinical intelligence platform** that blends the fluid experience of a conversational AI canvas with the structured reliability of traditional EHR views. The interface is designed around the principle that **clinicians should never have to choose between AI-powered insights and the comfort of seeing their data in predictable places**.

### The Core Insight

Traditional EHRs organize around **data** (meds tab, labs tab, notes tab). CruxMD organizes around **work** (what task do I need to do next?) while preserving instant access to structured data views.

### Key Experience Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   MAIN HUB                              TASK ENGAGED                        │
│   ─────────────────────────────────     ─────────────────────────────────   │
│                                                                             │
│   Conversational canvas                 Focused conversation                │
│   + Task queue in sidebar        →      + Task-specific context             │
│   + Quick launch actions                + Quick action pills                │
│                                                                             │
│   "What do I need to do?"               "Let me do this thing well"         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Design Philosophy

### The Hybrid Model

CruxMD rejects the false choice between:
- **Conversational AI** (flexible but unpredictable)
- **Traditional EHR** (structured but rigid)

Instead, we embrace both:

| Need | Solution |
|------|----------|
| "What's going on with this patient?" | Conversational canvas with AI synthesis |
| "Show me the full med list" | Structured sidebar panel, always accessible |
| "What should I do next?" | Prioritized task queue |
| "Help me think through this" | AI-guided analysis with inline visualizations |

### Work-Driven, Not Browse-Driven

Clinicians don't open CruxMD to "browse patients." They open it to **accomplish work**:

- Review the critical lab result
- Prepare for the next appointment
- Respond to patient messages
- Sign pending orders

The interface surfaces **prioritized tasks** and lets clinicians launch directly into focused work sessions.

### Escape Hatches to Familiar Ground

While the conversational canvas is primary, clinicians can always access traditional structured views:

- Full medication list
- Complete lab history
- Patient demographics and photo
- Recent notes

These aren't hidden — they're one click away in the context sidebar. The AI augments but never replaces the clinician's ability to verify the complete picture.

### Keyboard-First, Mouse-Optional

Clinical workflows demand speed. The interface is designed for keyboard navigation:

- `Tab` to move between tasks
- `Enter` to engage
- `Esc` to pause and return to hub
- Shortcut keys for common actions

Mouse/touch works, but power users never need to leave the keyboard.

---

## Design Principles

### 1. Quiet Competence

The interface speaks through work, not words. No celebratory animations, no "Great question!" affirmations. When CruxMD surfaces an insight, it presents it plainly: "Here's what I found."

**Implications:**
- No confetti or achievement badges
- Loading states are subtle (the X logo animation, not skeleton screens)
- Success states are matter-of-fact
- Error states are clear and actionable, never apologetic

### 2. Earned Confidence

Clinicians should feel certain, not hopeful. Every insight traces to source. Every recommendation has grounding.

**Implications:**
- All AI assertions link to supporting data (citations)
- Provenance is visible but not intrusive
- The clinician can always drill into the evidence

### 3. Structured Content Has One Home

The sidebar (desktop) or bottom sheet (mobile) is the **single location** for all structured data. This creates a consistent mental model:

- Canvas = conversation, synthesis, exploration
- Sidebar = data, facts, verification

**Implications:**
- Never scatter structured content across multiple locations
- The sidebar transforms based on context, but it's always the sidebar
- Quick action pills below the input are actions, not data

### 4. Context Awareness

The interface adapts to what the clinician is doing. When reviewing a critical lab, the sidebar shows relevant meds and related labs. When responding to a message, it shows the message thread and patient context.

**Implications:**
- Sidebar content is dynamically configured per task type
- Quick actions are surfaced based on context, not static menus
- The AI knows what's relevant and prioritizes accordingly

### 5. Zero Synchronous Dead Time

The clinician's workflow is never blocked by system operations. Session handoffs, task completion, and context assembly happen asynchronously.

**Implications:**
- No "please wait" modals
- Background operations complete while user continues
- Optimistic UI updates with graceful error handling

### 6. Warm, Not Cold

Following the CruxMD brand identity: Book Cloth terracotta, Ivory backgrounds, humanist typography. Premium without flash.

**Implications:**
- No clinical blue or sterile white
- Generous whitespace, room to think
- Typography like well-set medical literature

---

## Information Architecture

### Primary Structure

```
CruxMD
├── Main Hub (Home)
│   ├── Conversational Canvas (open-ended queries)
│   ├── Quick Launch Actions (contextual pills)
│   └── Task Queue Sidebar
│       ├── Critical Alerts
│       ├── Routine Coordination
│       ├── My Schedule
│       └── Latest Research
│
├── Task Engaged View
│   ├── Focused Conversational Canvas
│   │   ├── Task header and summary
│   │   ├── AI analysis and conversation
│   │   ├── Inline visualizations
│   │   └── Quick action pills
│   └── Context Sidebar (transforms per task type)
│       ├── Patient header
│       ├── Relevant clinical data
│       ├── Quick actions
│       └── Full chart access
│
├── Session Inventory (paused sessions)
│
└── Full Chart View (escape hatch to traditional EHR)
    ├── Overview
    ├── Medications
    ├── Labs
    ├── Problems
    ├── Notes
    └── Timeline
```

### Task Categories

#### Critical Alerts
Time-sensitive items flagged for immediate attention:
- Hospitalization alerts (admitted, discharged, high-risk transitions)
- Abnormal results requiring triage
- Significant specialist findings changing management
- Time-sensitive orders needing signature

#### Routine Coordination
Regular work needing provider review:
- Patient messages (with draft responses pending)
- External results without critical findings
- Pre-visit prep for upcoming appointments
- Follow-up orders suggested by the system

#### My Schedule
Appointment-driven work:
- **My Next Patient**: Context-aware launch into the next scheduled appointment
- **Prepare for the Day**: Pre-visit prep, schedule overview, staff delegation nudges

#### Latest Research
Proactive learning and protocol management:
- Journal summaries relevant to the clinician's discipline
- Interactive learning modules
- Protocol adjustment suggestions
- Patient impact flags

---

## Layout System

### Desktop Layout (≥1024px)

Horizontal split: Conversational canvas on left (~65%), structured sidebar on right (~35%).

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  HEADER                                                                      │
│  Logo                                                        [User Menu]    │
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │                       │
│                                                      │                       │
│                                                      │                       │
│                 CONVERSATIONAL                       │       SIDEBAR         │
│                    CANVAS                            │                       │
│                                                      │    Task Queue (hub)   │
│                 (~65% width)                         │         or            │
│                                                      │    Task Context       │
│                                                      │     (engaged)         │
│                                                      │                       │
│                                                      │     (~35% width)      │
│                                                      │                       │
│                                                      │                       │
│  ┌────────────────────────────────────────────────┐  │                       │
│  │  Input...                                  [→] │  │                       │
│  └────────────────────────────────────────────────┘  │                       │
│  [Quick Action] [Quick Action] [Quick Action]        │                       │
│                                                      │                       │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

### Tablet Layout (768-1023px)

Similar to desktop with narrower sidebar. Sidebar may be collapsible.

```
┌────────────────────────────────────────────────────────────────┐
│  HEADER                                          [User] [«]   │
├──────────────────────────────────────────┬─────────────────────┤
│                                          │                     │
│              CANVAS                      │      SIDEBAR        │
│              (~70%)                      │       (~30%)        │
│                                          │                     │
│                                          │   [Collapsible]     │
│                                          │                     │
└──────────────────────────────────────────┴─────────────────────┘
```

### Mobile Layout (<768px)

Full-width canvas with bottom sheet for structured content.

```
┌─────────────────────────────────────┐
│  HEADER                       [≡]  │
├─────────────────────────────────────┤
│                                     │
│                                     │
│         CONVERSATIONAL              │
│            CANVAS                   │
│                                     │
│         (full width)                │
│                                     │
│                                     │
│  ┌─────────────────────────────────┐│
│  │  Input...                   [→] ││
│  └─────────────────────────────────┘│
│  [Quick Action] [Quick Action]      │
│                                     │
├─────────────────────────────────────┤
│  ▔▔▔▔▔▔▔▔▔▔ drag handle ▔▔▔▔▔▔▔▔▔▔ │
│  👤 Patient Name      K+ 6.2 ⚠️    │  ← Peek state
│  [Pull up for context]              │
└─────────────────────────────────────┘
```

#### Bottom Sheet Snap Points

| State | Height | Content Visible |
|-------|--------|-----------------|
| **Collapsed** | ~0% | Just drag handle, canvas gets full screen |
| **Peek** | ~15% | Patient name + key metric |
| **Half** | ~50% | Patient header + primary data (meds, labs) |
| **Full** | ~85% | Complete context panel |

---

## Core Experiences

### Experience 1: Main Hub

The default state when opening CruxMD. Designed to answer: "What do I need to do?"

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CruxMD                                                    [Dr. Neumann ▼]  │
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │                       │
│                                                      │  📋 ACTION QUEUE      │
│     [X Logo]                                         │                       │
│                                                      │  🚨 Critical (3)      │
│     Good morning, Dr. Neumann                        │  ├─ K+ 6.2 - R. Chen  │
│                                                      │  ├─ Discharge - M. Jo │
│                                                      │  └─ CT finding - J. S │
│     ┌──────────────────────────────────────────┐    │                       │
│     │  How can I help you today?           [→] │    │  📬 Routine (12)      │
│     └──────────────────────────────────────────┘    │  ├─ 5 messages        │
│                                                      │  └─ 7 results         │
│     [Prepare for the day] [My next patient]         │                       │
│     [Panel overview]                                 │  📅 Schedule          │
│                                                      │  ├─ ▶ 9:00 S. Williams│
│                                                      │  ├─ 9:30 T. Brown     │
│                                                      │  └─ 10:00 A. Garcia   │
│                                                      │                       │
│                                                      │  📚 Learning (1)      │
│                                                      │  └─ GLP-1 update      │
│                                                      │                       │
│                                                      │  ─────────────────    │
│                                                      │  [Tab] to navigate    │
│                                                      │  [Enter] to engage    │
│                                                      │                       │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

#### Hub Components

| Component | Purpose |
|-----------|---------|
| **Greeting** | Time-aware, personalized ("Good morning, Dr. Neumann") |
| **Open Input** | Free-form queries to the AI |
| **Quick Launch Pills** | Contextual shortcuts (Prepare for the day, My next patient) |
| **Task Queue Sidebar** | Categorized, prioritized work items |

#### Hub Interactions

| Action | Trigger | Result |
|--------|---------|--------|
| Open-ended query | Type in input, press Enter | Starts orchestrating session conversation |
| Launch task | Tab to task, press Enter | Transitions to Task Engaged view |
| Quick launch | Click pill or Tab+Enter | Starts specific workflow |

---

### Experience 2: Task Engaged

Focused work on a specific task. The sidebar transforms to show task-relevant context.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CruxMD    ← Hub [Esc]                              [Dr. Neumann ▼]         │
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │                       │
│  🚨 Critical Lab: K+ 6.2 mEq/L                       │  👤 ROBERT CHEN       │
│  Robert Chen                                         │  67M │ MRN 123456     │
│  ─────────────────────────────────────────────────   │                       │
│                                                      │  ─────────────────    │
│  [AI Summary]                                        │                       │
│  Robert's potassium is critically elevated at        │  RELEVANT MEDS        │
│  6.2 mEq/L. Key factors:                            │  • Lisinopril 20mg    │
│                                                      │  • Spironolactone 25mg│
│  • Dual K+-sparing therapy (ACE-I + MRA)            │    ↑ K+ risk          │
│  • CKD Stage 3b (eGFR 45)                           │                       │
│  • Trending up: 4.8 → 5.1 → 6.2 over 6 weeks        │  ─────────────────    │
│                                                      │                       │
│  ┌─────────────────────────────────────────────┐    │  LABS                 │
│  │ [Chart: K+ trend with reference range]      │    │  K+   6.2 H ⚠️       │
│  └─────────────────────────────────────────────┘    │  Cr   1.8            │
│                                                      │  eGFR 45             │
│  ─────────────────────────────────────────────────   │                       │
│                                                      │  ─────────────────    │
│  You: What's his kidney trajectory?                  │                       │
│                                                      │  ALLERGIES            │
│  AI: Creatinine rising steadily over 6 months:       │  • Penicillin         │
│  1.4 → 1.6 → 1.8 mg/dL. Combined with the           │                       │
│  hyperkalemia, this suggests progressive CKD...     │  ─────────────────    │
│                                                      │                       │
│  ┌──────────────────────────────────────────────┐   │  QUICK ACTIONS        │
│  │  Ask about this patient...               [→] │   │  [Order]              │
│  └──────────────────────────────────────────────┘   │  [Message]            │
│                                                      │  [Refer]              │
│  [Hold spironolactone] [Repeat K+ stat] [Call pt]   │                       │
│                                                      │  ─────────────────    │
│  ─────────────────────────────────────────────────   │  [✓ Complete task]    │
│  [✓ Mark resolved] [⏸ Pause] [📝 Document]          │  [Expand full chart →]│
│                                                      │                       │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

#### Task Engaged Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Task Header** | Top of canvas | Task type, patient name, key metric |
| **AI Summary** | Canvas | Initial synthesis of the situation |
| **Inline Visualizations** | Canvas | Charts, tables rendered within conversation |
| **Conversation Thread** | Canvas | Ongoing dialogue about this task |
| **Input + Quick Actions** | Bottom of canvas | Continue conversation or take action |
| **Patient Header** | Top of sidebar | Photo, name, demographics |
| **Relevant Data Panels** | Sidebar | Meds, labs, allergies — filtered to relevance |
| **Sidebar Quick Actions** | Sidebar | Order, Message, Refer buttons |
| **Task Controls** | Bottom of both | Complete, Pause, Document, Full Chart |

#### Quick Action Pills

The pills below the input are **dynamically surfaced** by the context engine based on:
- Task type
- AI analysis findings
- Patient state
- Available actions

```typescript
// Example: Context engine surfaces quick actions
function surfaceQuickActions(context: TaskContext): QuickAction[] {
  const actions: QuickAction[] = [];

  // Based on critical finding about K+-sparing meds
  if (context.aiFindings.includes("k_sparing_medication_risk")) {
    actions.push({ label: "Hold spironolactone", type: "order" });
  }

  // Standard actions for critical lab review
  if (context.taskType === "critical_lab_review") {
    actions.push({ label: "Repeat K+ stat", type: "order" });
    actions.push({ label: "Call patient", type: "communicate" });
  }

  return actions.slice(0, 4); // Max 4 pills
}
```

---

### Experience 3: Session Inventory

When a task is paused (via `Esc` or interruption), sessions are preserved for later resumption.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  PAUSED SESSIONS                                                [X Close]   │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 🚨 Robert Chen - Critical Lab Review                    [10 min ago]  │ │
│  │    K+ 6.2 mEq/L • Last: "What's his kidney trajectory?"               │ │
│  │    [Resume]                                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ 💬 Sarah Williams - Message Response                    [25 min ago]  │ │
│  │    Medication refill request • Draft response ready                   │ │
│  │    [Resume]                                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ─────────────────────────────────────────────────────────────────────────   │
│  [Tab] to select • [Enter] to resume • [Esc] to return to hub               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

Accessible via:
- Keyboard shortcut (e.g., `Cmd+Shift+S`)
- Sidebar indicator showing count of paused sessions
- Menu option

---

### Experience 4: Full Chart View

The "escape hatch" to traditional EHR-style views. Accessible from any task via "Expand full chart →".

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CruxMD    ← Back to Task                               [Dr. Neumann ▼]     │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  👤 ROBERT CHEN                                                              │
│  67-year-old male │ DOB: 03/15/1958 │ MRN: 123456                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ [Overview] [Medications] [Labs] [Problems] [Notes] [Timeline]        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                              │
│  ACTIVE MEDICATIONS (4)                                                      │
│  ─────────────────────────────────────────────────────────────────────────   │
│  │ Medication              │ Dose           │ Frequency    │ Start     │   │
│  ├─────────────────────────┼────────────────┼──────────────┼───────────┤   │
│  │ Lisinopril              │ 20 mg          │ Daily        │ 2020-03   │   │
│  │ Spironolactone          │ 25 mg          │ Daily        │ 2024-08   │   │
│  │ Metformin               │ 1000 mg        │ BID          │ 2019-01   │   │
│  │ Atorvastatin            │ 40 mg          │ Daily        │ 2020-03   │   │
│  ─────────────────────────────────────────────────────────────────────────   │
│                                                                              │
│  [+ Add Medication]                                                          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

This view provides:
- Complete, unfiltered data
- Traditional tabbed navigation
- Full CRUD operations
- The familiar EHR mental model

---

## Navigation & Keyboard Model

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Pause current task, return to hub (or close modal) |
| `Cmd+K` / `Ctrl+K` | Open command palette / quick search |
| `Cmd+Shift+S` | Open session inventory |
| `Cmd+Shift+D` | Mark current task as done |
| `Tab` | Navigate between focusable elements |
| `Shift+Tab` | Navigate backwards |
| `Enter` | Engage selected item |
| `/` | Focus the chat input |

### Task Queue Navigation

| Shortcut | Action |
|----------|--------|
| `↑` / `↓` | Move between tasks in current category |
| `←` / `→` | Move between categories |
| `Enter` | Engage selected task |
| `Space` | Expand/collapse category |

### Chat Input

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line |
| `↑` | Edit last message (if input empty) |
| `Cmd+Enter` | Send and mark task complete |

### Quick Action Pills

| Shortcut | Action |
|----------|--------|
| `1-4` | Trigger quick action by position (when input focused) |
| `Tab` | Move focus to pills |
| `Enter` | Activate focused pill |

---

## Task Model

### Task Schema

Based on FHIR Task resource with CruxMD extensions for AI provenance and dynamic context.

```typescript
interface CruxTask {
  // === Identity ===
  id: string;                           // UUID
  identifier?: Identifier[];            // Business identifiers

  // === Classification ===
  type: TaskType;
  code: CodeableConcept;                // What the task is
  category: TaskCategory;               // Critical, Routine, Schedule, Research

  // === Status ===
  status: TaskStatus;
  statusReason?: CodeableConcept;

  // === Priority ===
  priority: "routine" | "urgent" | "asap" | "stat";
  priorityScore?: number;               // 0-100 computed ranking

  // === Content ===
  title: string;                        // <140 chars
  description?: string;                 // Markdown

  // === Timing ===
  createdAt: datetime;
  modifiedAt: datetime;
  dueOn?: date;

  // === References ===
  for: Reference<Patient>;              // Required
  encounter?: Reference<Encounter>;
  focus?: Reference;                    // Resource being acted on
  basedOn?: Reference[];                // Triggering authorization

  // === CruxMD Extensions ===
  provenance?: AITaskProvenance;        // AI reasoning and evidence
  context?: TaskContextConfig;          // What to show in sidebar
  sessionId?: string;                   // Links to conversation

  // === Delegation (Future) ===
  delegation?: {
    agent: string;                      // Which agent prepared this
    workProduct?: AgentWorkProduct;     // Draft response, analysis, etc.
    requiresApproval: boolean;
    approvalType: "provider" | "staff";
  };
}

type TaskType =
  | "critical_lab_review"
  | "abnormal_result"
  | "hospitalization_alert"
  | "patient_message"
  | "external_result"
  | "pre_visit_prep"
  | "follow_up"
  | "appointment"
  | "research_review"
  | "order_signature"
  | "custom";

type TaskCategory = "critical" | "routine" | "schedule" | "research";

type TaskStatus =
  | "pending"           // Not yet started
  | "in_progress"       // Currently being worked
  | "paused"            // Interrupted, preserved for later
  | "completed"         // Successfully finished
  | "cancelled"         // Aborted
  | "deferred";         // Pushed to later
```

### AI Task Provenance

Every AI-generated or AI-augmented task preserves its reasoning chain:

```typescript
interface AITaskProvenance {
  // What triggered this task
  trigger: {
    type: "care_gap" | "clinical_rule" | "user_query" | "scheduled" | "agent_observation";
    sourceData: Reference[];            // FHIR resources that triggered
    query?: string;                     // If from user question
    ruleId?: string;                    // If from clinical rule
  };

  // AI reasoning
  reasoning: {
    model: string;                      // "gpt-4o"
    timestamp: datetime;
    confidence?: number;                // 0-1
    chainOfThought?: string;            // Reasoning if we want to show it
    citations: Citation[];              // Evidence links
  };

  // Supporting evidence
  evidence: {
    supportingFacts: Reference[];       // Conditions, Observations
    guidelines?: ExternalReference[];   // Clinical guidelines
  };

  // User disposition
  disposition: {
    status: "pending" | "accepted" | "modified" | "rejected" | "deferred";
    modifiedAt?: datetime;
    modifiedBy?: Reference;
    rejectionReason?: CodeableConcept;
    feedback?: string;
  };
}
```

### Task Context Configuration

Defines what appears in the sidebar for each task type:

```typescript
interface TaskContextConfig {
  panels: ContextPanel[];
  actions: ContextAction[];
}

interface ContextPanel {
  id: string;
  component: "PatientHeader" | "MedList" | "LabPanel" | "Allergies" |
             "ProblemList" | "RecentNotes" | "MessageThread" | "CareGaps";
  props?: Record<string, any>;
  filter?: string;                      // Filter to relevant data
  priority: number;                     // Display order
  collapsible: boolean;
  defaultExpanded: boolean;
}

interface ContextAction {
  label: string;
  type: "order" | "message" | "refer" | "document" | "navigate";
  requiresApproval: boolean;
}
```

### Task Type Configurations

```typescript
const TASK_TYPE_CONFIGS: Record<TaskType, TaskContextConfig> = {
  critical_lab_review: {
    panels: [
      { id: "header", component: "PatientHeader", priority: 1, collapsible: false, defaultExpanded: true },
      { id: "meds", component: "MedList", filter: "relevant_to_lab", priority: 2, collapsible: true, defaultExpanded: true },
      { id: "labs", component: "LabPanel", filter: "related_labs", priority: 3, collapsible: true, defaultExpanded: true },
      { id: "allergies", component: "Allergies", priority: 4, collapsible: true, defaultExpanded: false },
    ],
    actions: [
      { label: "Order", type: "order", requiresApproval: false },
      { label: "Message patient", type: "message", requiresApproval: false },
      { label: "Refer", type: "refer", requiresApproval: false },
    ]
  },

  patient_message: {
    panels: [
      { id: "header", component: "PatientHeader", priority: 1, collapsible: false, defaultExpanded: true },
      { id: "thread", component: "MessageThread", priority: 2, collapsible: false, defaultExpanded: true },
      { id: "context", component: "AIContextSummary", priority: 3, collapsible: true, defaultExpanded: true },
    ],
    actions: [
      { label: "Send response", type: "message", requiresApproval: true },
      { label: "Schedule follow-up", type: "order", requiresApproval: false },
    ]
  },

  pre_visit_prep: {
    panels: [
      { id: "header", component: "PatientHeader", priority: 1, collapsible: false, defaultExpanded: true },
      { id: "reason", component: "VisitContext", priority: 2, collapsible: false, defaultExpanded: true },
      { id: "problems", component: "ProblemList", filter: "active", priority: 3, collapsible: true, defaultExpanded: true },
      { id: "meds", component: "MedList", priority: 4, collapsible: true, defaultExpanded: true },
      { id: "gaps", component: "CareGaps", priority: 5, collapsible: true, defaultExpanded: true },
      { id: "notes", component: "RecentNotes", props: { limit: 3 }, priority: 6, collapsible: true, defaultExpanded: false },
    ],
    actions: [
      { label: "Pend order", type: "order", requiresApproval: false },
      { label: "Add to note", type: "document", requiresApproval: false },
    ]
  },

  // ... other task types
};
```

---

## Session Model

### Session Types

```typescript
interface Session {
  id: string;
  type: "orchestrating" | "patient_task";
  status: "active" | "paused" | "completed";

  // For patient_task sessions
  patientId?: string;
  taskId?: string;

  // Relationship to other sessions
  parentSessionId?: string;             // Orchestrating session that spawned this

  // Timing
  startedAt: datetime;
  lastActiveAt: datetime;
  completedAt?: datetime;

  // Content
  messages: Message[];
  summary?: string;                     // AI-generated summary for handoff
}
```

### Session Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SESSION LIFECYCLE                                  │
│                                                                             │
│   ORCHESTRATING SESSION (Day-level)                                         │
│   ─────────────────────────────────────────────────────────────────────     │
│   • Created on login / day start                                            │
│   • Manages daily tasks, panel queries, cross-patient work                  │
│   • Persists across patient task sessions                                   │
│                                                                             │
│        │                                                                    │
│        │ User engages task                                                  │
│        ▼                                                                    │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │  PATIENT TASK SESSION                                               │  │
│   │  ─────────────────────────────────────────────────────────────────  │  │
│   │  • Created when task engaged                                        │  │
│   │  • Scoped to specific patient + task                                │  │
│   │  • Links to parent orchestrating session                            │  │
│   │                                                                     │  │
│   │       │                    │                     │                  │  │
│   │       ▼                    ▼                     ▼                  │  │
│   │   [Complete]           [Pause]              [Interrupt]             │  │
│   │       │                    │                     │                  │  │
│   │       │                    │                     │                  │  │
│   │       ▼                    ▼                     ▼                  │  │
│   │   Session ends,       Session preserved,    Session preserved,      │  │
│   │   summary saved       can resume later      urgent task takes       │  │
│   │                                             priority                │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│        │                                                                    │
│        │ Returns to orchestrating session                                   │
│        ▼                                                                    │
│   ORCHESTRATING SESSION (continues)                                         │
│   "Task complete. Your next patient is..."                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Session Handoff

When transitioning between sessions, context is automatically passed:

```typescript
interface SessionHandoff {
  fromSession: string;
  toSession: string;
  handoffType: "task_engage" | "task_complete" | "task_pause" | "interrupt";

  // Context passed to new session
  context: {
    summary: string;                    // What was happening
    pendingQuestions?: string[];        // Unanswered questions
    relevantFindings?: string[];        // Key discoveries
    nextSuggestedAction?: string;       // What to do next
  };

  timestamp: datetime;
}
```

---

## Context Engine

The Context Engine is responsible for:
1. Determining what data is relevant to the current task
2. Surfacing appropriate quick actions
3. Configuring the sidebar content
4. Providing context to the AI for responses

### Context Assembly

```typescript
async function assembleTaskContext(
  task: CruxTask,
  lastAgentResponse?: AgentResponse
): Promise<TaskContext> {
  // Get base configuration for task type
  const config = TASK_TYPE_CONFIGS[task.type];

  // Fetch patient data
  const patient = await getPatient(task.for);

  // Apply filters to get relevant data
  const relevantMeds = await getMedications(patient.id, {
    filter: config.panels.find(p => p.id === "meds")?.filter
  });

  const relevantLabs = await getLabs(patient.id, {
    filter: config.panels.find(p => p.id === "labs")?.filter
  });

  // Surface quick actions based on context
  const quickActions = surfaceQuickActions({
    task,
    patient,
    meds: relevantMeds,
    labs: relevantLabs,
    lastAgentResponse
  });

  return {
    patient,
    panels: config.panels,
    data: { meds: relevantMeds, labs: relevantLabs, ... },
    quickActions,
    sidebarActions: config.actions
  };
}
```

### Quick Action Surfacing

```typescript
function surfaceQuickActions(context: {
  task: CruxTask;
  patient: Patient;
  meds: Medication[];
  labs: Observation[];
  lastAgentResponse?: AgentResponse;
}): QuickAction[] {
  const actions: QuickAction[] = [];

  // === Task-type defaults ===
  const defaults = QUICK_ACTION_DEFAULTS[context.task.type] || [];
  actions.push(...defaults);

  // === AI-driven suggestions ===
  if (context.lastAgentResponse?.insights) {
    for (const insight of context.lastAgentResponse.insights) {
      if (insight.type === "critical" && insight.suggestedAction) {
        actions.unshift({
          label: insight.suggestedAction.label,
          type: insight.suggestedAction.type,
          priority: 1,
          source: "ai_insight"
        });
      }
    }
  }

  // === Clinical rule triggers ===
  // e.g., If K+ critical and on K+-sparing med, suggest hold
  const criticalK = context.labs.find(l =>
    l.code === "K+" && l.interpretation === "critical"
  );
  const kSparingMeds = context.meds.filter(m =>
    K_SPARING_MEDS.includes(m.code)
  );

  if (criticalK && kSparingMeds.length > 0) {
    actions.unshift({
      label: `Hold ${kSparingMeds[0].name}`,
      type: "order",
      priority: 1,
      source: "clinical_rule"
    });
  }

  // Deduplicate and limit
  return deduplicateActions(actions).slice(0, 4);
}
```

---

## Component Specifications

### Canvas Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `ConversationalCanvas` | Main chat container | `sessionId`, `onSendMessage` |
| `MessageHistory` | Scrollable message list | `messages`, `isLoading` |
| `AgentMessage` | Renders AI response with rich content | `message: DisplayMessage` |
| `UserMessage` | Renders user message bubble | `message: DisplayMessage` |
| `ChatInput` | Text input with send button | `onSend`, `disabled`, `placeholder` |
| `QuickActionPills` | Contextual action buttons | `actions`, `onAction` |
| `ThinkingIndicator` | X logo animation during AI processing | `isThinking` |

### Sidebar Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `TaskQueueSidebar` | Task list by category (hub state) | `tasks`, `onSelectTask` |
| `TaskContextSidebar` | Patient context (engaged state) | `context: TaskContext` |
| `PatientHeader` | Photo, name, demographics | `patient: Patient` |
| `MedList` | Medication list with relevance highlighting | `meds`, `filter?` |
| `LabPanel` | Lab values with reference ranges | `labs`, `filter?` |
| `Allergies` | Allergy list | `allergies` |
| `ProblemList` | Active/historical conditions | `conditions`, `filter?` |
| `RecentNotes` | Recent clinical notes | `notes`, `limit?` |
| `MessageThread` | Patient message history | `messages` |
| `CareGaps` | Outstanding care gaps | `gaps` |

### Clinical Visualization Components

| Component | Purpose | Props |
|-----------|---------|-------|
| `LabTrendChart` | Line chart of lab values over time | `labCode`, `patientId`, `timeRange` |
| `VitalsGrid` | Grid of recent vital signs | `patientId` |
| `MedicationTimeline` | Timeline of medication changes | `patientId` |
| `InsightCard` | Highlighted clinical finding | `type`, `title`, `content`, `citations` |

### Shared Components

| Component | Purpose |
|-----------|---------|
| `BottomSheet` | Mobile slide-up panel |
| `CollapsiblePanel` | Expandable sidebar section |
| `Badge` | Status/priority indicators |
| `Skeleton` | Loading placeholder |

---

## Agent Delegation Model

> **Note:** This section describes the target architecture. For V2 demo, agent work products will be simulated in fixtures.

### The Vision

Specialized AI agents handle preliminary work that would traditionally require clinical staff:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AGENT DELEGATION HIERARCHY                           │
│                                                                             │
│    ┌─────────────────┐                                                      │
│    │    PROVIDER     │  Reviews, approves, exercises clinical judgment     │
│    │   (Human MD)    │  Only sees what needs their expertise/licensure     │
│    └────────┬────────┘                                                      │
│             │ supervises                                                    │
│             ▼                                                               │
│    ┌─────────────────────────────────────────────────────────────────┐     │
│    │                     AGENT ORCHESTRA                              │     │
│    │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │     │
│    │  │  Triage  │  │  Chart   │  │  Comms   │  │ Research │        │     │
│    │  │  Agent   │  │  Prep    │  │  Agent   │  │  Agent   │        │     │
│    │  │ (Nurse)  │  │ (MA)     │  │ (Staff)  │  │ (Fellow) │        │     │
│    │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │     │
│    │       │              │              │              │            │     │
│    │       ▼              ▼              ▼              ▼            │     │
│    │  Flags critical  Pre-visit    Drafts patient  Scans journals   │     │
│    │  results, sets   prep, order  messages,       Flags protocols  │     │
│    │  priority        suggestions  schedules f/u   Identifies pts   │     │
│    └─────────────────────────────────────────────────────────────────┘     │
│                                                                             │
│    Each agent action requiring provider approval becomes a TASK             │
│    with full provenance (who suggested, why, what evidence)                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agent Work Products

```typescript
interface AgentWorkProduct {
  type: "draft_message" | "order_suggestion" | "analysis" | "summary";
  content: any;                         // Type-specific content
  reasoning: string;                    // Why this was produced
  confidence: number;                   // 0-1
  requiresApproval: boolean;
  approvalType: "provider" | "staff" | "auto";
}

// Example: Draft message response
interface DraftMessageWorkProduct extends AgentWorkProduct {
  type: "draft_message";
  content: {
    subject?: string;
    body: string;
    tone: "clinical" | "empathetic" | "urgent";
  };
}

// Example: Order suggestion
interface OrderSuggestionWorkProduct extends AgentWorkProduct {
  type: "order_suggestion";
  content: {
    orderType: "lab" | "imaging" | "medication" | "referral";
    code: CodeableConcept;
    rationale: string;
    urgency: "routine" | "urgent" | "stat";
  };
}
```

### Implementation Phases

| Phase | Scope | Timeline |
|-------|-------|----------|
| **Phase 1 (V2 Demo)** | Mock agent work products in fixtures | Current |
| **Phase 2** | Implement synchronous task execution with user | Post-demo |
| **Phase 3** | Background agents preparing work asynchronously | Future |
| **Phase 4** | Full agent delegation with oversight workflows | Future |

---

## Data Requirements

### New Models Required

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `Appointment` | Schedule entries | `patientId`, `datetime`, `type`, `reason`, `status` |
| `Task` | Actionable work items | See Task Schema above |
| `Session` | Conversation threads | See Session Model above |
| `Message` | Chat messages | `sessionId`, `role`, `content`, `agentResponse?` |
| `PatientMessage` | Patient portal messages | `patientId`, `direction`, `content`, `status` |

### Demo Fixtures Required

| Fixture | Count | Notes |
|---------|-------|-------|
| Patients | 5-10 | Varied clinical scenarios |
| Appointments (today) | 8-12 | Mix of visit types |
| Appointments (tomorrow) | 4-6 | For "prepare for tomorrow" |
| Critical tasks | 3-5 | Lab alerts, discharges, findings |
| Routine tasks | 8-12 | Messages, results, follow-ups |
| Patient messages | 5-10 | Some with draft responses |
| Sample conversations | 3-5 | Demonstrating key workflows |

### Clinical Scenarios to Support

1. **Critical hyperkalemia** — K+ 6.2 on dual K+-sparing therapy, CKD
2. **Hospital discharge** — High-risk patient, care transition needs
3. **Abnormal imaging** — Incidental pulmonary nodule on CT
4. **Diabetes follow-up** — Improving A1c, medication adjustment
5. **Patient message** — Refill request with clinical nuance
6. **Pre-visit prep** — New patient with complex history

---

## Conflicts with Existing Plan

### 1. Single Page vs. Multiple Experiences

**Existing V2 Plan (cruxmd-v2-plan.md):**
> "No fixed pages or predefined navigation. The interface is a single, scrollable conversation."

**This Specification:**
Introduces distinct experiences (Hub, Task Engaged, Full Chart) with transforming sidebar.

**Resolution:** The conversational canvas remains the primary interaction surface, but we now explicitly support:
- A "hub" state with task queue
- Task-specific contexts with transformed sidebar
- An escape hatch to traditional EHR views

This is an evolution, not a contradiction. The canvas is still central; we've added structure around it.

### 2. Component Catalog Scope

**Existing V2 Plan:**
Lists these clinical components:
- InsightCard ✅
- LabResultsChart
- LabResultsTable
- MedicationList
- ConditionList
- VitalsChart
- Timeline
- ActionButton

**This Specification:**
Adds:
- PatientHeader
- MessageThread
- CareGaps
- VisitContext
- AIContextSummary
- QuickActionPills
- BottomSheet
- TaskQueueSidebar
- TaskContextSidebar

**Resolution:** Expand the component catalog. The new components support the richer UX model.

### 3. Task Model

**Existing V2 Plan:**
Does not define a Task model. Tasks are implicit in "what the agent suggests."

**This Specification:**
Introduces explicit Task model with:
- Categories (Critical, Routine, Schedule, Research)
- AI provenance
- Context configuration
- Session linkage

**Resolution:** Add Task as a new domain model. This is additive, not conflicting.

### 4. Session Persistence

**Existing V2 Plan:**
> "P3: Conversation persistence — Sessions stored and retrievable"

**This Specification:**
Elevates session management to core architecture:
- Orchestrating vs. patient sessions
- Session inventory for interrupted work
- Automatic handoff between sessions

**Resolution:** Promote session management from P3 to P1. It's foundational to the multi-task UX.

### 5. Navigation Model

**Existing V2 Plan:**
> "The 'navigation' happens through follow-up questions."

**This Specification:**
Adds explicit navigation:
- Task queue in sidebar
- Keyboard shortcuts (Tab, Enter, Esc)
- Quick action pills
- Session inventory

**Resolution:** Follow-up questions remain primary for within-task exploration. Explicit navigation is added for between-task movement.

### 6. CruxMD-cwf Task Scope

**Existing Task (Story 4.4):**
Build the conversational canvas with:
- AgentMessage, UserMessage, ChatInput
- FollowUpSuggestions, ThinkingIndicator
- MessageHistory, ConversationalCanvas
- Wire up to chat/page.tsx

**This Specification:**
Requires additional:
- TaskQueueSidebar (hub state)
- TaskContextSidebar (engaged state)
- QuickActionPills
- Session management
- Task model and fixtures

**Resolution:** CruxMD-cwf should be expanded or split into multiple tasks:
1. Core canvas components (original scope)
2. Sidebar system (task queue + context)
3. Task model and fixtures
4. Session management

---

## Implementation Priorities

### Phase 1: Foundation (Aligns with existing Epic 4)

1. **Core Canvas Components**
   - ConversationalCanvas
   - MessageHistory
   - AgentMessage / UserMessage
   - ChatInput
   - ThinkingIndicator (using X logo animation)

2. **Basic Sidebar**
   - Sidebar container with transform capability
   - PatientHeader component
   - MedList, LabPanel, Allergies components

3. **useChat Hook Enhancements**
   - Session tracking
   - Message persistence

### Phase 2: Task System

1. **Task Model**
   - Database schema
   - CRUD API endpoints
   - Task fixtures for demo

2. **Task Queue Sidebar**
   - Category display
   - Task cards
   - Keyboard navigation

3. **Task Context Sidebar**
   - Context configuration per task type
   - Dynamic panel loading
   - Quick actions

### Phase 3: Session Management

1. **Session Model**
   - Orchestrating vs. patient sessions
   - Session persistence
   - Handoff mechanism

2. **Session Inventory**
   - Paused session list
   - Resume functionality

### Phase 4: Polish & Mobile

1. **Responsive Layout**
   - Tablet sidebar collapse
   - Mobile bottom sheet

2. **Quick Action Pills**
   - Context engine integration
   - Dynamic surfacing

3. **Full Chart View**
   - Traditional EHR tabs
   - Complete data views

### Phase 5: Agent Delegation (Future)

1. **Agent work product rendering**
2. **Approval workflows**
3. **Background agent integration**

---

## Appendix: ASCII Diagram Reference

### Main Hub (Desktop)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CruxMD                                                    [Dr. Neumann ▼]  │
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │                       │
│                                                      │  📋 ACTION QUEUE      │
│     [X Logo]                                         │                       │
│                                                      │  🚨 Critical (3)      │
│     Good morning, Dr. Neumann                        │  ├─ K+ 6.2 - R. Chen  │
│                                                      │  ├─ Discharge - M. Jo │
│                                                      │  └─ CT finding - J. S │
│     ┌──────────────────────────────────────────┐    │                       │
│     │  How can I help you today?           [→] │    │  📬 Routine (12)      │
│     └──────────────────────────────────────────┘    │  ├─ 5 messages        │
│                                                      │  └─ 7 results         │
│     [Prepare for the day] [My next patient]         │                       │
│     [Panel overview]                                 │  📅 Schedule          │
│                                                      │  ├─ ▶ 9:00 S. Williams│
│                                                      │  ├─ 9:30 T. Brown     │
│                                                      │  └─ 10:00 A. Garcia   │
│                                                      │                       │
│                                                      │  📚 Learning (1)      │
│                                                      │  └─ GLP-1 update      │
│                                                      │                       │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

### Task Engaged (Desktop)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  CruxMD    ← Hub [Esc]                              [Dr. Neumann ▼]         │
├──────────────────────────────────────────────────────┬───────────────────────┤
│                                                      │                       │
│  🚨 Critical Lab: K+ 6.2 mEq/L                       │  👤 ROBERT CHEN       │
│  Robert Chen                                         │  67M │ MRN 123456     │
│  ─────────────────────────────────────────────────   │                       │
│                                                      │  ─────────────────    │
│  [AI Summary]                                        │                       │
│  Robert's potassium is critically elevated...        │  RELEVANT MEDS        │
│                                                      │  • Lisinopril 20mg    │
│  ┌─────────────────────────────────────────────┐    │  • Spironolactone 25mg│
│  │ [Chart: K+ trend with reference range]      │    │                       │
│  └─────────────────────────────────────────────┘    │  ─────────────────    │
│                                                      │                       │
│  You: What's his kidney trajectory?                  │  LABS                 │
│                                                      │  K+   6.2 H ⚠️       │
│  AI: Creatinine rising steadily...                   │  Cr   1.8            │
│                                                      │                       │
│  ┌──────────────────────────────────────────────┐   │  ─────────────────    │
│  │  Ask about this patient...               [→] │   │  [✓ Complete task]    │
│  └──────────────────────────────────────────────┘   │  [Expand full chart →]│
│  [Hold spironolactone] [Repeat K+ stat] [Call pt]   │                       │
│                                                      │                       │
└──────────────────────────────────────────────────────┴───────────────────────┘
```

### Mobile with Bottom Sheet

```
┌─────────────────────────────────────┐
│  CruxMD                       [≡]  │
├─────────────────────────────────────┤
│                                     │
│  🚨 Critical Lab: K+ 6.2           │
│  Robert Chen                        │
│  ─────────────────────────────────  │
│                                     │
│  [AI Summary]                       │
│  Robert's potassium is critically   │
│  elevated at 6.2 mEq/L...          │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ Ask about this patient...   [→] ││
│  └─────────────────────────────────┘│
│  [Hold med] [Repeat K+] [Call]      │
│                                     │
├─────────────────────────────────────┤
│  ▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  │
│  👤 Robert Chen, 67M    K+ 6.2 ⚠️  │
│  [Pull up for full context]         │
└─────────────────────────────────────┘
```

---

*Specification authored: January 2026*
*Last updated: January 2026*
