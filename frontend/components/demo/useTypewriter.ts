"use client";

import { useEffect, useRef, useState } from "react";
import { STREAM_CHARS_PER_TICK, STREAM_INTERVAL_MS } from "@/lib/constants/chat";

export type TypewriterSpeed = "human" | "stream";

// ─── Typing delay constants (human mode) ────────────────────────────────────
// Simulates natural typing rhythm with randomized delays

const TYPING_DELAYS = {
  /** Punctuation gets a longer pause (.,;:!?) */
  PUNCTUATION: { base: 80, variance: 60 },
  /** Brief pause at word boundaries */
  SPACE: { base: 30, variance: 40 },
  /** Dash/em-dash gets slight hesitation */
  DASH: { base: 50, variance: 40 },
  /** Regular characters — fast with slight variance */
  REGULAR: { base: 18, variance: 28 },
} as const;

/** Characters to scroll-sync on during typing */
const GROW_CALLBACK_INTERVAL = 5;

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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const callbackRef = useRef(onContentGrow);
  const lastGrowCallRef = useRef(0);

  // Keep callback ref fresh
  useEffect(() => {
    callbackRef.current = onContentGrow;
  }, [onContentGrow]);

  // Reset when text changes
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset on text change
    setCharIndex(0);
    lastGrowCallRef.current = 0;
  }, [text]);

  // Cleanup all timers on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  // Call onContentGrow periodically during typing
  useEffect(() => {
    if (!active) return;

    // Call on completion
    if (charIndex >= text.length) {
      callbackRef.current?.();
      return;
    }

    // Call every N characters or on newlines to keep scroll synced
    const char = text[charIndex - 1];
    const charsSinceLastCall = charIndex - lastGrowCallRef.current;
    const shouldCallGrow = charsSinceLastCall >= GROW_CALLBACK_INTERVAL || char === "\n";

    if (shouldCallGrow && charIndex > 0) {
      lastGrowCallRef.current = charIndex;
      callbackRef.current?.();
    }
  }, [active, charIndex, text]);

  // Human mode: character-by-character with variable delays
  useEffect(() => {
    if (speed !== "human") {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    if (!active || charIndex >= text.length) return;

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
    if (speed !== "stream") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    if (!active) return;

    // Reset to start when activating
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset before starting interval
    setCharIndex(0);
    lastGrowCallRef.current = 0;

    intervalRef.current = setInterval(() => {
      setCharIndex((prev) => {
        const next = prev + STREAM_CHARS_PER_TICK;
        if (next >= text.length) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return text.length;
        }
        return next;
      });
    }, STREAM_INTERVAL_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
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
  if (".,;:!?".includes(char)) {
    return TYPING_DELAYS.PUNCTUATION.base + Math.random() * TYPING_DELAYS.PUNCTUATION.variance;
  }
  if (char === " ") {
    return TYPING_DELAYS.SPACE.base + Math.random() * TYPING_DELAYS.SPACE.variance;
  }
  if (char === "—" || char === "-") {
    return TYPING_DELAYS.DASH.base + Math.random() * TYPING_DELAYS.DASH.variance;
  }
  return TYPING_DELAYS.REGULAR.base + Math.random() * TYPING_DELAYS.REGULAR.variance;
}
