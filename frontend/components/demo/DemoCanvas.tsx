"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useTheme } from "next-themes";
import Image from "next/image";
import Lottie from "lottie-react";
import {
  Brain,
  Check,
  FileText,
  Heart,
  Mic,
  Pill,
  Send,
  AlertCircle,
  ExternalLink,
  Stethoscope,
  User,
} from "lucide-react";
import { AgentMessage, ThinkingIndicator } from "@/components/canvas";
import { useTypewriter } from "./useTypewriter";
import { replaceDatePlaceholders } from "@/lib/utils";
import { loadLottieData, getLottieData, isLottieLoaded, subscribeLottieCache } from "@/lib/lottie-cache";
import type { DisplayMessage } from "@/hooks";
import { INTRO_PHASES, TRIAGE_PHASES } from "./useAutoplay";
import type { DemoScenario, DemoInteraction, DemoAction, DemoEpilogueCompletion } from "@/lib/demo-scenarios";
import type { ActionType } from "@/lib/types";

const PHASES_PER_INTERACTION = 5;

// Phase offsets within each interaction:
// 0 = user message appears
// 1 = thinking/reasoning
// 2 = narrative
// 3 = insights
// 4 = follow-ups + actions

// ─── Unified icon lookup ─────────────────────────────────────────────────────
// Single mapping for action icons - supports both type-based defaults and explicit overrides

type IconComponent = typeof Pill;

const ICON_MAP: Record<string, IconComponent> = {
  // Action type defaults
  order: Pill,
  refer: Stethoscope,
  document: FileText,
  alert: AlertCircle,
  link: ExternalLink,
  // Explicit icon overrides (scenario can specify these)
  heart: Heart,
  pill: Pill,
  stethoscope: Stethoscope,
  file: FileText,
};

function getActionIcon(action: DemoAction): IconComponent {
  // Prefer explicit icon override, then fall back to type-based lookup, then Send
  return (action.icon && ICON_MAP[action.icon]) || ICON_MAP[action.type] || Send;
}

const ACTION_COLORS: Record<ActionType, string> = {
  order: "text-foreground border-border bg-muted/50 hover:bg-muted",
  refer: "text-foreground border-border bg-muted/50 hover:bg-muted",
  document: "text-muted-foreground border-border bg-muted/50 hover:bg-muted",
  alert: "text-foreground border-border bg-muted/50 hover:bg-muted",
  link: "text-muted-foreground border-border bg-muted/50 hover:bg-muted",
};

function DemoActionButtons({
  actions,
  selectedLabels,
}: {
  actions: DemoAction[];
  selectedLabels?: string[];
}) {
  const selected = new Set(selectedLabels ?? []);
  return (
    <div className="mt-4">
      {/* Take action separator */}
      <div className="flex items-center gap-3 mb-3">
        <div className="h-px flex-1 bg-border/40" />
        <span className="text-xs font-medium text-muted-foreground/70 uppercase tracking-wider">
          Take action
        </span>
        <div className="h-px flex-1 bg-border/40" />
      </div>
      <div className="flex flex-wrap gap-2 mb-2">
        {actions.map((action, i) => {
          const Icon = getActionIcon(action);
          const isSelected = selected.has(action.label);
          const colors = isSelected
            ? "text-primary border-primary/30 bg-primary/10"
            : ACTION_COLORS[action.type] ?? ACTION_COLORS.document;
          return (
            <button
              key={i}
              className={`inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-lg border transition-colors cursor-default ${colors}`}
              tabIndex={-1}
              aria-disabled="true"
            >
              {isSelected ? <Check className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
              {action.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── Epilogue results list ───────────────────────────────────────────────────

interface EpilogueResultItem {
  completion: DemoEpilogueCompletion;
  isInProgress: boolean;
}

function DemoEpilogueResults({
  items,
  lottieData,
}: {
  items: EpilogueResultItem[];
  lottieData: object | null;
}) {
  return (
    <ul className="space-y-2 my-3">
      {items.map((item, i) => {
        const { completion, isInProgress } = item;
        const { type, activeLabel, result } = completion;

        // Determine icon based on type and state
        let icon: React.ReactNode;
        if (type === "human_queued") {
          // Human-queued always shows user icon
          icon = <User className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />;
        } else if (type === "agent_task" && isInProgress) {
          // Agent task in progress shows Crux spin
          icon = lottieData ? (
            <div className="h-4 w-4 shrink-0 mt-0.5">
              <Lottie animationData={lottieData} loop autoplay className="h-4 w-4" />
            </div>
          ) : (
            <div className="h-4 w-4 shrink-0 mt-0.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          );
        } else {
          // Instant or completed agent_task shows checkmark
          icon = <Check className="h-4 w-4 text-primary shrink-0 mt-0.5" />;
        }

        // Determine text based on state
        const rawText = type === "agent_task" && isInProgress && activeLabel ? activeLabel : result;
        const text = replaceDatePlaceholders(rawText);

        return (
          <li
            key={i}
            className="flex items-start gap-2 text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-1 duration-300"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            {icon}
            <span>{text}</span>
          </li>
        );
      })}
    </ul>
  );
}

// ─── Memory nudge ────────────────────────────────────────────────────────────

function DemoMemoryNudge({ text }: { text: string }) {
  return (
    <div className="animate-in fade-in slide-in-from-bottom-1 duration-500">
      {/* Subtle separator line */}
      <div className="border-t border-border/40 my-4" />
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Brain className="h-3.5 w-3.5 shrink-0" />
        <span>{text}</span>
      </div>
    </div>
  );
}

// ─── Typewriter user message ─────────────────────────────────────────────────

function DemoUserMessage({
  text,
  typing,
  onContentGrow,
}: {
  text: string;
  typing: boolean;
  onContentGrow?: () => void;
}) {
  const displayed = useTypewriter(text, typing, onContentGrow);
  const isActivelyTyping = typing && displayed.length < text.length;
  return (
    <div className="mb-8">
      <div className="flex justify-end">
        <div className="bg-muted rounded-2xl px-4 py-3 max-w-[80%] relative">
          {/* Invisible full text to reserve final bubble size */}
          <p className="text-foreground whitespace-pre-wrap invisible" aria-hidden="true">
            {text}
          </p>
          {/* Visible typewriter text overlaid at same position */}
          <p className="text-foreground whitespace-pre-wrap absolute inset-0 px-4 py-3">
            {displayed}
          </p>
          {/* Mic icon in lower right - pulses while typing, disappears when done */}
          {isActivelyTyping && (
            <Mic className="absolute bottom-2 right-2 h-3.5 w-3.5 text-muted-foreground/60 animate-pulse" />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Triage message (AI initiates) ──────────────────────────────────────────

const TRIAGE_STYLES = [
  "text-foreground text-sm leading-relaxed",
  "[&_p]:mb-3 [&_p:last-child]:mb-0",
  "[&_strong]:font-semibold",
].join(" ");

function DemoTriageMessage({
  text,
  typing,
  onContentGrow,
}: {
  text: string;
  typing: boolean;
  onContentGrow?: () => void;
}) {
  const displayed = useTypewriter(text, typing, onContentGrow, "stream");
  return (
    <div className="mb-6">
      <p className={TRIAGE_STYLES}>{displayed}</p>
    </div>
  );
}

// ─── Discriminated union for rendered items ─────────────────────────────────
// Each item type has only the properties it needs

interface BaseItem {
  key: string;
}

interface TriageItem extends BaseItem {
  type: "triage";
  triageText: string;
  typing: boolean;
}

interface UserItem extends BaseItem {
  type: "user";
  userText: string;
  typing: boolean;
}

interface ThinkingItem extends BaseItem {
  type: "thinking";
  reasoningText?: string;
}

interface AgentItem extends BaseItem {
  type: "agent";
  message: DisplayMessage;
}

interface ActionsItem extends BaseItem {
  type: "actions";
  actions: DemoAction[];
  selectedLabels?: string[];
}

interface EpilogueResultsItem extends BaseItem {
  type: "epilogue-results";
  epilogueItems: EpilogueResultItem[];
}

interface MemoryItem extends BaseItem {
  type: "memory";
  memoryText: string;
}

type RenderedItem =
  | TriageItem
  | UserItem
  | ThinkingItem
  | AgentItem
  | ActionsItem
  | EpilogueResultsItem
  | MemoryItem;

function interactionToItems(
  interaction: DemoInteraction,
  interactionIndex: number,
  localPhase: number,
): RenderedItem[] {
  const { userMessage, agentResponse } = interaction;
  const prefix = `demo-${interactionIndex}`;
  const items: RenderedItem[] = [];

  // Phase 0+: user message visible (typewriter only on phase 0)
  if (localPhase >= 0) {
    items.push({
      type: "user",
      key: `${prefix}-user`,
      userText: userMessage,
      typing: localPhase === 0,
    });
  }

  // Phase 1: thinking spinner
  if (localPhase === 1) {
    items.push({
      type: "thinking",
      key: `${prefix}-thinking`,
      reasoningText: agentResponse.reasoningText,
    });
  }

  // Phase 2+: narrative (and progressively insights + follow-ups)
  if (localPhase >= 2) {
    items.push({
      type: "agent",
      key: `${prefix}-agent`,
      message: {
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
          follow_ups: localPhase >= 4 ? agentResponse.followUps : [],
        },
      },
    });

    // Phase 4: show action buttons if present
    if (localPhase >= 4 && agentResponse.actions?.length) {
      items.push({
        type: "actions",
        key: `${prefix}-actions`,
        actions: agentResponse.actions,
      });
    }
  }

  return items;
}

function buildAllItems(
  scenario: DemoScenario,
  phase: number,
  completedAgentTasks: Set<string>,
): RenderedItem[] {
  const items: RenderedItem[] = [];

  // Triage message appears first (AI initiates the conversation)
  // It types during phase 0 (triage phase), then is static afterward
  if (phase >= 0 && scenario.triageMessage) {
    items.push({
      type: "triage",
      key: "triage-message",
      triageText: scenario.triageMessage,
      typing: phase < TRIAGE_PHASES,
    });
  }

  // Interactions start after triage phase completes
  const interactionPhase = phase - TRIAGE_PHASES;
  if (interactionPhase < 0) return items;

  const interactionPhases = scenario.interactions.length * PHASES_PER_INTERACTION;
  const epiloguePhase = interactionPhase - interactionPhases; // -1 or less = no epilogue yet
  const hasEpilogue = !!scenario.epilogue;
  const completions = scenario.epilogue?.completions ?? [];

  // Calculate how many actions are checked based on epilogue phase
  // Phase 0 = pause (no selections), Phase 1+ = one selection per phase
  const checkedCount = hasEpilogue ? Math.max(0, Math.min(epiloguePhase, completions.length)) : 0;
  const checkedLabels = completions.slice(0, checkedCount).map(c => c.label);

  // Build epilogue items with in-progress state for agent tasks
  const epilogueItems: EpilogueResultItem[] = completions.slice(0, checkedCount).map((completion) => ({
    completion,
    // Agent tasks start in progress until their animation completes
    isInProgress: completion.type === "agent_task" && !completedAgentTasks.has(completion.label),
  }));

  for (let i = 0; i < scenario.interactions.length; i++) {
    const interactionStart = i * PHASES_PER_INTERACTION;
    if (interactionPhase < interactionStart) break;

    const localPhase = Math.min(interactionPhase - interactionStart, PHASES_PER_INTERACTION - 1);
    const interactionItems = interactionToItems(scenario.interactions[i], i, localPhase);

    // If epilogue is active and this is the last interaction, mark checked actions
    if (hasEpilogue && epiloguePhase >= 0 && i === scenario.interactions.length - 1) {
      for (const item of interactionItems) {
        if (item.type === "actions") {
          item.selectedLabels = checkedLabels;
        }
      }
    }

    items.push(...interactionItems);
  }

  // Epilogue: show results list if any actions are checked
  if (hasEpilogue && epilogueItems.length > 0) {
    items.push({
      type: "epilogue-results",
      key: "epilogue-results",
      epilogueItems,
    });
  }

  // Memory shows after all actions are checked (epiloguePhase > completions.length because phase 0 is pause)
  if (hasEpilogue && epiloguePhase > completions.length) {
    items.push({
      type: "memory",
      key: "epilogue-memory",
      memoryText: scenario.epilogue!.memory,
    });
  }

  return items;
}

// ─── Component ──────────────────────────────────────────────────────────────

interface DemoCanvasProps {
  scenario: DemoScenario;
  phase: number;
  avatar?: string;
  onContentGrow?: () => void;
}

// Duration for agent task "working" animation before showing result
const AGENT_TASK_DURATION_MS = 5000;

export function DemoCanvas({ scenario, phase: rawPhase, avatar, onContentGrow }: DemoCanvasProps) {
  // Offset phase by intro phases so canvas interactions start at 0
  const phase = rawPhase - INTRO_PHASES;
  const { resolvedTheme } = useTheme();
  const [lottieLoaded, setLottieLoaded] = useState(isLottieLoaded());
  const [completedAgentTasks, setCompletedAgentTasks] = useState<Set<string>>(new Set());
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // Load Lottie data on mount (cached globally)
  useEffect(() => {
    loadLottieData();
    return subscribeLottieCache(() => setLottieLoaded(isLottieLoaded()));
  }, []);

  // Reset completed tasks when scenario changes
  useEffect(() => {
    setCompletedAgentTasks(new Set());
    timersRef.current.forEach((timer) => clearTimeout(timer));
    timersRef.current.clear();
  }, [scenario.id]);

  // Set up timers for agent_task items to transition from "in progress" to "completed"
  const completions = scenario.epilogue?.completions ?? [];
  const interactionPhases = scenario.interactions.length * PHASES_PER_INTERACTION;
  const interactionPhase = phase - TRIAGE_PHASES;
  const epiloguePhase = interactionPhase - interactionPhases;
  const checkedCount = Math.max(0, Math.min(epiloguePhase, completions.length));

  useEffect(() => {
    // Check each completion that's now visible
    for (let i = 0; i < checkedCount; i++) {
      const completion = completions[i];
      // Skip if stayInProgress is true - these never resolve
      if (completion.stayInProgress) continue;
      if (completion.type === "agent_task" && !completedAgentTasks.has(completion.label) && !timersRef.current.has(completion.label)) {
        // Start timer to complete this agent task
        const timer = setTimeout(() => {
          setCompletedAgentTasks((prev) => new Set([...prev, completion.label]));
          timersRef.current.delete(completion.label);
        }, AGENT_TASK_DURATION_MS);
        timersRef.current.set(completion.label, timer);
      }
    }

    // Cleanup timers on unmount
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer));
    };
  }, [checkedCount, completions, completedAgentTasks]);

  const lottieData = lottieLoaded
    ? getLottieData(resolvedTheme === "dark" ? "dark" : "light")
    : null;

  const items = useMemo(
    () => buildAllItems(scenario, phase, completedAgentTasks),
    [scenario, phase, completedAgentTasks],
  );

  if (items.length === 0) {
    return (
      <p className="text-muted-foreground text-center text-sm">
        Scroll to begin the demo&hellip;
      </p>
    );
  }

  return (
    <>
      {/* Patient header */}
      <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border/50">
        {avatar ? (
          <div className="h-10 w-10 rounded-full overflow-hidden ring-1 ring-border/30">
            <Image
              src={avatar}
              alt={scenario.patient}
              width={80}
              height={80}
              className="h-full w-full object-cover"
              unoptimized
            />
          </div>
        ) : (
          <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center ring-1 ring-border/30">
            <span className="text-sm text-muted-foreground">
              {scenario.patient.charAt(0)}
            </span>
          </div>
        )}
        <div>
          <p className="text-sm font-medium text-foreground">{scenario.patient}</p>
          <p className="text-xs text-muted-foreground">{scenario.subtitle}</p>
        </div>
      </div>

      {items.map((item) => {
        switch (item.type) {
          case "triage":
            return (
              <DemoTriageMessage
                key={item.key}
                text={item.triageText}
                typing={item.typing}
                onContentGrow={onContentGrow}
              />
            );
          case "user":
            return (
              <DemoUserMessage
                key={item.key}
                text={item.userText}
                typing={item.typing}
                onContentGrow={onContentGrow}
              />
            );
          case "thinking":
            return (
              <ThinkingIndicator
                key={item.key}
                reasoningText={item.reasoningText}
                lottieData={lottieData}
              />
            );
          case "actions":
            return (
              <DemoActionButtons
                key={item.key}
                actions={item.actions}
                selectedLabels={item.selectedLabels}
              />
            );
          case "epilogue-results":
            return (
              <DemoEpilogueResults
                key={item.key}
                items={item.epilogueItems}
                lottieData={lottieData}
              />
            );
          case "memory":
            return <DemoMemoryNudge key={item.key} text={item.memoryText} />;
          case "agent":
            return (
              <AgentMessage
                key={item.key}
                message={item.message}
                onFollowUpSelect={() => {}}
                onContentGrow={onContentGrow}
                onRetry={() => {}}
              />
            );
        }
      })}
    </>
  );
}
