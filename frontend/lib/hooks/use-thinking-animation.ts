"use client";

import { useState, useEffect } from "react";
import { THINKING_VERBS, THINKING_VERB_INTERVAL_MS } from "@/lib/constants/chat";

/**
 * Hook for cycling through thinking verbs during loading states
 * Returns the current thinking verb to display
 */
export function useThinkingAnimation(isThinking: boolean): string {
  const [verbIndex, setVerbIndex] = useState(0);

  useEffect(() => {
    if (!isThinking) return;

    setVerbIndex(0);

    const interval = setInterval(() => {
      setVerbIndex((prev) => (prev + 1) % THINKING_VERBS.length);
    }, THINKING_VERB_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [isThinking]);

  return THINKING_VERBS[verbIndex];
}
