"use client";

/**
 * Chat page - Main conversational canvas styled like Claude.ai
 */

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
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

export default function ChatPage() {
  const [inputValue, setInputValue] = useState("");

  // Get time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border">
        <Link href="/">
          <Image
            src="/brand/wordmark-primary.svg"
            alt="CruxMD"
            width={120}
            height={28}
            priority
          />
        </Link>
      </header>

      {/* Main content - centered */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-32">
        <div className="w-full max-w-2xl flex flex-col items-center">
          {/* Greeting with mark */}
          <div className="flex items-center gap-3 mb-8">
            <Image
              src="/brand/mark-primary.svg"
              alt=""
              width={40}
              height={40}
            />
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
                placeholder="How can I help you today?"
                className="w-full bg-transparent text-foreground placeholder:text-muted-foreground resize-none outline-none text-base min-h-[24px] max-h-[200px]"
                rows={1}
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
                  disabled={!inputValue.trim()}
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

          {/* Disclaimer */}
          <p className="text-xs text-muted-foreground text-center mt-8 max-w-md">
            For demonstration purposes only. Not for clinical use. Always
            verify information with primary sources.
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
