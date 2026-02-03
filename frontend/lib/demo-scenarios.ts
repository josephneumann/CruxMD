import type { Insight, FollowUp } from "./types";

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
