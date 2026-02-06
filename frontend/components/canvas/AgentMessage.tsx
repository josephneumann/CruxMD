"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, Clock, CircleCheck, Copy, ThumbsUp, ThumbsDown, RefreshCw, Check } from "lucide-react";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import type { DisplayMessage } from "@/hooks";
import { ToolActivity } from "./ToolActivity";
import { InsightCard } from "@/components/clinical/InsightCard";
import { FollowUpSuggestions } from "./FollowUpSuggestions";
import { STREAM_CHARS_PER_TICK, STREAM_INTERVAL_MS } from "@/lib/constants/chat";

interface AgentMessageProps {
  message: DisplayMessage;
  onFollowUpSelect: (question: string) => void;
  /** Called during typewriter/animation so parent can auto-scroll */
  onContentGrow?: () => void;
  /** Called to regenerate this response */
  onRetry?: () => void;
}

const NARRATIVE_STYLES = [
  "text-foreground text-sm leading-relaxed",
  "[&_p]:mb-3 [&_p:last-child]:mb-0",
  "[&_h1]:text-xl [&_h1]:font-semibold [&_h1]:mb-2",
  "[&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mb-2",
  "[&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2",
  "[&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3",
  "[&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3",
  "[&_li]:mb-1",
  "[&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs",
  "[&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded-lg [&_pre]:mb-3 [&_pre]:overflow-x-auto",
  "[&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground",
  "[&_a]:text-primary [&_a]:underline",
  "[&_table]:w-full [&_table]:border-collapse",
  "[&_th]:border [&_th]:border-border [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:bg-muted",
  "[&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5",
].join(" ");

/**
 * Hook that reveals text progressively (typewriter effect).
 * Calls onTick each time visible text changes so caller can scroll.
 */
function useTypewriter(
  fullText: string,
  active: boolean,
  onTick?: () => void,
) {
  const [charCount, setCharCount] = useState(active ? 0 : fullText.length);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onTickRef = useRef(onTick);
  // eslint-disable-next-line react-hooks/refs -- sync ref pattern for stable callback in interval
  onTickRef.current = onTick;

  useEffect(() => {
    if (!active) {
      setCharCount(fullText.length);
      return;
    }

    setCharCount(0);
    intervalRef.current = setInterval(() => {
      setCharCount((prev) => {
        const next = prev + STREAM_CHARS_PER_TICK;
        if (next >= fullText.length) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return fullText.length;
        }
        return next;
      });
      onTickRef.current?.();
    }, STREAM_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fullText, active]);

  const done = charCount >= fullText.length;
  let end = charCount;
  if (!done) {
    const nextSpace = fullText.indexOf(" ", charCount);
    end = nextSpace === -1 ? charCount : nextSpace;
  }

  return { visibleText: fullText.slice(0, end), done };
}

/** Format ms duration as human-readable string */
function formatDuration(ms: number): string {
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds} second${seconds !== 1 ? "s" : ""}`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return remaining > 0
    ? `${minutes}m ${remaining}s`
    : `${minutes} minute${minutes !== 1 ? "s" : ""}`;
}

/** Severity ordering for insight cards (most severe first) */
const INSIGHT_SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
  positive: 3,
};

/** Stagger delay in ms between each insight card appearing */
const INSIGHT_STAGGER_MS = 150;

export function AgentMessage({ message, onFollowUpSelect, onContentGrow, onRetry }: AgentMessageProps) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const agentResponse = message.agentResponse;
  const isStreaming = message.pending || (message.streaming && message.streaming.phase !== "done");

  // Don't render anything while actively streaming — ThinkingIndicator handles that
  if (isStreaming) return null;

  const narrativeContent = agentResponse?.narrative ?? message.content;
  const justFinished = message.streaming?.phase === "done";

  // Full reasoning chain for expanded view (prefer accumulated SSE summaries which
  // contain the entire chain, fall back to agentResponse.thinking)
  const reasoningText = message.streaming?.reasoningText || agentResponse?.thinking;
  const reasoningDurationMs = message.streaming?.reasoningDurationMs;
  const toolCalls = message.streaming?.toolCalls ?? [];

  return (
    <AgentMessageInner
      key={message.id}
      narrativeContent={narrativeContent}
      agentResponse={agentResponse}
      reasoningText={reasoningText}
      reasoningDurationMs={reasoningDurationMs}
      toolCalls={toolCalls}
      thinkingExpanded={thinkingExpanded}
      setThinkingExpanded={setThinkingExpanded}
      onFollowUpSelect={onFollowUpSelect}
      animate={!!justFinished}
      onContentGrow={onContentGrow}
      onRetry={onRetry}
    />
  );
}

function AgentMessageInner({
  narrativeContent,
  agentResponse,
  reasoningText,
  reasoningDurationMs,
  toolCalls,
  thinkingExpanded,
  setThinkingExpanded,
  onFollowUpSelect,
  animate,
  onContentGrow,
  onRetry,
}: {
  narrativeContent: string;
  agentResponse?: DisplayMessage["agentResponse"];
  reasoningText?: string;
  reasoningDurationMs?: number;
  toolCalls: import("@/hooks").ToolCallState[];
  thinkingExpanded: boolean;
  setThinkingExpanded: (v: boolean) => void;
  onFollowUpSelect: (question: string) => void;
  animate: boolean;
  onContentGrow?: () => void;
  onRetry?: () => void;
}) {
  const { visibleText, done } = useTypewriter(narrativeContent, animate, onContentGrow);
  const showExtras = !animate || done;

  // Sort insight cards by severity (critical first)
  const insights = [...(agentResponse?.insights ?? [])].sort(
    (a, b) => (INSIGHT_SEVERITY_ORDER[a.type] ?? 9) - (INSIGHT_SEVERITY_ORDER[b.type] ?? 9),
  );
  const [visibleInsightCount, setVisibleInsightCount] = useState(
    animate ? 0 : insights.length,
  );

  useEffect(() => {
    if (!animate || !showExtras || insights.length === 0) {
      if (showExtras) setVisibleInsightCount(insights.length);
      return;
    }

    setVisibleInsightCount(0);
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setVisibleInsightCount(i);
      onContentGrow?.();
      if (i >= insights.length) clearInterval(timer);
    }, INSIGHT_STAGGER_MS);

    return () => clearInterval(timer);
  }, [showExtras, animate, insights.length, onContentGrow]);

  const durationLabel = reasoningDurationMs
    ? `Thought for ${formatDuration(reasoningDurationMs)}`
    : "Reasoning";

  return (
    <div className="mb-8 space-y-3">
      {/* Thinking section — Claude-style "Thought for Xs" */}
      {(reasoningText || toolCalls.length > 0) && (
        <button
          onClick={() => setThinkingExpanded(!thinkingExpanded)}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          <span>{durationLabel}</span>
          {thinkingExpanded ? (
            <ChevronUp className="h-3 w-3" />
          ) : (
            <ChevronDown className="h-3 w-3" />
          )}
        </button>
      )}

      {thinkingExpanded && (reasoningText || toolCalls.length > 0) && (
        <div className="border-l-2 border-border pl-4 py-2 space-y-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5" />
            <span>Thinking</span>
          </div>
          {reasoningText && (
            <div className="text-xs text-muted-foreground leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ul]:mb-2 [&_li]:mb-0.5 [&_strong]:text-muted-foreground [&_strong]:font-semibold">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {reasoningText}
              </ReactMarkdown>
            </div>
          )}
          {toolCalls.length > 0 && (
            <ToolActivity toolCalls={toolCalls} />
          )}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <CircleCheck className="h-3.5 w-3.5" />
            <span>Done</span>
          </div>
        </div>
      )}

      {/* Narrative (markdown) */}
      {visibleText && (
        <div className={NARRATIVE_STYLES}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {visibleText}
          </ReactMarkdown>
        </div>
      )}

      {/* Insights — staggered reveal */}
      {insights.length > 0 && visibleInsightCount > 0 && (
        <div className="space-y-2 mt-4">
          {insights.slice(0, visibleInsightCount).map((insight, index) => (
            <div
              key={index}
              className={animate ? "animate-in fade-in slide-in-from-bottom-2 duration-300" : ""}
            >
              <InsightCard insight={insight} />
            </div>
          ))}
        </div>
      )}

      {/* Message actions */}
      {showExtras && narrativeContent && <MessageActions narrativeContent={narrativeContent} onRetry={onRetry} />}

      {/* Follow-up suggestions */}
      {showExtras && visibleInsightCount >= insights.length &&
        agentResponse?.follow_ups && agentResponse.follow_ups.length > 0 && (
        <FollowUpSuggestions
          followUps={agentResponse.follow_ups}
          onSelect={onFollowUpSelect}
        />
      )}
    </div>
  );
}

function MessageActions({ narrativeContent, onRetry }: { narrativeContent: string; onRetry?: () => void }) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(narrativeContent);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = narrativeContent;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex items-center gap-1 mt-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Copy</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={() => setFeedback(feedback === "up" ? null : "up")}
            className={`p-1.5 rounded-md transition-colors cursor-pointer ${feedback === "up" ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}
          >
            <ThumbsUp className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Give positive feedback</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={() => setFeedback(feedback === "down" ? null : "down")}
            className={`p-1.5 rounded-md transition-colors cursor-pointer ${feedback === "down" ? "text-destructive bg-destructive/10" : "text-muted-foreground hover:text-foreground hover:bg-muted"}`}
          >
            <ThumbsDown className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Give negative feedback</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={onRetry}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Retry</TooltipContent>
      </Tooltip>
    </div>
  );
}
