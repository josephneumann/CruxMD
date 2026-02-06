"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DemoScenario } from "@/lib/demo-scenarios";
import { STREAM_CHARS_PER_TICK, STREAM_INTERVAL_MS } from "@/lib/constants/chat";

const PHASES_PER_INTERACTION = 5;
const TOTAL_INTERACTIONS = 3;

/** Number of intro phases before canvas interactions begin. */
export const INTRO_PHASES = 3;

/** Number of phases for triage message typewriter (before first interaction). */
export const TRIAGE_PHASES = 1;

const INTRO_MESSAGE = "Lets review patients needing my attention this morning";

/** Average ms per character for human typing estimate (matches useTypewriter "human" mode). */
const AVG_MS_PER_CHAR_HUMAN = 38;
/** Effective ms per character for AI streaming (matches useTypewriter "stream" mode). */
const AVG_MS_PER_CHAR_STREAM = STREAM_INTERVAL_MS / STREAM_CHARS_PER_TICK;
/** Extra buffer after typing completes before advancing. */
const POST_TYPING_PAUSE = 400;

/** Milliseconds to hold each interaction-local phase before advancing. */
const PHASE_DURATIONS: Record<number, number> = {
  0: 0,    // user message — duration computed from typing speed
  1: 1800, // thinking indicator
  2: 2200, // narrative
  3: 1600, // insights
  4: 1200, // follow-ups
};

function getEpiloguePhaseCount(scenario?: DemoScenario): number {
  if (!scenario?.epilogue) return 0;
  // One phase for pre-epilogue pause + one per completion + one for memory
  return 1 + scenario.epilogue.completions.length + 1;
}

function getTotalPhases(scenario?: DemoScenario): number {
  const base = INTRO_PHASES + TRIAGE_PHASES + TOTAL_INTERACTIONS * PHASES_PER_INTERACTION;
  return base + getEpiloguePhaseCount(scenario);
}

function getPhaseDuration(phase: number, scenario?: DemoScenario): number {
  // Intro phases
  if (phase < INTRO_PHASES) {
    if (phase === 0) return 1200; // home screen visible
    if (phase === 1) return INTRO_MESSAGE.length * AVG_MS_PER_CHAR_HUMAN + POST_TYPING_PAUSE; // typing
    return 1000; // submit animation (allows smooth transition)
  }

  const canvasPhase = phase - INTRO_PHASES;

  // Triage phase — AI's initial seeding message (uses fast streaming speed)
  if (canvasPhase < TRIAGE_PHASES) {
    const triageLen = scenario?.triageMessage?.length ?? 100;
    return triageLen * AVG_MS_PER_CHAR_STREAM + POST_TYPING_PAUSE;
  }

  const interactionPhase = canvasPhase - TRIAGE_PHASES;
  const interactionPhases = TOTAL_INTERACTIONS * PHASES_PER_INTERACTION;

  // Epilogue phases (pause, then one per action completion, then memory)
  if (interactionPhase >= interactionPhases) {
    const epiloguePhase = interactionPhase - interactionPhases;
    const completionCount = scenario?.epilogue?.completions.length ?? 0;
    // Phase 0: pre-epilogue pause — let narrative fully resolve before action selection
    if (epiloguePhase === 0) return 1800;
    // Action completion phases — slower to perceive each check
    if (epiloguePhase <= completionCount) return 800;
    // Memory phase
    return 1200;
  }

  const localPhase = interactionPhase % PHASES_PER_INTERACTION;
  if (localPhase === 0 && scenario) {
    const interactionIdx = Math.floor(interactionPhase / PHASES_PER_INTERACTION);
    const msg = scenario.interactions[interactionIdx]?.userMessage ?? "";
    return msg.length * AVG_MS_PER_CHAR_HUMAN + POST_TYPING_PAUSE;
  }
  return PHASE_DURATIONS[localPhase] ?? 1200;
}

/**
 * Auto-advances through demo phases when visible in viewport.
 * Phases 0-2 are intro (home screen → typing → submit).
 * Phase 3+ maps to canvas interaction phases.
 */
export function useAutoplay(triggerRef: React.RefObject<HTMLElement | null>, scenario?: DemoScenario) {
  const [phase, setPhase] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isVisibleRef = useRef(false);
  const hasSeenIntroRef = useRef(false);

  const totalPhases = getTotalPhases(scenario);

  // Advance to next phase
  const advance = useCallback(() => {
    setPhase((prev) => {
      const next = prev + 1;
      // Mark intro as seen once we pass it
      if (next >= INTRO_PHASES) {
        hasSeenIntroRef.current = true;
      }
      if (next >= totalPhases) {
        setIsPlaying(false);
        return totalPhases - 1;
      }
      return next;
    });
  }, [totalPhases]);

  // Schedule next advance
  useEffect(() => {
    if (!isPlaying || phase < 0 || phase >= totalPhases - 1) return;

    timerRef.current = setTimeout(advance, getPhaseDuration(phase, scenario));
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- totalPhases derived from scenario
  }, [phase, isPlaying, advance, scenario]);

  // IntersectionObserver — start when visible
  useEffect(() => {
    const el = triggerRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        isVisibleRef.current = entry.isIntersecting;
        if (entry.isIntersecting && phase === -1) {
          setPhase(0);
          setIsPlaying(true);
        }
      },
      { threshold: 0.2 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [triggerRef, phase]);

  const reset = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    // If intro already seen, skip directly to canvas phase without intermediate state
    if (hasSeenIntroRef.current) {
      setPhase(INTRO_PHASES);
      setIsPlaying(true);
    } else {
      setPhase(-1);
      setIsPlaying(false);
      setTimeout(() => {
        setPhase(0);
        setIsPlaying(true);
      }, 100);
    }
  }, []);

  // If intro was seen, never return a phase below INTRO_PHASES
  const effectivePhase = hasSeenIntroRef.current
    ? Math.max(phase, INTRO_PHASES)
    : Math.max(phase, 0);

  const isComplete = phase >= totalPhases - 1;

  return { phase: effectivePhase, isPlaying, isComplete, reset, introMessage: INTRO_MESSAGE };
}
