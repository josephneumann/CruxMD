"use client";

import type { ToolCallState } from "@/hooks";
import { formatToolDone, getToolIcon } from "./tool-labels";

interface ToolActivityProps {
  toolCalls: ToolCallState[];
}

export function ToolActivity({ toolCalls }: ToolActivityProps) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="space-y-1">
      {toolCalls.map((tc) => {
        const Icon = getToolIcon(tc.name);
        return (
          <div
            key={tc.callId}
            className="flex items-center gap-2 text-xs text-muted-foreground"
          >
            <Icon className="h-3.5 w-3.5 shrink-0" />
            <span>{formatToolDone(tc.name, tc.arguments)}</span>
          </div>
        );
      })}
    </div>
  );
}
