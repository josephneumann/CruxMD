"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAutoplay, INTRO_PHASES } from "./useAutoplay";
import { useTypewriter } from "./useTypewriter";
import { DemoCanvas } from "./DemoCanvas";
import { DemoHomeScreen } from "./DemoHomeScreen";
import { ScenarioTabs } from "./ScenarioTabs";
import {
  heartFailureScenario,
  qtProlongationScenario,
  hcmScenario,
  hypoglycemiaScenario,
} from "@/lib/demo-scenarios";

const SCENARIO_TABS = [
  { id: "heart-failure", label: "Heart Failure", scenario: heartFailureScenario, avatar: "/brand/demo/avatar-margaret-chen.png" },
  { id: "qt-prolongation", label: "QT Prolongation", scenario: qtProlongationScenario, avatar: "/brand/demo/avatar-dorothy-williams.png" },
  { id: "hcm", label: "Young Athlete", scenario: hcmScenario, avatar: "/brand/demo/avatar-tyler-reeves.png" },
  { id: "hypoglycemia", label: "Hypoglycemia", scenario: hypoglycemiaScenario, avatar: "/brand/demo/avatar-robert-garcia.png" },
];

export function DemoSection() {
  const sectionRef = useRef<HTMLElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTabId, setActiveTabId] = useState(SCENARIO_TABS[0].id);
  const [isLocked, setIsLocked] = useState(false);
  const scrollAccumulatorRef = useRef(0);

  const activeTab = useMemo(
    () => SCENARIO_TABS.find((t) => t.id === activeTabId)!,
    [activeTabId],
  );

  const { phase, reset: resetAutoplay, introMessage, isComplete } = useAutoplay(canvasRef, activeTab.scenario);

  const isIntro = phase < INTRO_PHASES;
  const isTyping = phase === 1;
  const isSubmitted = phase >= 2;

  // Typewriter text for the home screen input
  const typedText = useTypewriter(introMessage, isTyping);

  // Auto-scroll canvas to bottom as new content appears
  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [phase, scrollToBottom]);

  const handleTabSelect = useCallback(
    (id: string) => {
      if (id === activeTabId) return;
      setActiveTabId(id);
      resetAutoplay();
      // Reset canvas scroll position
      if (scrollRef.current) {
        scrollRef.current.scrollTop = 0;
      }
    },
    [activeTabId, resetAutoplay],
  );

  // Scroll hijacking logic - lock body scroll when demo section is in view
  useEffect(() => {
    const section = sectionRef.current;
    const scrollContainer = scrollRef.current;
    if (!section || !scrollContainer) return;

    let isLockedInternal = false;

    const lockScroll = () => {
      if (!isLockedInternal) {
        isLockedInternal = true;
        setIsLocked(true);
        document.body.style.overflow = "hidden";
      }
    };

    const unlockScroll = () => {
      if (isLockedInternal) {
        isLockedInternal = false;
        setIsLocked(false);
        document.body.style.overflow = "";
      }
    };

    // Check if we should be locked based on current visibility
    const checkAndLock = () => {
      const rect = section.getBoundingClientRect();
      // Lock when section top is near or above viewport top and demo not complete
      const shouldLock = rect.top <= 100 && rect.bottom > window.innerHeight * 0.5 && !isComplete;

      if (shouldLock) {
        lockScroll();
        // Snap to section top if we're close
        if (rect.top > 0 && rect.top < 100) {
          section.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    };

    // Use IntersectionObserver to detect when section enters viewport
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isComplete) {
          checkAndLock();
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(section);

    const handleWheel = (e: WheelEvent) => {
      const rect = section.getBoundingClientRect();
      const scrollingDown = e.deltaY > 0;
      const scrollingUp = e.deltaY < 0;

      // Check if demo section fills the viewport (or nearly so)
      const sectionFillsViewport = rect.top <= 10 && rect.bottom >= window.innerHeight - 10;

      // Check if we're approaching from above (scrolling down)
      const approachingFromAbove = rect.top > 10;

      const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
      const isAtBottom = scrollTop + clientHeight >= scrollHeight - 1;

      // SCROLLING UP: Always allow - user can return to hero anytime
      if (scrollingUp) {
        unlockScroll();
        return;
      }

      // SCROLLING DOWN scenarios:
      if (scrollingDown) {
        // If demo section hasn't filled viewport yet (approaching from above), let page scroll
        if (approachingFromAbove) {
          unlockScroll();
          return;
        }

        // If demo is complete and canvas is at bottom, release to scroll past demo
        if (isComplete && isAtBottom) {
          unlockScroll();
          return;
        }
      }

      // If section doesn't fill viewport at all, don't hijack
      if (!sectionFillsViewport) {
        unlockScroll();
        return;
      }

      // Lock and hijack scroll (only for scrolling down within demo)
      e.preventDefault();
      lockScroll();

      // Apply scroll to canvas
      scrollContainer.scrollTop += e.deltaY;
    };

    window.addEventListener("wheel", handleWheel, { passive: false });

    return () => {
      observer.disconnect();
      window.removeEventListener("wheel", handleWheel);
      document.body.style.overflow = "";
    };
  }, [isComplete]);

  return (
    <section
      ref={sectionRef}
      className="relative px-4 md:px-8 min-h-screen md:h-screen flex flex-col justify-start md:justify-center pt-8 md:pt-0 overflow-hidden"
    >
      <div className="max-w-4xl mx-auto w-full">
        {/* Scenario tabs — fade in after intro */}
        <div
          className={`transition-all duration-700 ease-out ${
            isIntro ? "opacity-0 translate-y-2 pointer-events-none" : "opacity-100 translate-y-0"
          }`}
        >
          <ScenarioTabs
            tabs={SCENARIO_TABS}
            activeId={activeTabId}
            onSelect={handleTabSelect}
          />
        </div>

        {/* Canvas frame */}
        <div
          ref={canvasRef}
          className="rounded-xl border border-border bg-background"
          role="region"
          aria-label="Interactive demo preview"
        >
          <div
            ref={scrollRef}
            className="overflow-y-auto scrollbar-hide h-[75vh] md:h-[70vh]"
          >
            {/* Home screen — visible during intro phases */}
            {isIntro && (
              <DemoHomeScreen
                inputText={isTyping ? typedText : ""}
                submitted={isSubmitted}
              />
            )}

            {/* Canvas — visible after intro */}
            {!isIntro && (
              <div className="max-w-3xl mx-auto px-4 pt-8 pb-8 animate-in fade-in slide-in-from-bottom-2 duration-700 ease-out">
                <DemoCanvas scenario={activeTab.scenario} phase={phase} avatar={activeTab.avatar} onContentGrow={scrollToBottom} />
              </div>
            )}
          </div>
        </div>

        {/* Scroll hint — appears after demo completes */}
        {isComplete && (
          <p className="text-center text-xs text-muted-foreground/60 mt-4">
            Scroll to continue
          </p>
        )}
      </div>
    </section>
  );
}
