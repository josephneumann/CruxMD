"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Typewriter hook that reveals text character-by-character at variable speed.
 * Simulates natural typing with randomized delays — faster on common letters,
 * slower on punctuation and word boundaries.
 */
export function useTypewriter(
  text: string,
  active: boolean,
  onComplete?: () => void,
) {
  const [charIndex, setCharIndex] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const completeRef = useRef(onComplete);
  completeRef.current = onComplete;

  // Reset when text changes
  useEffect(() => {
    setCharIndex(0);
  }, [text]);

  useEffect(() => {
    if (!active || charIndex >= text.length) {
      if (active && charIndex >= text.length) {
        completeRef.current?.();
      }
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
  }, [active, charIndex, text]);

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
