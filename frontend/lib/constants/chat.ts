/**
 * Shared constants for chat functionality
 */

// Clinical reasoning verbs for thinking animation
export const THINKING_VERBS = [
  "Starting context engine",
  "Traversing knowledge graph",
  "Expanding the graph",
  "Running semantic search",
  "Compiling FHIR resources",
  "Assembling clinical guidelines",
  "Completing clinical review",
  "Cogitating",
  "Discombobulating",
  "Reflecting",
  "Meditating",
  "Introspecting",
  "Thinking again",
  "Considering alternatives",
  "Checking my work",
  "Resolving gaps",
  "Exploring further",
] as const;

// Streaming text animation timing
export const STREAM_CHARS_PER_TICK = 3; // Average chars per interval
export const STREAM_INTERVAL_MS = 15;
export const STREAM_BUFFER_MS = 100;

// Thinking animation timing
export const THINKING_VERB_INTERVAL_MS = 2000;
