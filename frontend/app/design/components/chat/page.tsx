"use client";

import { useState } from "react";
import Image from "next/image";
import { useTheme } from "next-themes";
import { Brain, Eye, Radio, ArrowRight } from "lucide-react";
import { UserMessage } from "@/components/canvas/UserMessage";
import { AgentMessage } from "@/components/canvas/AgentMessage";
import { ThinkingIndicator } from "@/components/canvas/ThinkingIndicator";
import { ChatInput } from "@/components/canvas/ChatInput";
import { FollowUpSuggestions } from "@/components/canvas/FollowUpSuggestions";
import { InsightCard } from "@/components/clinical/InsightCard";
import type { DisplayMessage } from "@/hooks";
import type { ModelId, ReasoningEffort } from "@/lib/types";

// ---------------------------------------------------------------------------
// Mock Data
// ---------------------------------------------------------------------------

const MOCK_USER_1: DisplayMessage = {
  id: "u1",
  role: "user",
  content: "What medications is this patient currently taking? Are there any interactions I should be aware of?",
  timestamp: new Date("2026-01-30T09:15:00"),
};

const MOCK_AGENT_1: DisplayMessage = {
  id: "a1",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:15:12"),
  streaming: { phase: "done", reasoningText: "**Reviewing medication list**\n\nI need to check the patient's active medications and cross-reference for known drug interactions.\n\n**Cross-referencing interactions**\n\nLisinopril + Spironolactone can both increase potassium. Combined with the patient's CKD stage 3, this creates a significant hyperkalemia risk.", narrativeText: "", reasoningDurationMs: 8200 },
  agentResponse: {
    thinking: "**Reviewing medication list**\n\nI need to check the patient's active medications and cross-reference for known drug interactions.\n\n**Cross-referencing interactions**\n\nLisinopril + Spironolactone can both increase potassium. Combined with the patient's CKD stage 3, this creates a significant hyperkalemia risk.",
    narrative: "The patient is currently taking **4 active medications**:\n\n1. **Lisinopril** 20mg daily — ACE inhibitor for hypertension\n2. **Metformin** 1000mg twice daily — Type 2 diabetes management\n3. **Spironolactone** 25mg daily — Aldosterone antagonist for heart failure\n4. **Atorvastatin** 40mg at bedtime — Cholesterol management\n\nI identified one significant interaction that warrants attention.",
    insights: [
      {
        type: "warning",
        title: "Hyperkalemia Risk: Lisinopril + Spironolactone",
        content: "Both lisinopril (ACE inhibitor) and spironolactone (potassium-sparing diuretic) can independently raise serum potassium. Combined use increases the risk of hyperkalemia, especially given this patient's CKD stage 3. Last potassium was 4.8 mEq/L — within normal range but trending upward.",
        citations: ["Basic Metabolic Panel (2026-01-15)", "Medication List (active)"],
      },
      {
        type: "info",
        title: "Metformin Dose Appropriate for Renal Function",
        content: "Current eGFR of 42 mL/min supports continued metformin use at the current dose, though monitoring should continue. FDA guidance permits use down to eGFR 30.",
        citations: ["Basic Metabolic Panel (2026-01-15)", "FDA Drug Label"],
      },
    ],
    follow_ups: [
      { question: "Show me the potassium trend over the last 6 months" },
      { question: "What monitoring schedule do you recommend for this combination?" },
      { question: "Are there alternative medications with lower interaction risk?" },
    ],
  },
};

const MOCK_USER_2: DisplayMessage = {
  id: "u2",
  role: "user",
  content: "Show me the potassium trend over the last 6 months",
  timestamp: new Date("2026-01-30T09:16:30"),
};

const MOCK_AGENT_2: DisplayMessage = {
  id: "a2",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:16:38"),
  streaming: { phase: "done", reasoningText: "**Querying lab results**\n\nPulling potassium values from the last 6 months to assess trend direction.", narrativeText: "", reasoningDurationMs: 3400 },
  agentResponse: {
    thinking: "**Querying lab results**\n\nPulling potassium values from the last 6 months to assess trend direction.",
    narrative: "Here are the potassium levels over the last 6 months:\n\n| Date | K⁺ (mEq/L) | Status |\n|---|---|---|\n| 2025-07-20 | 4.2 | Normal |\n| 2025-09-14 | 4.4 | Normal |\n| 2025-11-03 | 4.6 | Normal |\n| 2026-01-15 | 4.8 | High-normal |\n\nThere is a **consistent upward trend** of approximately 0.1 mEq/L per month. While all values remain within the reference range (3.5–5.0), the trajectory warrants attention given the dual potassium-elevating medications.",
    insights: [
      {
        type: "critical",
        title: "Rising Potassium Trajectory",
        content: "At the current rate, potassium could exceed 5.0 mEq/L within 2 months. Consider more frequent monitoring (every 2–4 weeks) and dietary potassium counseling.",
        citations: ["Basic Metabolic Panel trend (Jul 2025 – Jan 2026)"],
      },
    ],
    follow_ups: [
      { question: "What dietary modifications would help manage potassium?" },
      { question: "Should we adjust the spironolactone dose?" },
    ],
  },
};

const MOCK_MESSAGES: DisplayMessage[] = [MOCK_USER_1, MOCK_AGENT_1, MOCK_USER_2, MOCK_AGENT_2];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChatDesignPage() {
  const { resolvedTheme } = useTheme();
  const markSrc = resolvedTheme === "dark" ? "/brand/mark-reversed.svg" : "/brand/mark-primary.svg";

  // ChatInput demo state
  const [inputValue, setInputValue] = useState("");
  const [model, setModel] = useState<ModelId>("gpt-5-mini");
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("medium");

  return (
    <div className="space-y-16">
      {/* Hero */}
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Conversational Canvas</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          The core experience of CruxMD. A single scrollable conversation where the LLM
          decides what to show — narrative, insights, data, and follow-ups — and the UI
          renders it progressively.
        </p>
      </div>

      {/* Full Conversation Mock */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Full Conversation</h2>
        <p className="text-muted-foreground">
          A complete conversation flow showing user messages, agent responses with reasoning,
          insights, and follow-up suggestions. All data is static — no backend required.
        </p>
        <div className="rounded-xl border border-border bg-background overflow-hidden">
          <div className="max-w-3xl mx-auto px-4 pt-8 pb-8">
            {MOCK_MESSAGES.map((message) =>
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
            {/* Static CruxMD mark */}
            <div className="flex justify-start mt-2 mb-4">
              <Image
                src={markSrc}
                alt=""
                width={28}
                height={28}
                className="opacity-40"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Input Toolbar */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Input Toolbar</h2>
        <p className="text-muted-foreground">
          The ChatInput component combines a resizable textarea with model selection,
          reasoning toggle, attachment button, and send action.
        </p>
        <div className="rounded-xl border border-border bg-background overflow-hidden">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={() => setInputValue("")}
            model={model}
            onModelChange={setModel}
            reasoningEffort={reasoningEffort}
            onReasoningEffortChange={setReasoningEffort}
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {[
            { label: "Plus button", desc: "Add files, connectors, and attachments" },
            { label: "Clock icon", desc: "Toggle extended thinking (reasoning effort)" },
            { label: "Model selector", desc: "Switch between GPT-5, GPT-5 mini, GPT-5 nano" },
            { label: "Send button", desc: "Submit message (disabled when empty or loading)" },
          ].map((item) => (
            <div key={item.label} className="rounded-lg border border-border p-3">
              <div className="font-medium">{item.label}</div>
              <div className="text-muted-foreground text-xs mt-1">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Component Breakdown */}
      <section className="space-y-12">
        <div className="space-y-4">
          <h2 className="text-2xl font-medium">Component Breakdown</h2>
          <p className="text-muted-foreground">
            Individual subcomponents that compose the conversational canvas.
          </p>
        </div>

        {/* UserMessage */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">UserMessage</h3>
          <p className="text-sm text-muted-foreground">
            Right-aligned bubble with muted background. Renders plain text with preserved whitespace.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-3xl mx-auto">
              <UserMessage message={MOCK_USER_1} />
            </div>
          </div>
        </div>

        {/* AgentMessage */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">AgentMessage</h3>
          <p className="text-sm text-muted-foreground">
            Full-width response containing reasoning toggle, markdown narrative, insight cards,
            message actions (copy, feedback, retry), and follow-up suggestions.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-3xl mx-auto">
              <AgentMessage
                message={MOCK_AGENT_1}
                onFollowUpSelect={() => {}}
                onContentGrow={() => {}}
                onRetry={() => {}}
              />
            </div>
          </div>
        </div>

        {/* ThinkingIndicator */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">ThinkingIndicator</h3>
          <p className="text-sm text-muted-foreground">
            Shown while the agent is streaming a response. Displays a Lottie spinner
            alongside the latest reasoning headline or a rotating thinking verb.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-3xl mx-auto">
              <ThinkingIndicator
                reasoningText="**Analyzing medication interactions**\n\nCross-referencing active prescriptions with known interaction databases."
              />
            </div>
          </div>
        </div>

        {/* InsightCard */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">InsightCard</h3>
          <p className="text-sm text-muted-foreground">
            Collapsible severity cards with left accent bar. Click title or chevron to
            expand. See also{" "}
            <a href="/design/components/alert" className="text-primary hover:underline">
              Alert
            </a>{" "}
            for the full color reference.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-xl space-y-3">
              <InsightCard
                defaultExpanded
                insight={{
                  type: "warning",
                  title: "Hyperkalemia Risk: Lisinopril + Spironolactone",
                  content: "Both medications can raise serum potassium. Combined use increases risk, especially with CKD stage 3.",
                  citations: ["Basic Metabolic Panel (2026-01-15)", "Medication List (active)"],
                }}
              />
              <InsightCard
                insight={{
                  type: "critical",
                  title: "Rising Potassium Trajectory",
                  content: "At the current rate, potassium could exceed 5.0 mEq/L within 2 months.",
                  citations: ["Basic Metabolic Panel trend (Jul 2025 – Jan 2026)"],
                }}
              />
              <InsightCard
                insight={{
                  type: "info",
                  title: "Metformin Dose Appropriate for Renal Function",
                  content: "Current eGFR of 42 mL/min supports continued metformin use at this dose.",
                  citations: ["Basic Metabolic Panel (2026-01-15)", "FDA Drug Label"],
                }}
              />
            </div>
          </div>
        </div>

        {/* FollowUpSuggestions */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">FollowUpSuggestions</h3>
          <p className="text-sm text-muted-foreground">
            Ghost buttons with chevron icons that continue the conversation. Clicking
            a suggestion sends it as the next user message.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-3xl mx-auto">
              <FollowUpSuggestions
                followUps={[
                  { question: "Show me the potassium trend over the last 6 months" },
                  { question: "What monitoring schedule do you recommend for this combination?" },
                  { question: "Are there alternative medications with lower interaction risk?" },
                ]}
                onSelect={() => {}}
              />
            </div>
          </div>
        </div>

        {/* MessageActions */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">MessageActions</h3>
          <p className="text-sm text-muted-foreground">
            Inline action bar below each agent message: copy to clipboard, thumbs up/down
            feedback, and retry. Rendered as part of AgentMessage — shown here
            in context above.
          </p>
        </div>
      </section>

      {/* Design Principles */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Design Principles</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            {
              icon: Brain,
              title: "LLM-first",
              description: "The agent decides what content to show — narrative, insights, tables, charts. The UI renders whatever the LLM returns, not predefined screens.",
            },
            {
              icon: Eye,
              title: "Progressive Disclosure",
              description: "Reasoning is collapsed behind a toggle. Insight cards start collapsed. Details emerge on demand, keeping the default view clean.",
            },
            {
              icon: Radio,
              title: "Streaming-native",
              description: "Responses stream in real-time: thinking indicator with reasoning headlines, typewriter narrative reveal, staggered insight card animation.",
            },
            {
              icon: ArrowRight,
              title: "Conversational Flow",
              description: "Follow-up suggestions keep the dialogue going. Each answer seeds the next question, enabling emergent navigation through patient data.",
            },
          ].map((principle) => (
            <div key={principle.title} className="rounded-xl border border-border p-5 space-y-2">
              <div className="flex items-center gap-2">
                <principle.icon className="h-5 w-5 text-primary" />
                <h3 className="font-medium">{principle.title}</h3>
              </div>
              <p className="text-sm text-muted-foreground">{principle.description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
