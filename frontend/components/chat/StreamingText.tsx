"use client";

import { useState, useEffect } from "react";
import { STREAM_CHARS_PER_TICK, STREAM_INTERVAL_MS } from "@/lib/constants/chat";

interface StreamingTextProps {
  text: string;
  isStreaming: boolean;
  onComplete?: () => void;
}

/**
 * Text that reveals character by character with streaming animation
 */
export function StreamingText({ text, isStreaming, onComplete }: StreamingTextProps) {
  const [displayedChars, setDisplayedChars] = useState(0);

  useEffect(() => {
    if (!isStreaming) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync display when not streaming
      setDisplayedChars(text.length);
      return;
    }

    setDisplayedChars(0);
    const interval = setInterval(() => {
      setDisplayedChars((prev) => {
        const next = Math.min(prev + STREAM_CHARS_PER_TICK, text.length);
        if (next >= text.length) {
          clearInterval(interval);
          onComplete?.();
        }
        return next;
      });
    }, STREAM_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [text, isStreaming, onComplete]);

  return <span>{text.slice(0, displayedChars)}</span>;
}
