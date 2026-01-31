"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, Copy, ThumbsUp, ThumbsDown, RotateCcw } from "lucide-react";
import type { DisplayMessage } from "@/hooks";
import { InsightCard } from "@/components/clinical/InsightCard";
import { FollowUpSuggestions } from "./FollowUpSuggestions";

interface AgentMessageProps {
  message: DisplayMessage;
  onFollowUpSelect: (question: string) => void;
}

export function AgentMessage({ message, onFollowUpSelect }: AgentMessageProps) {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);
  const agentResponse = message.agentResponse;

  return (
    <div className="mb-8 space-y-3">
      {/* Thinking section */}
      {agentResponse?.thinking && (
        <button
          onClick={() => setThinkingExpanded(!thinkingExpanded)}
          className="flex items-center justify-between w-full max-w-2xl bg-muted/50 hover:bg-muted rounded-xl px-4 py-3 text-left transition-colors"
        >
          <span className="text-sm text-muted-foreground">
            Reasoning
          </span>
          {thinkingExpanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </button>
      )}

      {thinkingExpanded && agentResponse?.thinking && (
        <div className="bg-muted/30 rounded-xl px-4 py-3 text-sm text-muted-foreground whitespace-pre-wrap">
          {agentResponse.thinking}
        </div>
      )}

      {/* Narrative (markdown) */}
      <div className="agent-narrative text-foreground text-sm leading-relaxed [&_p]:mb-3 [&_p:last-child]:mb-0 [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:mb-2 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:mb-2 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:mb-3 [&_ol]:list-decimal [&_ol]:pl-5 [&_ol]:mb-3 [&_li]:mb-1 [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:rounded-lg [&_pre]:mb-3 [&_pre]:overflow-x-auto [&_blockquote]:border-l-2 [&_blockquote]:border-border [&_blockquote]:pl-4 [&_blockquote]:text-muted-foreground [&_a]:text-primary [&_a]:underline [&_table]:w-full [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:bg-muted [&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {message.content}
        </ReactMarkdown>
      </div>

      {/* Insights */}
      {agentResponse?.insights && agentResponse.insights.length > 0 && (
        <div className="space-y-2 mt-4">
          {agentResponse.insights.map((insight, index) => (
            <InsightCard key={index} insight={insight} />
          ))}
        </div>
      )}

      {/* Visualizations placeholder */}
      {agentResponse?.visualizations && agentResponse.visualizations.length > 0 && (
        <div className="space-y-2 mt-4">
          {agentResponse.visualizations.map((viz, index) => (
            <div
              key={index}
              className="rounded-xl border border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground"
            >
              📊 {viz.title} — visualization coming soon
            </div>
          ))}
        </div>
      )}

      {/* Tables placeholder */}
      {agentResponse?.tables && agentResponse.tables.length > 0 && (
        <div className="space-y-2 mt-4">
          {agentResponse.tables.map((table, index) => (
            <div
              key={index}
              className="rounded-xl border border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground"
            >
              📋 {table.title} — data table coming soon
            </div>
          ))}
        </div>
      )}

      {/* Follow-up suggestions */}
      {agentResponse?.follow_ups && agentResponse.follow_ups.length > 0 && (
        <FollowUpSuggestions
          followUps={agentResponse.follow_ups}
          onSelect={onFollowUpSelect}
        />
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-1">
        <ActionButton icon={Copy} label="Copy" />
        <ActionButton icon={ThumbsUp} label="Good response" />
        <ActionButton icon={ThumbsDown} label="Bad response" />
        <ActionButton icon={RotateCcw} label="Retry" />
      </div>
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title={label}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
