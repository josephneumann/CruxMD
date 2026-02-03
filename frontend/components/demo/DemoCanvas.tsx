"use client";

import { useEffect, useMemo, useState } from "react";
import { useTheme } from "next-themes";
import Image from "next/image";
import {
  Brain,
  Check,
  FileText,
  Heart,
  Pill,
  Send,
  AlertCircle,
  ExternalLink,
  Stethoscope,
} from "lucide-react";
import { AgentMessage, ThinkingIndicator } from "@/components/canvas";
import { useTypewriter } from "./useTypewriter";
import type { DisplayMessage } from "@/hooks";
import { INTRO_PHASES } from "./useAutoplay";
import type { DemoScenario, DemoInteraction, DemoAction, DemoEpilogue } from "@/lib/demo-scenarios";
import type { ActionType } from "@/lib/types";

const PHASES_PER_INTERACTION = 5;

// Phase offsets within each interaction:
// 0 = user message appears
// 1 = thinking/reasoning
// 2 = narrative
// 3 = insights
// 4 = follow-ups + actions

// ─── Action icon mapping ────────────────────────────────────────────────────

const ACTION_ICONS: Record<ActionType, typeof Pill> = {
  order: Pill,
  refer: Stethoscope,
  document: FileText,
  alert: AlertCircle,
  link: ExternalLink,
};

const ICON_OVERRIDES: Record<string, typeof Pill> = {
  heart: Heart,
  pill: Pill,
  stethoscope: Stethoscope,
  file: FileText,
  alert: AlertCircle,
  link: ExternalLink,
};

function getActionIcon(action: DemoAction): typeof Pill {
  if (action.icon && ICON_OVERRIDES[action.icon]) return ICON_OVERRIDES[action.icon];
  return ACTION_ICONS[action.type] ?? Send;
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
  selectedLabel,
}: {
  actions: DemoAction[];
  selectedLabel?: string;
}) {
  return (
    <div className="flex flex-wrap gap-2 mt-3 mb-2">
      {actions.map((action, i) => {
        const Icon = getActionIcon(action);
        const isSelected = selectedLabel === action.label;
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
  );
}

// ─── Memory nudge ────────────────────────────────────────────────────────────

function DemoMemoryNudge({ text }: { text: string }) {
  return (
    <div className="flex items-center gap-2 my-3 text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-1 duration-500">
      <Brain className="h-3.5 w-3.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

function DemoConfirmation({ text }: { text: string }) {
  return (
    <p className="my-3 text-sm text-muted-foreground animate-in fade-in slide-in-from-bottom-1 duration-300">
      {text}
    </p>
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
            {typing && displayed.length < text.length && (
              <span className="inline-block w-0.5 h-4 bg-foreground/60 align-text-bottom ml-0.5 animate-pulse" />
            )}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Message building ───────────────────────────────────────────────────────

interface RenderedItem {
  type: "user" | "agent" | "actions" | "thinking" | "memory" | "confirmation";
  key: string;
  message?: DisplayMessage;
  userText?: string;
  typing?: boolean;
  actions?: DemoAction[];
  selectedLabel?: string;
  reasoningText?: string;
  memoryText?: string;
  confirmationText?: string;
}

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
): RenderedItem[] {
  const items: RenderedItem[] = [];
  const interactionPhases = scenario.interactions.length * PHASES_PER_INTERACTION;
  const epiloguePhase = phase - interactionPhases; // -1 or less = no epilogue yet
  const hasEpilogue = !!scenario.epilogue;

  for (let i = 0; i < scenario.interactions.length; i++) {
    const interactionStart = i * PHASES_PER_INTERACTION;
    if (phase < interactionStart) break;

    const localPhase = Math.min(phase - interactionStart, PHASES_PER_INTERACTION - 1);
    const interactionItems = interactionToItems(scenario.interactions[i], i, localPhase);

    // If epilogue is active and this is the last interaction, mark the selected action
    if (hasEpilogue && epiloguePhase >= 0 && i === scenario.interactions.length - 1) {
      for (const item of interactionItems) {
        if (item.type === "actions") {
          item.selectedLabel = scenario.epilogue!.actionLabel;
        }
      }
    }

    items.push(...interactionItems);
  }

  // Epilogue phase 0: confirmation
  if (hasEpilogue && epiloguePhase >= 0) {
    items.push({
      type: "confirmation",
      key: "epilogue-confirmation",
      confirmationText: scenario.epilogue!.confirmation,
    });
  }

  // Epilogue phase 1: memory
  if (hasEpilogue && epiloguePhase >= 1) {
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

export function DemoCanvas({ scenario, phase: rawPhase, avatar, onContentGrow }: DemoCanvasProps) {
  // Offset phase by intro phases so canvas interactions start at 0
  const phase = rawPhase - INTRO_PHASES;
  const { resolvedTheme } = useTheme();
  const [lottieLight, setLottieLight] = useState<object | null>(null);
  const [lottieDark, setLottieDark] = useState<object | null>(null);

  useEffect(() => {
    fetch("/brand/crux-spin.json").then((r) => r.json()).then(setLottieLight).catch(() => {});
    fetch("/brand/crux-spin-reversed.json").then((r) => r.json()).then(setLottieDark).catch(() => {});
  }, []);

  const lottieData = resolvedTheme === "dark" ? lottieDark : lottieLight;

  const items = useMemo(
    () => buildAllItems(scenario, phase),
    [scenario, phase],
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
        if (item.type === "user") {
          return (
            <DemoUserMessage
              key={item.key}
              text={item.userText!}
              typing={item.typing!}
              onContentGrow={onContentGrow}
            />
          );
        }
        if (item.type === "thinking") {
          return (
            <ThinkingIndicator
              key={item.key}
              reasoningText={item.reasoningText}
              lottieData={lottieData}
            />
          );
        }
        if (item.type === "actions") {
          return (
            <DemoActionButtons
              key={item.key}
              actions={item.actions!}
              selectedLabel={item.selectedLabel}
            />
          );
        }
        if (item.type === "confirmation") {
          return <DemoConfirmation key={item.key} text={item.confirmationText!} />;
        }
        if (item.type === "memory") {
          return <DemoMemoryNudge key={item.key} text={item.memoryText!} />;
        }
        return (
          <AgentMessage
            key={item.key}
            message={item.message!}
            onFollowUpSelect={() => {}}
            onContentGrow={onContentGrow}
            onRetry={() => {}}
          />
        );
      })}
    </>
  );
}
