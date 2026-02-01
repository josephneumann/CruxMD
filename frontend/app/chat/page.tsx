"use client";

/**
 * Chat Entry Page - Initial greeting and input that redirects to chat session
 */

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowUp, Users, AlertCircle, BookOpen, Plus, Clock, ChevronDown, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";
import { useSession } from "@/lib/auth-client";
import { MODEL_OPTIONS, DEFAULT_MODEL } from "@/lib/types";
import type { ModelId } from "@/lib/types";

export default function ChatPage() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");
  const [model, setModel] = useState<ModelId>(DEFAULT_MODEL);
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
          {/* Greeting */}
          <div className="flex items-center gap-3 mb-8">
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
                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                  <Plus className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8 rounded-lg">
                  <Clock className="h-4 w-4" />
                </Button>
              </div>

              {/* Right toolbar */}
              <div className="flex items-center gap-2">
                <div className="relative" ref={menuRef}>
                  <button
                    onClick={() => setShowModelMenu((v) => !v)}
                    className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
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
              { label: "Patients needing attention", icon: AlertCircle },
              { label: "Review research", icon: BookOpen },
            ].map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => setInputValue(label)}
                className="flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card text-sm text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
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
