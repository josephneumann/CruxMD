/**
 * Shared types and barrel export for demo scenario scripts.
 *
 * Each scenario lives in its own file under demo-scenarios/ and is
 * re-exported here for consumption by the DemoSection component.
 */

import type { Insight, FollowUp } from "./types";

// ─── Types ───────────────────────────────────────────────────────────────────

export type DemoActionType = "order" | "refer" | "document" | "alert" | "link";

export interface DemoAction {
  label: string;
  type: DemoActionType;
  description?: string;
  icon?: "heart" | "pill" | "stethoscope" | "file" | "alert" | "link";
}

export interface DemoInteraction {
  userMessage: string;
  agentResponse: {
    reasoningText: string;
    reasoningDurationMs: number;
    narrative: string;
    insights: Insight[];
    followUps: FollowUp[];
    actions?: DemoAction[];
  };
}

/**
 * Epilogue completion types:
 * - instant: Simple orders that resolve immediately (prescriptions, flags)
 * - agent_task: Work requiring coordination (scheduling, referrals, records)
 * - human_queued: Sensitive interactions routed to staff (callbacks, difficult conversations)
 */
export type EpilogueCompletionType = "instant" | "agent_task" | "human_queued";

export interface DemoEpilogueCompletion {
  /** The action button label to check */
  label: string;
  /** Completion type determines animation behavior */
  type: EpilogueCompletionType;
  /** For agent_task: in-progress label (e.g., "Scheduling echocardiogram...") */
  activeLabel?: string;
  /** Result text to show when complete */
  result: string;
  /** If true, agent_task stays in progress indefinitely (never resolves) */
  stayInProgress?: boolean;
}

export interface DemoEpilogue {
  /** Array of action completions to animate sequentially */
  completions: DemoEpilogueCompletion[];
  /** Memory learning text shown at the very end */
  memory: string;
}

export interface DemoScenario {
  id: string;
  title: string;
  subtitle: string;
  patient: string;
  /** AI's initial triage message that introduces the patient and prompts investigation */
  triageMessage: string;
  interactions: [DemoInteraction, DemoInteraction, DemoInteraction];
  epilogue?: DemoEpilogue;
}

// ─── Scenario re-exports ─────────────────────────────────────────────────────

export { heartFailureScenario } from "./demo-scenarios/heart-failure";

export { qtProlongationScenario } from "./demo-scenarios/qt-prolongation";
export { hcmScenario } from "./demo-scenarios/hcm";
export { hypoglycemiaScenario } from "./demo-scenarios/hypoglycemia";
