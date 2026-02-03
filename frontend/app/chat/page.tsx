"use client";

/**
 * Chat Entry Page - Initial greeting and input that redirects to chat session
 */

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowUp, Users, AlertCircle, BookOpen, Plus, Clock, ChevronDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { Sidebar } from "@/components/Sidebar";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";
import { useSession } from "@/lib/auth-client";
import { MODEL_OPTIONS, DEFAULT_MODEL } from "@/lib/types";
import type { ModelId, ReasoningEffort } from "@/lib/types";

export default function ChatPage() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [model, setModel] = useState<ModelId>(DEFAULT_MODEL);
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("medium");
  const [showModelMenu, setShowModelMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { data: session } = useSession();

  useEffect(() => {
    if (!showModelMenu) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowModelMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showModelMenu]);

  const selectedModel = MODEL_OPTIONS.find((m) => m.id === model) ?? MODEL_OPTIONS[0];
  const firstName = session?.user?.name?.split(" ")[0] || "there";

  const handleSubmit = () => {
    if (!inputValue.trim()) return;

    // Generate session ID and redirect with message in URL
    const sessionId = crypto.randomUUID();
    const encodedMessage = encodeURIComponent(inputValue.trim());
    router.push(`/chat/${sessionId}?message=${encodedMessage}`);
  };

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-32">
        <div className="w-full max-w-2xl flex flex-col items-center">
          {/* Avatar + Greeting */}
          <div className="flex flex-col items-center mb-8">
            <div className="mb-4 h-32 w-32 rounded-full overflow-hidden">
              <Image
                src="/brand/avatars/admin-avatar-front-facing.png"
                alt={firstName}
                width={128}
                height={128}
                className="h-full w-full object-cover opacity-70"
              />
            </div>
            <div className="flex items-center gap-3">
              <Image
                src="/brand/mark-primary.svg"
                alt=""
                width={40}
                height={40}
              />
              <h1 className="text-3xl md:text-4xl font-light text-foreground">
                {getGreeting()}, <span className="font-normal">{firstName}</span>
              </h1>
            </div>
          </div>

          {/* Input card */}
          <div className="w-full bg-card rounded-2xl border border-border shadow-sm">
            <div className="px-4 py-4">
              <AutoResizeTextarea
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSubmit}
                placeholder="What can I help you with today?"
                autoFocus
              />
            </div>
            <div className="flex items-center justify-between px-4 pb-4">
              {/* Left toolbar */}
              <div className="flex items-center gap-1">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer">
                      <Plus className="h-5 w-5" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">Add files, connectors and more</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors cursor-pointer"
                      onClick={() => setReasoningEffort(reasoningEffort === "high" ? "medium" : "high")}
                    >
                      <Clock className={`h-5 w-5 ${reasoningEffort === "high" ? "text-primary" : ""}`} />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">Extended thinking</TooltipContent>
                </Tooltip>
              </div>

              {/* Right toolbar */}
              <div className="flex items-center gap-2">
                <div className="relative" ref={menuRef}>
                  <button
                    onClick={() => setShowModelMenu((v) => !v)}
                    className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg px-2 py-1 transition-colors cursor-pointer"
                  >
                    {selectedModel.label}
                    <ChevronDown className="h-3 w-3" />
                  </button>
                  {showModelMenu && (
                    <div className="absolute bottom-full right-0 mb-2 w-56 rounded-lg border border-border bg-popover shadow-lg py-1 z-50">
                      {MODEL_OPTIONS.map((option) => (
                        <button
                          key={option.id}
                          onClick={() => {
                            setModel(option.id as ModelId);
                            setShowModelMenu(false);
                          }}
                          className="w-full flex items-center gap-3 px-3 py-2.5 text-left cursor-pointer rounded-md hover:bg-muted transition-colors"
                        >
                          <div className="w-4 flex-shrink-0">
                            {option.id === model && (
                              <Check className="h-4 w-4 text-primary" />
                            )}
                          </div>
                          <div>
                            <div className="text-sm font-medium">{option.label}</div>
                            <div className="text-xs text-muted-foreground">
                              {option.description}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <Button
                  size="icon"
                  className="h-8 w-8 rounded-lg"
                  disabled={!inputValue.trim()}
                  onClick={handleSubmit}
                >
                  <ArrowUp className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>

          {/* Quick actions */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {[
              { label: "Start huddle", icon: Users },
              { label: "Let's review patients needing my attention today", icon: AlertCircle },
              { label: "Review research", icon: BookOpen },
            ].map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => setInputValue(label)}
                className="flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors cursor-pointer"
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>

          {/* Copyright */}
          <p className="text-xs text-muted-foreground text-center mt-8">
            &copy; {new Date().getFullYear()} CruxMD
          </p>
        </div>
      </main>
    </div>
  );
}
