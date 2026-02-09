"use client";

import { useState } from "react";
import Image from "next/image";
import { useTheme } from "next-themes";
import {
  Brain,
  Eye,
  Radio,
  ArrowRight,
  Pill,
  Stethoscope,
  Heart,
  FileText,
  Check,
  User,
} from "lucide-react";
import { UserMessage } from "@/components/canvas/UserMessage";
import { AgentMessage } from "@/components/canvas/AgentMessage";
import { ThinkingIndicator } from "@/components/canvas/ThinkingIndicator";
import { ChatInput } from "@/components/canvas/ChatInput";
import { FollowUpSuggestions } from "@/components/canvas/FollowUpSuggestions";
import { InsightCard } from "@/components/clinical/InsightCard";
import type { DisplayMessage } from "@/hooks";
import type { ModelId } from "@/lib/types";
import type { DemoActionType } from "@/lib/demo-scenarios";

// ---------------------------------------------------------------------------
// Heart Failure Scenario Mock Data
// Based on the Margaret Chen demo scenario: Silent HF Progression
// ---------------------------------------------------------------------------

const TRIAGE_MESSAGE = "Margaret Chen, 68F — HTN, T2DM, obesity. On your schedule this afternoon. Her furosemide has been uptitrated twice in 4 months (20 → 30 → 40 mg). Escalating diuretic requirement may indicate worsening fluid retention.";

const MOCK_USER_1: DisplayMessage = {
  id: "hf-u1",
  role: "user",
  content: "What's driving the diuretic escalation? Pull her recent trends.",
  timestamp: new Date("2026-01-30T09:15:00"),
};

const MOCK_AGENT_1: DisplayMessage = {
  id: "hf-a1",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:15:12"),
  streaming: {
    phase: "done",
    reasoningText: "Checking medication history, weight trends, and labs. Furosemide was added 4 months ago and uptitrated twice. Let me pull her weight, NT-proBNP, and any relevant visit notes to understand the underlying pattern.",
    narrativeText: "",
    reasoningDurationMs: 6400,
    toolCalls: [],
  },
  agentResponse: {
    thinking: "Checking medication history, weight trends, and labs. Furosemide was added 4 months ago and uptitrated twice. Let me pull her weight, NT-proBNP, and any relevant visit notes to understand the underlying pattern.",
    narrative: "**Active medications** — lisinopril 10 mg daily, metformin 1000 mg BID, atorvastatin 40 mg daily, and furosemide 40 mg daily.\n\nThe furosemide escalation pattern is concerning: **started at 20 mg just 4 months ago and already at 40 mg**. That kind of rapid uptitration suggests progressive fluid retention that's outpacing her current regimen.\n\nHer most recent labs show **NT-proBNP at 219 pg/mL** — technically within normal range, but I want to look at the trend. She also had a visit note from October mentioning fatigue.",
    insights: [
      {
        type: "warning",
        title: "Escalating diuretic requirement",
        content: "Furosemide dose doubled in 4 months (20 → 40 mg). Escalating loop diuretic need may indicate worsening fluid retention and should prompt evaluation for underlying cardiac dysfunction.",
        citations: ["Medication history — furosemide added 2025-09-14, uptitrated 2025-11-02, 2025-12-18"],
      },
    ],
    follow_ups: [
      { question: "What's the latest echocardiogram?" },
    ],
  },
};

const MOCK_USER_2: DisplayMessage = {
  id: "hf-u2",
  role: "user",
  content: "Pull her weight trend alongside the BNP — I want to see if the diuretic escalation correlates with fluid retention.",
  timestamp: new Date("2026-01-30T09:16:30"),
};

const MOCK_AGENT_2: DisplayMessage = {
  id: "hf-a2",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:16:38"),
  streaming: {
    phase: "done",
    reasoningText: "Looking at weight entries over the past 6 months and NT-proBNP results over the same period. Weight: 187 lbs in August → 191 in October → 195 in January — an 8-pound gain despite the patient reporting dietary efforts. NT-proBNP: 85 pg/mL in July, 142 in October, 219 in January.",
    narrativeText: "",
    reasoningDurationMs: 8200,
    toolCalls: [],
  },
  agentResponse: {
    thinking: "Looking at weight entries over the past 6 months and NT-proBNP results over the same period. Weight: 187 lbs in August → 191 in October → 195 in January — an 8-pound gain despite the patient reporting dietary efforts. NT-proBNP: 85 pg/mL in July, 142 in October, 219 in January.",
    narrative: "Two trends tell the story:\n\n**Weight** — up 8 lbs over 5 months (187 → 191 → 195 lbs) despite Margaret reporting she's been dieting. Fluid retention is the most likely driver given the concurrent diuretic escalation.\n\n**NT-proBNP** — trending upward: **85 → 142 → 219 pg/mL** over the last 6 months. Each individual value falls within the normal reference range for her age (< 300 pg/mL), which is why it wasn't flagged — but the **trajectory** tells a different story.\n\nBuried in recent visit notes:\n- **October** — fatigue, attributed to \"getting older\"\n- **December** — mild exertional dyspnea on stairs, charted as \"deconditioning\"\n\nThese symptoms were assessed independently and dismissed, but when combined with rising NT-proBNP, weight gain despite diuretics, and escalating furosemide — the pattern is consistent with **progression from Stage B to Stage C heart failure**.",
    insights: [
      {
        type: "critical",
        title: "Pattern consistent with Stage B → C heart failure progression",
        content: "NT-proBNP rising 85 → 142 → 219 pg/mL over 6 months, 8-lb weight gain despite diuretic therapy, escalating furosemide requirement, and symptoms (fatigue, exertional dyspnea) attributed to other causes. Individual data points appear normal — the trend is not.",
        citations: [
          "NT-proBNP — 85 pg/mL (2025-07-15), 142 pg/mL (2025-10-22), 219 pg/mL (2026-01-08)",
          "Weight — 187 lbs (2025-08-10), 191 lbs (2025-10-22), 195 lbs (2026-01-08)",
          "Visit note 2025-10-22 — \"Patient reports fatigue, likely age-related\"",
          "Visit note 2025-12-18 — \"Mild dyspnea on exertion, likely deconditioning\"",
        ],
      },
      {
        type: "info",
        title: "ACC/AHA guidelines recommend GDMT at this stage",
        content: "The 2022 AHA/ACC/HFSA guideline for heart failure management recommends initiating guideline-directed medical therapy (GDMT) — including neurohormonal blockade — upon recognition of Stage C HF, even when symptoms are mild.",
        citations: ["Heidenreich PA, et al. 2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure. Circulation. 2022;145(18):e895–e1032"],
      },
    ],
    follow_ups: [
      { question: "What's her full cardiac risk profile?" },
    ],
  },
};

const MOCK_USER_3: DisplayMessage = {
  id: "hf-u3",
  role: "user",
  content: "I'm thinking GDMT — walk me through initiation given her current regimen and the contraindication landscape.",
  timestamp: new Date("2026-01-30T09:18:00"),
};

const MOCK_AGENT_3: DisplayMessage = {
  id: "hf-a3",
  role: "assistant",
  content: "",
  timestamp: new Date("2026-01-30T09:18:15"),
  streaming: {
    phase: "done",
    reasoningText: "Reviewing Margaret's current regimen against heart failure GDMT recommendations. She's on lisinopril 10 mg — an ACE inhibitor, which is appropriate but under-dosed for HF (target 20-40 mg). She's not on a beta-blocker — needs one.",
    narrativeText: "",
    reasoningDurationMs: 7800,
    toolCalls: [],
  },
  agentResponse: {
    thinking: "Reviewing Margaret's current regimen against heart failure GDMT recommendations. She's on lisinopril 10 mg — an ACE inhibitor, which is appropriate but under-dosed for HF (target 20-40 mg). She's not on a beta-blocker — needs one.",
    narrative: "Here's a guideline-directed plan to initiate today and refine after imaging:\n\n**1. Optimize ACE inhibitor** — Uptitrate lisinopril from 10 mg to 20 mg daily (target 20–40 mg for HF). Monitor potassium and creatinine in 1–2 weeks.\n\n**2. Start beta-blocker** — Initiate carvedilol 3.125 mg BID. Low starting dose with gradual uptitration. Her resting HR of 78 and systolic BP in the 130s provide a comfortable margin.\n\n**3. Add SGLT2 inhibitor** — Empagliflozin 10 mg daily. Per 2022 AHA/ACC/HFSA guidelines, SGLT2 inhibitors are now recommended across the full spectrum of HF (both HFrEF and HFpEF) — no need to wait for echo results to start.\n\n**4. Order echocardiogram** — Essential to classify HF subtype (HFrEF vs HFpEF) and guide further optimization. If EF ≤ 40%, add mineralocorticoid receptor antagonist.\n\n**5. Close follow-up** — Schedule 2-week recheck with daily home weights. Instruct Margaret to call if weight increases > 2 lbs/day or > 5 lbs/week.",
    insights: [
      {
        type: "positive",
        title: "Early GDMT initiation reduces HF hospitalization risk by 30–40%",
        content: "Landmark trials (PARADIGM-HF, EMPEROR-Preserved, DAPA-HF) demonstrate that early initiation of guideline-directed medical therapy significantly reduces heart failure hospitalization and cardiovascular mortality. The greatest absolute benefit is seen when therapy starts before severe decompensation.",
        citations: [
          "McMurray JJV, et al. Angiotensin–Neprilysin Inhibition versus Enalapril in Heart Failure. N Engl J Med. 2014;371:993–1004",
          "Anker SD, et al. Empagliflozin in Heart Failure with a Preserved Ejection Fraction. N Engl J Med. 2021;385:1451–1461",
        ],
      },
      {
        type: "info",
        title: "Empagliflozin — dual cardiac and renal benefit",
        content: "For Margaret, empagliflozin addresses two problems with one medication: SGLT2 inhibitors improve heart failure outcomes independent of diabetes status, while also providing glycemic control and renal protection (demonstrated eGFR preservation in EMPA-KIDNEY).",
        citations: ["The EMPA-KIDNEY Collaborative Group. Empagliflozin in Patients with Chronic Kidney Disease. N Engl J Med. 2023;388:117–127"],
      },
    ],
    follow_ups: [
      { question: "Draft the cardiology referral" },
      { question: "What monitoring parameters should I track?" },
    ],
  },
};

const MOCK_MESSAGES: DisplayMessage[] = [MOCK_USER_1, MOCK_AGENT_1, MOCK_USER_2, MOCK_AGENT_2, MOCK_USER_3, MOCK_AGENT_3];

// ---------------------------------------------------------------------------
// Action Button Types
// ---------------------------------------------------------------------------

interface DemoAction {
  label: string;
  type: DemoActionType;
  icon?: string;
}

const DEMO_ACTIONS: DemoAction[] = [
  { label: "Prescribe carvedilol 3.125 mg BID", type: "order" },
  { label: "Uptitrate lisinopril to 20 mg", type: "order" },
  { label: "Refer to cardiology", type: "refer" },
  { label: "Order echocardiogram", type: "order", icon: "heart" },
];

const ACTION_ICONS: Record<string, typeof Pill> = {
  order: Pill,
  refer: Stethoscope,
  document: FileText,
  heart: Heart,
};

const ACTION_COLORS: Record<DemoActionType, string> = {
  order: "text-foreground border-border bg-muted/50 hover:bg-muted",
  refer: "text-foreground border-border bg-muted/50 hover:bg-muted",
  document: "text-muted-foreground border-border bg-muted/50 hover:bg-muted",
  alert: "text-foreground border-border bg-muted/50 hover:bg-muted",
  link: "text-muted-foreground border-border bg-muted/50 hover:bg-muted",
};

// ---------------------------------------------------------------------------
// Epilogue Completion States
// ---------------------------------------------------------------------------

interface CompletionItem {
  label: string;
  type: "instant" | "agent_task" | "human_queued";
  state: "pending" | "in_progress" | "completed";
  result?: string;
}

const EPILOGUE_COMPLETIONS: CompletionItem[] = [
  { label: "Prescribe carvedilol 3.125 mg BID", type: "instant", state: "completed", result: "Carvedilol 3.125 mg BID prescribed — sent to CVS Pharmacy" },
  { label: "Uptitrate lisinopril to 20 mg", type: "instant", state: "completed", result: "Lisinopril uptitrated to 20 mg — patient notified via portal" },
  { label: "Refer to cardiology", type: "agent_task", state: "in_progress", result: "Coordinating with cardiology..." },
  { label: "Order echocardiogram", type: "human_queued", state: "pending", result: "Follow-up appointment and echocardiogram queued for discussion and scheduling during today's visit" },
];

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ChatDesignPage() {
  const { resolvedTheme } = useTheme();
  const markSrc = resolvedTheme === "dark" ? "/brand/logos/mark-reversed.svg" : "/brand/logos/mark-primary.svg";

  // ChatInput demo state
  const [inputValue, setInputValue] = useState("");
  const [model, setModel] = useState<ModelId>("gpt-5-mini");
  const [reasoningBoost, setReasoningBoost] = useState(false);
  const [selectedActions, setSelectedActions] = useState<Set<string>>(new Set(["Prescribe carvedilol 3.125 mg BID", "Uptitrate lisinopril to 20 mg"]));

  const toggleAction = (label: string) => {
    setSelectedActions((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

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
          A complete clinical workflow showing the heart failure progression detection scenario.
          The agent synthesizes scattered data — trending biomarkers, weight changes, escalating
          medications, and buried symptoms — to identify early-stage heart failure that no
          single data point would flag alone.
        </p>
        <div className="rounded-xl border border-border bg-background overflow-hidden">
          <div className="max-w-3xl mx-auto px-4 pt-8 pb-8">
            {/* Patient Header */}
            <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border/50">
              <div className="h-10 w-10 rounded-full overflow-hidden ring-1 ring-border/30">
                <Image
                  src="/brand/demo/patient-margaret-chen.png"
                  alt="Margaret Chen"
                  width={80}
                  height={80}
                  className="h-full w-full object-cover"
                  unoptimized
                />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Margaret Chen, 68F</p>
                <p className="text-xs text-muted-foreground">Silent Progression</p>
              </div>
            </div>

            {/* Triage Message */}
            <div className="mb-6">
              <p className="text-foreground text-sm leading-relaxed">
                {TRIAGE_MESSAGE}
              </p>
            </div>

            {/* Conversation */}
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

      {/* Triage/Seeding Message */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Triage Message</h2>
        <p className="text-muted-foreground">
          The AI initiates the conversation with a contextual seeding message. This provides
          relevant patient context and highlights the reason for the interaction — setting
          up the clinical question before the user asks anything.
        </p>
        <div className="rounded-xl border border-border bg-background p-6">
          <div className="max-w-3xl mx-auto">
            <p className="text-foreground text-sm leading-relaxed">
              {TRIAGE_MESSAGE}
            </p>
          </div>
        </div>
        <div className="bg-muted/50 rounded-lg p-4 text-sm">
          <p className="font-medium mb-2">Design Notes:</p>
          <ul className="list-disc list-inside space-y-1 text-muted-foreground">
            <li>Renders with typewriter animation at AI streaming speed</li>
            <li>Left-aligned, plain text — no bubble styling</li>
            <li>Patient name bolded, key clinical flags highlighted</li>
            <li>Appears before user interaction begins</li>
          </ul>
        </div>
      </section>

      {/* Action Buttons */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Action Buttons</h2>
        <p className="text-muted-foreground">
          After the agent provides recommendations, action buttons allow one-click execution.
          Actions can be orders (prescriptions, labs), referrals, documentation, or alerts.
          Selected actions show a checkmark and primary color styling.
        </p>
        <div className="rounded-xl border border-border bg-background p-6">
          <div className="max-w-3xl mx-auto">
            {/* Take action separator */}
            <div className="flex items-center gap-3 mb-3">
              <div className="h-px flex-1 bg-border/40" />
              <span className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider">
                Take action
              </span>
              <div className="h-px flex-1 bg-border/40" />
            </div>
            <div className="flex flex-wrap gap-2 mb-2">
              {DEMO_ACTIONS.map((action) => {
                const IconComponent = action.icon ? ACTION_ICONS[action.icon] : ACTION_ICONS[action.type];
                const isSelected = selectedActions.has(action.label);
                const colors = isSelected
                  ? "text-primary border-primary/30 bg-primary/10"
                  : ACTION_COLORS[action.type];
                return (
                  <button
                    key={action.label}
                    onClick={() => toggleAction(action.label)}
                    className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors cursor-pointer ${colors}`}
                  >
                    {isSelected ? <Check className="h-3.5 w-3.5" /> : <IconComponent className="h-3.5 w-3.5" />}
                    {action.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          {[
            { type: "order", icon: Pill, desc: "Medications, labs, imaging" },
            { type: "refer", icon: Stethoscope, desc: "Specialist referrals" },
            { type: "document", icon: FileText, desc: "Notes, letters, forms" },
            { type: "heart", icon: Heart, desc: "Custom icon override" },
          ].map((item) => (
            <div key={item.type} className="rounded-lg border border-border p-3">
              <div className="flex items-center gap-2 font-medium">
                <item.icon className="h-4 w-4" />
                {item.type}
              </div>
              <div className="text-muted-foreground text-xs mt-1">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Epilogue Completion States */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Epilogue & Task Completion</h2>
        <p className="text-muted-foreground">
          After actions are selected, the epilogue shows completion states. Different action
          types have different completion behaviors: instant (immediate), agent tasks
          (async with spinner), and human-queued (deferred for manual handling).
        </p>
        <div className="rounded-xl border border-border bg-background p-6">
          <div className="max-w-3xl mx-auto">
            <ul className="space-y-2">
              {EPILOGUE_COMPLETIONS.map((item, i) => {
                let icon: React.ReactNode;
                if (item.type === "human_queued") {
                  icon = <User className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />;
                } else if (item.type === "agent_task" && item.state === "in_progress") {
                  icon = <div className="h-4 w-4 shrink-0 mt-0.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />;
                } else {
                  icon = <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />;
                }
                return (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-muted-foreground"
                  >
                    {icon}
                    <span>{item.result}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          {[
            { type: "instant", icon: Check, color: "text-primary", desc: "Completes immediately. Shows checkmark. Used for simple orders." },
            { type: "agent_task", icon: "spinner", color: "text-primary", desc: "Agent works asynchronously. Shows spinner, then checkmark when done." },
            { type: "human_queued", icon: User, color: "text-blue-500", desc: "Deferred to human. Shows user icon. Requires manual action." },
          ].map((item) => (
            <div key={item.type} className="rounded-lg border border-border p-3">
              <div className="flex items-center gap-2 font-medium">
                {item.icon === "spinner" ? (
                  <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                ) : (
                  <item.icon className={`h-4 w-4 ${item.color}`} />
                )}
                {item.type}
              </div>
              <div className="text-muted-foreground text-xs mt-1">{item.desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Memory Nudge */}
      <section className="space-y-6">
        <h2 className="text-2xl font-medium">Memory Nudge</h2>
        <p className="text-muted-foreground">
          After completing actions, the agent shows what it learned from the interaction.
          This builds trust by making the learning loop transparent.
        </p>
        <div className="rounded-xl border border-border bg-background p-6">
          <div className="max-w-3xl mx-auto">
            <div className="border-t border-border/40 pt-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Brain className="h-3.5 w-3.5 shrink-0" />
                <span>Learned: your diagnosis and treatment preferences for heart failure.</span>
              </div>
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
            reasoningBoost={reasoningBoost}
            onReasoningBoostChange={setReasoningBoost}
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
            Right-aligned bubble with muted background. In the demo, user messages have a
            typewriter effect with a pulsing microphone icon to simulate voice input.
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
                message={MOCK_AGENT_2}
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
                reasoningText="**Reviewing medication history**\n\nChecking furosemide uptitration timeline and correlating with weight trends and NT-proBNP values."
              />
            </div>
          </div>
        </div>

        {/* InsightCard */}
        <div className="space-y-4">
          <h3 className="text-xl font-medium">InsightCard</h3>
          <p className="text-sm text-muted-foreground">
            Collapsible severity cards with left accent bar. Four types: critical (red),
            warning (amber), info (blue), and positive (green). Click title or chevron to
            expand. Citations show the source documents that support the finding.
          </p>
          <div className="rounded-xl border border-border bg-background p-6">
            <div className="max-w-xl space-y-3">
              <InsightCard
                defaultExpanded
                insight={{
                  type: "critical",
                  title: "Pattern consistent with Stage B → C heart failure progression",
                  content: "NT-proBNP rising 85 → 142 → 219 pg/mL over 6 months, 8-lb weight gain despite diuretic therapy, escalating furosemide requirement.",
                  citations: ["NT-proBNP trend (Jul 2025 – Jan 2026)", "Weight trend", "Medication history"],
                }}
              />
              <InsightCard
                insight={{
                  type: "warning",
                  title: "Escalating diuretic requirement",
                  content: "Furosemide dose doubled in 4 months (20 → 40 mg). May indicate worsening fluid retention.",
                  citations: ["Medication history — furosemide added 2025-09-14, uptitrated twice"],
                }}
              />
              <InsightCard
                insight={{
                  type: "positive",
                  title: "Early GDMT initiation reduces HF hospitalization risk by 30–40%",
                  content: "Landmark trials demonstrate that early guideline-directed therapy significantly reduces heart failure hospitalization and cardiovascular mortality.",
                  citations: ["PARADIGM-HF", "EMPEROR-Preserved", "DAPA-HF trials"],
                }}
              />
              <InsightCard
                insight={{
                  type: "info",
                  title: "ACC/AHA guidelines recommend GDMT at this stage",
                  content: "The 2022 AHA/ACC/HFSA guideline recommends initiating guideline-directed medical therapy upon recognition of Stage C HF.",
                  citations: ["Heidenreich PA, et al. Circulation. 2022"],
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
                  { question: "What's the latest echocardiogram?" },
                  { question: "What's her full cardiac risk profile?" },
                  { question: "Draft the cardiology referral" },
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
            feedback, and retry. Rendered as part of AgentMessage — shown in context above.
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
