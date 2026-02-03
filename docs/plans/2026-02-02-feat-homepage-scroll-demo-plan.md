---
title: "feat: Homepage Scroll-Triggered Conversational Canvas Demo"
type: feat
date: 2026-02-02
brainstorm: docs/brainstorms/2026-02-02-homepage-hero-demo-brainstorm.md
---

# feat: Homepage Scroll-Triggered Conversational Canvas Demo

## Overview

Build a scroll-triggered, scripted replay of the CruxMD conversational canvas on the homepage. Replaces the current features grid section with a sticky-canvas Apple-style layout where real chat components (AgentMessage, UserMessage, InsightCard, ThinkingIndicator, FollowUpSuggestions) play back pre-scripted clinical scenarios driven by scroll position. Four clinical scenarios accessible via tabs, each with 3 user→agent interactions.

## Problem Statement

The homepage describes CruxMD's capabilities with static feature cards. Visitors never see the core product experience — an LLM synthesizing scattered clinical data into actionable insights in real-time. A live demo showing real component animations (typewriter, reasoning, insight stagger) is far more compelling than bullet points.

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────┐
│  Homepage (page.tsx)                                │
│  ┌───────────────────────────────────────────────┐  │
│  │ Hero Section (unchanged)                      │  │
│  ├───────────────────────────────────────────────┤  │
│  │ Trust Bar (unchanged)                         │  │
│  ├───────────────────────────────────────────────┤  │
│  │ Problem/Solution (unchanged)                  │  │
│  ├───────────────────────────────────────────────┤  │
│  │ ┌─ DemoSection ────────────────────────────┐  │  │
│  │ │ ScenarioTabs [HF] [QT] [HCM] [Hypo]     │  │  │
│  │ │ ┌─────────────────┬────────────────────┐ │  │  │
│  │ │ │  Scroll Driver  │  Sticky Canvas     │ │  │  │
│  │ │ │  (tall div that │  ┌──────────────┐  │ │  │  │
│  │ │ │   drives scroll │  │ MessageList  │  │ │  │  │
│  │ │ │   progress)     │  │ UserMessage  │  │ │  │  │
│  │ │ │                 │  │ Thinking...  │  │ │  │  │
│  │ │ │  Progress       │  │ AgentMessage │  │ │  │  │
│  │ │ │  indicators     │  │  - narrative │  │ │  │  │
│  │ │ │  (optional)     │  │  - insights  │  │ │  │  │
│  │ │ │                 │  │  - followups │  │ │  │  │
│  │ │ │                 │  │ UserMessage  │  │ │  │  │
│  │ │ │                 │  │ ...          │  │ │  │  │
│  │ │ │                 │  └──────────────┘  │ │  │  │
│  │ │ └─────────────────┴────────────────────┘ │  │  │
│  │ └─────────────────────────────────────────────┘  │
│  ├───────────────────────────────────────────────┤  │
│  │ Testimonials (unchanged)                      │  │
│  ├───────────────────────────────────────────────┤  │
│  │ CTA + Footer (unchanged)                      │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Scroll Mechanics

**Scroll-to-phase mapping**: The DemoSection contains a tall scroll-driver div (height: ~6 viewport heights for 3 interactions). Scroll progress through this div is mapped to conversation phases:

Each interaction has 5 phases:
1. User message appears (fade-in)
2. ThinkingIndicator with reasoning text
3. Narrative typewriter effect
4. Insight cards stagger in
5. Follow-up suggestions appear

3 interactions × 5 phases = 15 scroll segments. Each segment = ~1/15 of total scroll height (~40vh per segment on desktop, ~6000px total scroll region).

**Implementation approach**: Use `IntersectionObserver` with threshold arrays on sentinel elements placed at each phase boundary within the scroll-driver div. Each sentinel triggers the corresponding conversation phase. No scroll event listeners needed — observers are performant and battery-friendly.

**Reverse scroll**: Conversation freezes on reverse scroll. Elements remain visible. Scrolling forward resumes from where it left off. No rewind animations — simpler, less confusing, and avoids uncanny valley.

**Interrupted animations**: If scroll advances past a phase while animation is playing, snap to completed state for that phase and begin next. Typewriter jumps to full text, thinking indicator resolves, insight cards appear immediately. Queue-based: each phase checks if previous phases are complete; if not, completes them instantly.

### Sticky Canvas

- Canvas sticks when demo section enters viewport (top of canvas hits `top: 80px` below nav)
- Canvas unsticks when bottom of scroll-driver approaches viewport bottom
- Use CSS `position: sticky` with `top: 80px` — no JS needed for the sticky behavior itself
- Canvas takes ~55% of width; scroll-driver takes ~45% (invisible but provides scroll height)

### Tab Switching

- Horizontal tab bar above the sticky region
- On switch: smooth-scroll to top of demo section, reset conversation state to phase 0, begin new scenario
- 300ms debounce on tab clicks to prevent rapid switching
- Active tab: bottom border accent + bold text + `aria-selected="true"`

### Mobile (< 768px)

- Disable sticky layout; canvas scrolls inline
- Conversation phases still scroll-triggered but with inline IntersectionObserver on each message block
- Tabs become horizontally scrollable pill bar
- Reduced scroll height (~4vh per segment instead of ~40vh)

### Accessibility

- `prefers-reduced-motion`: disable typewriter and stagger animations; content appears instantly per phase
- `aria-live="polite"` region for new messages
- Tab bar is `role="tablist"` with keyboard arrow navigation
- Skip link: "Skip demo" anchor to next section

### Data Structure

Scenario scripts defined as TypeScript constants reusing existing types:

```typescript
// frontend/lib/demo-scenarios.ts

interface DemoInteraction {
  userMessage: string;
  agentResponse: {
    reasoningText: string;           // Markdown for reasoning collapsible
    reasoningDurationMs: number;     // e.g. 8200
    narrative: string;               // Markdown for typewriter
    insights: Insight[];             // Existing Insight type
    followUps: FollowUp[];          // Existing FollowUp type
  };
}

interface DemoScenario {
  id: string;                        // e.g. "heart-failure"
  title: string;                     // Tab label: "Heart Failure"
  subtitle: string;                  // e.g. "Silent Progression"
  patient: string;                   // e.g. "Margaret Chen, 68F"
  interactions: [DemoInteraction, DemoInteraction, DemoInteraction];
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  heartFailureScenario,
  qtProlongationScenario,
  hcmScenario,
  hypoglycemiaScenario,
];
```

Each scenario's interactions map directly to `DisplayMessage` objects at render time. The existing design system mockup (`frontend/app/design/components/chat/page.tsx`) already demonstrates this pattern.

## Technical Approach

### New Files

| File | Purpose |
|------|---------|
| `frontend/components/demo/DemoSection.tsx` | Outer container: tabs + sticky layout + scroll driver |
| `frontend/components/demo/DemoCanvas.tsx` | The sticky chat canvas that renders messages based on scroll phase |
| `frontend/components/demo/ScenarioTabs.tsx` | Tab bar component |
| `frontend/components/demo/useScrollPhase.ts` | Hook: maps scroll position → current phase number |
| `frontend/lib/demo-scenarios.ts` | All 4 scenario scripts as typed constants |
| `frontend/lib/demo-scenarios/heart-failure.ts` | Heart failure scenario data |
| `frontend/lib/demo-scenarios/qt-prolongation.ts` | QT scenario data |
| `frontend/lib/demo-scenarios/hcm.ts` | HCM scenario data |
| `frontend/lib/demo-scenarios/hypoglycemia.ts` | Hypoglycemia scenario data |

### Modified Files

| File | Change |
|------|--------|
| `frontend/app/page.tsx` | Replace features grid section (~lines 119-195) with `<DemoSection />` |

### Component Reuse

These existing components are used as-is with no modifications:
- `AgentMessage` — pass `DisplayMessage` with `streaming.phase: "done"` for completed phases
- `UserMessage` — pass `DisplayMessage` with role "user"
- `InsightCard` — rendered by AgentMessage from `agentResponse.insights`
- `FollowUpSuggestions` — rendered by AgentMessage from `agentResponse.follow_ups`

`ThinkingIndicator` may need a minor prop adjustment — it currently expects Lottie refs. The demo can pass null for Lottie and rely on the text-only fallback mode.

### Key Hook: `useScrollPhase`

```typescript
function useScrollPhase(containerRef: RefObject<HTMLElement>): {
  phase: number;       // 0-14 (15 phases across 3 interactions)
  progress: number;    // 0-1 within current phase
}
```

Uses IntersectionObserver with sentinel divs placed at each phase boundary. Returns current phase number and sub-phase progress (useful for typewriter partial reveal).

### Rendering Logic

```typescript
// Pseudocode for DemoCanvas
function DemoCanvas({ scenario, phase }) {
  const messages: DisplayMessage[] = [];

  for (let i = 0; i < 3; i++) {
    const interactionStartPhase = i * 5;
    if (phase < interactionStartPhase) break;

    // Phase 0: User message
    if (phase >= interactionStartPhase) {
      messages.push(makeUserMessage(scenario.interactions[i]));
    }

    // Phase 1: Thinking indicator (handled by pending state)
    // Phase 2: Narrative (typewriter driven by progress)
    // Phase 3: Insights (stagger)
    // Phase 4: Follow-ups
    if (phase >= interactionStartPhase + 1) {
      messages.push(makeAgentMessage(scenario.interactions[i], {
        currentPhase: phase - interactionStartPhase,
        progress: subPhaseProgress,
      }));
    }
  }

  return <MessageList messages={messages} />;
}
```

## Acceptance Criteria

### Functional
- [ ] Features grid section replaced with scroll-triggered demo
- [ ] Sticky canvas layout works on desktop (≥768px)
- [ ] 4 scenario tabs switch correctly, resetting conversation state
- [ ] Each scenario plays 3 interactions with: user message → thinking → narrative → insights → follow-ups
- [ ] Scroll position drives phase progression forward
- [ ] Reverse scroll freezes conversation (no rewind)
- [ ] Typewriter effect plays during narrative phase
- [ ] Insight cards stagger in during insights phase
- [ ] Follow-up suggestions appear (non-interactive) during final phase
- [ ] Heart Failure scenario has full clinical content
- [ ] QT Prolongation scenario has full clinical content
- [ ] HCM scenario has full clinical content
- [ ] Hypoglycemia scenario has full clinical content

### Non-Functional
- [ ] No scroll jank — smooth 60fps during scroll-driven phases
- [ ] `prefers-reduced-motion` respected — animations disabled, content instant
- [ ] Keyboard accessible tab switching (arrow keys within tablist)
- [ ] Screen reader: aria-live announces new messages
- [ ] Mobile (< 768px): inline layout, no sticky, horizontally scrollable tabs
- [ ] No new runtime dependencies (use IntersectionObserver, CSS sticky)
- [ ] All scenario content is clinically accurate and sourced

### Quality Gates
- [ ] Tested in Chrome, Safari, Firefox on desktop
- [ ] Tested on iOS Safari and Android Chrome
- [ ] Lighthouse performance score ≥ 90 on homepage
- [ ] No layout shift (CLS) from demo section

## Implementation Phases

### Phase 1: Core Scroll Infrastructure
- `useScrollPhase` hook with IntersectionObserver
- `DemoSection` container with sticky layout + scroll driver
- `DemoCanvas` rendering messages from phase state
- Wire into `page.tsx` replacing features grid
- Single hardcoded test scenario (Heart Failure, interaction 1 only)

### Phase 2: Full Heart Failure Scenario
- Complete Heart Failure scenario data (all 3 interactions)
- Typewriter integration via phase progress
- Insight card stagger driven by phase
- Follow-up suggestions rendering
- ThinkingIndicator integration

### Phase 3: Scenario Tabs + Remaining Scenarios
- `ScenarioTabs` component with keyboard navigation
- Tab switching with scroll reset and state clear
- QT Prolongation scenario data
- HCM scenario data
- Hypoglycemia scenario data

### Phase 4: Mobile + Accessibility + Polish
- Mobile inline layout (< 768px)
- Horizontally scrollable tab pills on mobile
- `prefers-reduced-motion` support
- aria-live regions for messages
- Skip link past demo section
- Cross-browser testing and polish

## Dependencies & Risks

**Dependencies**: None — purely frontend, no backend changes, no new libraries.

**Risks**:
- **Scroll jank on Safari**: Safari handles `position: sticky` + IntersectionObserver differently. Mitigation: test early, fall back to simpler layout if needed.
- **Mobile scroll momentum**: Touch inertia may skip phases. Mitigation: larger phase thresholds on mobile; accept that fast scrolling may skip animations.
- **Clinical content accuracy**: Scenarios must be medically sound. Mitigation: content sourced from clinical research (see brainstorm); review by clinician recommended.
- **Component coupling**: Demo reuses production chat components; component changes could break demo. Mitigation: components are stable, well-typed, and the demo uses the same data shapes as production.

## References

### Internal
- Brainstorm: `docs/brainstorms/2026-02-02-homepage-hero-demo-brainstorm.md`
- Design system mockup pattern: `frontend/app/design/components/chat/page.tsx`
- Homepage features grid (replace target): `frontend/app/page.tsx:119-195`
- Type definitions: `frontend/lib/types.ts`
- Chat constants: `frontend/lib/constants/chat.ts`
- AgentMessage: `frontend/components/canvas/AgentMessage.tsx`
- UserMessage: `frontend/components/canvas/UserMessage.tsx`
- InsightCard: `frontend/components/clinical/InsightCard.tsx`
- ThinkingIndicator: `frontend/components/canvas/ThinkingIndicator.tsx`
- FollowUpSuggestions: `frontend/components/canvas/FollowUpSuggestions.tsx`
