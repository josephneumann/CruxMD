"use client";

import { useRef } from "react";
import { useScrollPhase } from "./useScrollPhase";
import { UserMessage, AgentMessage } from "@/components/canvas";
import type { DisplayMessage } from "@/hooks";

// ---------------------------------------------------------------------------
// Mock data — Heart Failure interaction 1
// ---------------------------------------------------------------------------

const MOCK_USER: DisplayMessage = {
  id: "demo-u1",
  role: "user",
  content:
    "What medications is this patient currently taking? Are there any interactions I should be aware of?",
  timestamp: new Date("2026-01-30T09:15:00"),
};

const MOCK_AGENT: DisplayMessage = {
  id: "demo-a1",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:15:12"),
  streaming: {
    phase: "done",
    reasoningText:
      "**Reviewing medication list**\n\nCross-referencing active prescriptions with known interaction databases.",
    narrativeText: "",
    reasoningDurationMs: 8200,
    toolCalls: [],
  },
  agentResponse: {
    thinking:
      "**Reviewing medication list**\n\nCross-referencing active prescriptions with known interaction databases.",
    narrative:
      "The patient is currently taking **4 active medications**:\n\n1. **Lisinopril** 20mg daily — ACE inhibitor for hypertension\n2. **Metformin** 1000mg twice daily — Type 2 diabetes management\n3. **Spironolactone** 25mg daily — Aldosterone antagonist for heart failure\n4. **Atorvastatin** 40mg at bedtime — Cholesterol management\n\nI identified one significant interaction that warrants attention.",
    insights: [
      {
        type: "warning" as const,
        title: "Hyperkalemia Risk: Lisinopril + Spironolactone",
        content:
          "Both lisinopril (ACE inhibitor) and spironolactone (potassium-sparing diuretic) can independently raise serum potassium. Combined use increases the risk of hyperkalemia, especially given this patient's CKD stage 3.",
        citations: ["Basic Metabolic Panel (2026-01-15)", "Medication List (active)"],
      },
    ],
    follow_ups: [
      { question: "Show me the potassium trend over the last 6 months" },
      { question: "What monitoring schedule do you recommend?" },
    ],
  },
};

// ---------------------------------------------------------------------------
// Phase → visible content mapping (interaction 1: phases 0–4)
// ---------------------------------------------------------------------------

function buildMessages(phase: number): DisplayMessage[] {
  if (phase < 0) return [];

  const messages: DisplayMessage[] = [MOCK_USER];

  if (phase === 1) {
    messages.push({
      ...MOCK_AGENT,
      id: "demo-a1-thinking",
      streaming: {
        phase: "reasoning",
        reasoningText: MOCK_AGENT.streaming!.reasoningText,
        narrativeText: "",
        toolCalls: [],
      },
      agentResponse: undefined,
    });
  } else if (phase >= 2) {
    messages.push({
      ...MOCK_AGENT,
      agentResponse: {
        ...MOCK_AGENT.agentResponse!,
        insights: phase >= 3 ? MOCK_AGENT.agentResponse!.insights : [],
        follow_ups: phase >= 4 ? MOCK_AGENT.agentResponse!.follow_ups : [],
      },
    });
  }

  return messages;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DemoSection() {
  const scrollDriverRef = useRef<HTMLDivElement>(null);
  const { phase } = useScrollPhase(scrollDriverRef);
  const messages = buildMessages(phase);

  return (
    <section className="relative px-8 py-16 md:py-24">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
          See CruxMD in action
        </h2>

        {/* Scroll-driven layout */}
        <div ref={scrollDriverRef} className="relative flex gap-8" style={{ height: "600vh" }}>
          {/* Scroll driver (invisible — provides scroll height) */}
          <div className="w-[45%] shrink-0" aria-hidden="true" />

          {/* Sticky canvas */}
          <div
            className="w-[55%] shrink-0 sticky top-[80px] self-start"
            style={{ maxHeight: "calc(100vh - 100px)" }}
            role="region"
            aria-label="Interactive demo preview"
          >
            <div className="rounded-xl border border-border bg-background overflow-y-auto" style={{ maxHeight: "calc(100vh - 120px)" }}>
              <div className="max-w-3xl mx-auto px-4 pt-8 pb-8">
                {messages.length === 0 && (
                  <p className="text-muted-foreground text-center text-sm">
                    Scroll to begin the demo&hellip;
                  </p>
                )}
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
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
