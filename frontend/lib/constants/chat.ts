/**
 * Shared constants for chat functionality
 */

// Clinical reasoning verbs for thinking animation
export const THINKING_VERBS = [
  "Researching",
  "Reviewing history",
  "Considering differential",
  "Analyzing labs",
  "Cross-referencing",
  "Refining thinking",
  "Ruling out",
  "Synthesizing",
  "Correlating findings",
  "Checking interactions",
  "Cogitating",
  "Introspecting",
  "Discombobulating",
  "Reflecting",
  "Meditating",
] as const;

// Streaming text animation timing
export const STREAM_CHARS_PER_TICK = 3; // Average chars per interval
export const STREAM_INTERVAL_MS = 15;
export const STREAM_BUFFER_MS = 100;

// Thinking animation timing
export const THINKING_VERB_INTERVAL_MS = 2000;
