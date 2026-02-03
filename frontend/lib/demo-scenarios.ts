/**
 * Shared types and barrel export for demo scenario scripts.
 *
 * Each scenario lives in its own file under demo-scenarios/ and is
 * re-exported here for consumption by the DemoSection component.
 */

import type { Insight, FollowUp } from "./types";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DemoInteraction {
  userMessage: string;
  agentResponse: {
    reasoningText: string;
    reasoningDurationMs: number;
    narrative: string;
    insights: Insight[];
    followUps: FollowUp[];
  };
}

export interface DemoScenario {
  id: string;
  title: string;
  subtitle: string;
  patient: string;
  interactions: [DemoInteraction, DemoInteraction, DemoInteraction];
}

// ─── Scenario re-exports ─────────────────────────────────────────────────────

export { heartFailureScenario } from "./demo-scenarios/heart-failure";

export { qtProlongationScenario } from "./demo-scenarios/qt-prolongation";
export { hcmScenario } from "./demo-scenarios/hcm";
export { hypoglycemiaScenario } from "./demo-scenarios/hypoglycemia";
