/**
 * Shared types and barrel export for demo scenario scripts.
 *
 * Each scenario lives in its own file under demo-scenarios/ and is
 * re-exported here for consumption by the DemoSection component.
 */

import type { Insight, FollowUp, ActionType } from "./types";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DemoAction {
  label: string;
  type: ActionType;
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

export interface DemoEpilogue {
  /** Which action button label triggers the epilogue (shown as "selected") */
  actionLabel: string;
  /** Confirmation text shown after the action is "placed" */
  confirmation: string;
  /** Memory learning text shown below the confirmation */
  memory: string;
}

export interface DemoScenario {
  id: string;
  title: string;
  subtitle: string;
  patient: string;
  interactions: [DemoInteraction, DemoInteraction, DemoInteraction];
  epilogue?: DemoEpilogue;
}

// ─── Scenario re-exports ─────────────────────────────────────────────────────

export { heartFailureScenario } from "./demo-scenarios/heart-failure";

export { qtProlongationScenario } from "./demo-scenarios/qt-prolongation";
export { hcmScenario } from "./demo-scenarios/hcm";
export { hypoglycemiaScenario } from "./demo-scenarios/hypoglycemia";
