"use client";

import { useThinkingAnimation } from "@/lib/hooks/use-thinking-animation";

export function ThinkingIndicator() {
  const thinkingVerb = useThinkingAnimation(true);

  return (
    <div className="mb-4">
      <div className="bg-muted/50 rounded-xl px-4 py-3 w-fit">
        <span className="text-sm text-muted-foreground animate-pulse">
          {thinkingVerb}...
        </span>
      </div>
    </div>
  );
}
