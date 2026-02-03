"use client";

import { useEffect, useRef, useState } from "react";
import { STREAM_CHARS_PER_TICK, STREAM_INTERVAL_MS } from "@/lib/constants/chat";

export type TypewriterSpeed = "human" | "stream";

/**
 * Typewriter hook that reveals text progressively.
 *
 * Two speed modes:
 * - "human": Character-by-character with natural variable delays (for user input)
 * - "stream": Fast chunk-based reveal matching AI response streaming speed
 *
 * @param onContentGrow - Called periodically during typing and on completion,
 *   allowing scroll sync as content grows.
 */
export function useTypewriter(
  text: string,
  active: boolean,
  onContentGrow?: () => void,
  speed: TypewriterSpeed = "human",
) {
  const [charIndex, setCharIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const callbackRef = useRef(onContentGrow);
  callbackRef.current = onContentGrow;
  const lastGrowCallRef = useRef(0);

  // Reset when text changes
  useEffect(() => {
    setCharIndex(0);
    lastGrowCallRef.current = 0;
  }, [text]);

  // Call onContentGrow periodically during typing
  useEffect(() => {
    if (!active) return;

    // Call on completion
    if (charIndex >= text.length) {
      callbackRef.current?.();
      return;
    }

    // Call every ~5 characters or on newlines to keep scroll synced
    const char = text[charIndex - 1]; // just typed char
    const charsSinceLastCall = charIndex - lastGrowCallRef.current;
    const shouldCallGrow = charsSinceLastCall >= 5 || char === "\n";

    if (shouldCallGrow && charIndex > 0) {
      lastGrowCallRef.current = charIndex;
      callbackRef.current?.();
    }
  }, [active, charIndex, text]);

  // Human mode: character-by-character with variable delays
  useEffect(() => {
    if (speed !== "human" || !active || charIndex >= text.length) {
      return;
    }

    const char = text[charIndex];
    const delay = getCharDelay(char);

    timerRef.current = setTimeout(() => {
      setCharIndex((prev) => prev + 1);
    }, delay);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [active, charIndex, text, speed]);

  // Stream mode: fast chunk-based reveal (matches AI response streaming)
  useEffect(() => {
    if (speed !== "stream" || !active) {
      return;
    }

    // Reset to start when activating
    setCharIndex(0);
    lastGrowCallRef.current = 0;

    const interval = setInterval(() => {
      setCharIndex((prev) => {
        const next = prev + STREAM_CHARS_PER_TICK;
        if (next >= text.length) {
          clearInterval(interval);
          return text.length;
        }
        return next;
      });
    }, STREAM_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [active, text, speed]);

  // For stream mode, snap to word boundaries for cleaner display
  if (speed === "stream" && active && charIndex < text.length) {
    const nextSpace = text.indexOf(" ", charIndex);
    const end = nextSpace === -1 ? charIndex : nextSpace;
    return text.slice(0, end);
  }

  return active ? text.slice(0, charIndex) : text;
}

/** Variable delay per character to simulate natural typing rhythm. */
function getCharDelay(char: string): number {
  // Pause longer on punctuation
  if (".,;:!?".includes(char)) return 80 + Math.random() * 60;
  // Brief pause at word boundaries
  if (char === " ") return 30 + Math.random() * 40;
  // Dash/em-dash gets a slight hesitation
  if (char === "—" || char === "-") return 50 + Math.random() * 40;
  // Regular characters — fast with slight variance
  return 18 + Math.random() * 28;
}
