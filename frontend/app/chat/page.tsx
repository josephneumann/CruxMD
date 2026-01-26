"use client";

/**
 * Chat page - Main conversational canvas styled like Claude.ai
 */

import { useState, useEffect } from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import {
  Plus,
  Clock,
  ArrowUp,
  Phone,
  BookOpen,
  BarChart3,
  Users,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";

// Dynamically import Lottie to avoid SSR issues
const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

// Clinical reasoning verbs for the thinking animation
const THINKING_VERBS = [
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
];

export default function ChatPage() {
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingVerbIndex, setThinkingVerbIndex] = useState(0);
  const [lottieData, setLottieData] = useState<object | null>(null);

  // Load Lottie animation data
  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then((data) => setLottieData(data));
  }, []);

  // Cycle through thinking verbs
  useEffect(() => {
    if (!isThinking) return;
    const interval = setInterval(() => {
      setThinkingVerbIndex((prev) => (prev + 1) % THINKING_VERBS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [isThinking]);

  // Handle message submission
  const handleSubmit = () => {
    if (!inputValue.trim()) return;
    setIsThinking(true);
    setInputValue("");
  };

  // Get time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content - centered */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-32">
        <div className="w-full max-w-2xl flex flex-col items-center">
          {/* Greeting with mark */}
          <div className="flex items-center gap-3 mb-8">
            {/* Animated mark when thinking, static mark otherwise */}
            {isThinking && lottieData ? (
              <div className="w-10 h-10">
                <Lottie
                  animationData={lottieData}
                  loop={true}
                  style={{ width: "100%", height: "100%" }}
                />
              </div>
            ) : (
              <Image
                src="/brand/mark-primary.svg"
                alt=""
                width={40}
                height={40}
              />
            )}
            <h1 className="text-3xl md:text-4xl font-light text-foreground">
              {getGreeting()}, <span className="font-normal">Dr. Neumann</span>
            </h1>
          </div>

          {/* Input card */}
          <div className="w-full bg-card rounded-2xl border border-border shadow-sm">
            {/* Text input area */}
            <div className="px-4 py-4">
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={isThinking ? `${THINKING_VERBS[thinkingVerbIndex]}...` : "How can I help you today?"}
                className={`w-full bg-transparent text-foreground placeholder:text-muted-foreground resize-none outline-none text-base min-h-[24px] max-h-[200px] ${isThinking ? "placeholder:animate-pulse" : ""}`}
                rows={1}
                disabled={isThinking}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  target.style.height = `${target.scrollHeight}px`;
                }}
              />
            </div>

            {/* Bottom toolbar */}
            <div className="flex items-center justify-between px-4 pb-4">
              {/* Left actions */}
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                >
                  <Plus className="h-5 w-5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground"
                >
                  <Clock className="h-5 w-5" />
                </Button>
              </div>

              {/* Right actions */}
              <div className="flex items-center gap-2">
                {/* Model selector placeholder */}
                <Button
                  variant="ghost"
                  className="h-8 px-3 text-sm text-muted-foreground hover:text-foreground gap-1"
                >
                  Opus 4.5
                  <ChevronDown className="h-4 w-4" />
                </Button>

                {/* Send button */}
                <Button
                  size="icon"
                  className="h-8 w-8 rounded-lg"
                  disabled={!inputValue.trim() || isThinking}
                  onClick={handleSubmit}
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Quick action chips */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
            <QuickActionChip icon={Phone} label="Patients to call" />
            <QuickActionChip icon={BookOpen} label="Latest research" />
            <QuickActionChip icon={BarChart3} label="My performance" />
            <QuickActionChip icon={Users} label="Panel overview" />
          </div>

          {/* Copyright */}
          <p className="text-xs text-muted-foreground text-center mt-8">
            © {new Date().getFullYear()} CruxMD
          </p>
        </div>
      </main>
    </div>
  );
}

// Quick action chip component
function QuickActionChip({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card hover:bg-muted/50 text-sm text-foreground transition-colors">
      <Icon className="h-4 w-4 text-primary" />
      {label}
    </button>
  );
}
