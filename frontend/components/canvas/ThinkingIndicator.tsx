"use client";

import { useThinkingAnimation } from "@/lib/hooks/use-thinking-animation";

interface ThinkingIndicatorProps {
  /** Accumulated reasoning summary text from SSE stream */
  reasoningText?: string;
}

/**
 * Extract the short headline from a reasoning summary.
 * OpenAI formats summaries as "**Bold Header**\n\nDetails..." —
 * we extract just the bold header for a concise inline display.
 */
function extractHeadline(text: string): string | null {
  if (!text) return null;

  // Get the last paragraph block (most recent reasoning step)
  const blocks = text.trim().split(/\n\n+/).filter(Boolean);
  const lastBlock = blocks[blocks.length - 1];
  if (!lastBlock) return null;

  // Try to extract **bold header** from the block
  const boldMatch = lastBlock.match(/\*\*(.+?)\*\*/);
  if (boldMatch) return boldMatch[1];

  // Fallback: use first line, truncated
  const firstLine = lastBlock.split("\n")[0].trim();
  return firstLine.length > 80 ? firstLine.slice(0, 77) + "..." : firstLine;
}

export function ThinkingIndicator({ reasoningText }: ThinkingIndicatorProps) {
  const thinkingVerb = useThinkingAnimation(true);
  const headline = extractHeadline(reasoningText ?? "");

  return (
    <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
      <span className="animate-pulse">
        {headline ?? thinkingVerb}
      </span>
    </div>
  );
}
