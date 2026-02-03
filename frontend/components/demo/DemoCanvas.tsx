"use client";

import { useMemo } from "react";
import { UserMessage, AgentMessage } from "@/components/canvas";
import type { DisplayMessage } from "@/hooks";
import type { DemoScenario, DemoInteraction } from "@/lib/demo-scenarios";

const PHASES_PER_INTERACTION = 5;

// Phase offsets within each interaction:
// 0 = user message appears
// 1 = thinking/reasoning
// 2 = narrative
// 3 = insights
// 4 = follow-ups

/**
 * Maps a single DemoInteraction to DisplayMessage(s) based on the local phase
 * (0–4) within that interaction.
 */
function interactionToMessages(
  interaction: DemoInteraction,
  interactionIndex: number,
  localPhase: number,
): DisplayMessage[] {
  const { userMessage, agentResponse } = interaction;
  const prefix = `demo-${interactionIndex}`;
  const messages: DisplayMessage[] = [];

  // Phase 0+: user message visible
  if (localPhase >= 0) {
    messages.push({
      id: `${prefix}-user`,
      role: "user",
      content: userMessage,
      timestamp: new Date(),
    });
  }

  // Phase 1: thinking only
  if (localPhase === 1) {
    messages.push({
      id: `${prefix}-agent`,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      streaming: {
        phase: "reasoning",
        reasoningText: agentResponse.reasoningText,
        narrativeText: "",
        toolCalls: [],
      },
    });
  }

  // Phase 2+: narrative (and progressively insights + follow-ups)
  if (localPhase >= 2) {
    messages.push({
      id: `${prefix}-agent`,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      streaming: {
        phase: "done",
        reasoningText: agentResponse.reasoningText,
        reasoningDurationMs: agentResponse.reasoningDurationMs,
        narrativeText: "",
        toolCalls: [],
      },
      agentResponse: {
        thinking: agentResponse.reasoningText,
        narrative: agentResponse.narrative,
        insights: localPhase >= 3 ? agentResponse.insights : [],
        // Map camelCase followUps → snake_case follow_ups
        follow_ups: localPhase >= 4 ? agentResponse.followUps : [],
      },
    });
  }

  return messages;
}

/**
 * Builds the full DisplayMessage[] array from a scenario and global phase (0–14).
 *
 * For each interaction (0, 1, 2), we compute a local phase:
 * - If global phase hasn't reached this interaction yet → skip
 * - If global phase is past this interaction → show fully completed (localPhase = 4)
 * - If global phase is within this interaction → show partial
 */
function buildAllMessages(
  scenario: DemoScenario,
  phase: number,
): DisplayMessage[] {
  const messages: DisplayMessage[] = [];

  for (let i = 0; i < scenario.interactions.length; i++) {
    const interactionStart = i * PHASES_PER_INTERACTION;
    const interactionEnd = interactionStart + PHASES_PER_INTERACTION - 1;

    if (phase < interactionStart) break;

    // Snap completed interactions to final phase
    const localPhase = Math.min(phase - interactionStart, PHASES_PER_INTERACTION - 1);

    messages.push(
      ...interactionToMessages(scenario.interactions[i], i, localPhase),
    );
  }

  return messages;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface DemoCanvasProps {
  scenario: DemoScenario;
  phase: number;
}

export function DemoCanvas({ scenario, phase }: DemoCanvasProps) {
  const messages = useMemo(
    () => buildAllMessages(scenario, phase),
    [scenario, phase],
  );

  if (messages.length === 0) {
    return (
      <p className="text-muted-foreground text-center text-sm">
        Scroll to begin the demo&hellip;
      </p>
    );
  }

  return (
    <>
      {messages.map((message) =>
        message.role === "user" ? (
          <UserMessage key={message.id} message={message} />
        ) : (
          <AgentMessage
            key={message.id}
            message={message}
            onFollowUpSelect={() => {}}
            onContentGrow={() => {}}
            onRetry={() => {}}
          />
        ),
      )}
    </>
  );
}
