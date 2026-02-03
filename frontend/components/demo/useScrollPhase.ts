"use client";

import { useCallback, useEffect, useState, type RefObject } from "react";

const PHASES_PER_INTERACTION = 5;
const TOTAL_INTERACTIONS = 3;
const TOTAL_PHASES = TOTAL_INTERACTIONS * PHASES_PER_INTERACTION;

/**
 * Maps scroll position within a container to a phase number (0–14).
 *
 * Places invisible sentinel divs aren't needed — instead we measure
 * the container's scroll progress directly via IntersectionObserver
 * threshold array on the scroll-driver element itself.
 */
export function useScrollPhase(containerRef: RefObject<HTMLElement | null>): {
  phase: number;
  reset: () => void;
} {
  const [phase, setPhase] = useState(0);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const rect = container.getBoundingClientRect();
      const viewportHeight = window.innerHeight;

      // Total scrollable distance: container height minus one viewport
      const scrollableHeight = container.offsetHeight - viewportHeight;
      if (scrollableHeight <= 0) return;

      // How far the container top has scrolled past the top of the viewport
      // (offset by sticky top so phases align with visible canvas area)
      const scrolled = -rect.top;
      const rawProgress = Math.max(0, Math.min(1, scrolled / scrollableHeight));

      const exactPhase = rawProgress * TOTAL_PHASES;
      setPhase(Math.floor(exactPhase));
    };

    // Use IntersectionObserver to know when the container is visible,
    // then attach a passive scroll listener for granular phase tracking.
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          window.addEventListener("scroll", handleScroll, { passive: true });
          handleScroll(); // initial calc
        } else {
          window.removeEventListener("scroll", handleScroll);
        }
      },
      { threshold: 0 }
    );

    observer.observe(container);

    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", handleScroll);
    };
  }, [containerRef]);

  const reset = useCallback(() => setPhase(0), []);

  return { phase, reset };
}
