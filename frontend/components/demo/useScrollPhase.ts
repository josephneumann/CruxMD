"use client";

import { useEffect, useState, type RefObject } from "react";

const TOTAL_PHASES = 15; // 3 interactions × 5 phases each

/**
 * Maps scroll position within a container to a phase number (0–14).
 *
 * Places invisible sentinel divs aren't needed — instead we measure
 * the container's scroll progress directly via IntersectionObserver
 * threshold array on the scroll-driver element itself.
 */
export function useScrollPhase(containerRef: RefObject<HTMLElement | null>): {
  phase: number;
  progress: number;
} {
  const [phase, setPhase] = useState(0);
  const [progress, setProgress] = useState(0);

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
      const currentPhase = Math.min(Math.floor(exactPhase), TOTAL_PHASES - 1);
      const subProgress = exactPhase - currentPhase;

      setPhase(currentPhase);
      setProgress(Math.max(0, Math.min(1, subProgress)));
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

  return { phase, progress };
}
