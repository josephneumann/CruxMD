"use client";

/**
 * Chat Entry Page - Initial greeting and input that redirects to chat session
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";

export default function ChatPage() {
  const router = useRouter();
  const [inputValue, setInputValue] = useState("");

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
              {getGreeting()}, <span className="font-normal">Dr. Neumann</span>
            </h1>
          </div>

          {/* Input card */}
          <div className="w-full bg-card rounded-2xl border border-border shadow-sm">
            <div className="px-4 py-4">
              <AutoResizeTextarea
                value={inputValue}
                onChange={setInputValue}
                onSubmit={handleSubmit}
                placeholder="How can I help you today?"
              />
            </div>
            <div className="flex items-center justify-end px-4 pb-4">
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

          {/* Quick actions */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {[
              "Review patient panel",
              "Summarize recent labs",
              "Check drug interactions",
              "Prepare for rounds",
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => {
                  setInputValue(suggestion);
                }}
                className="px-4 py-2 rounded-full border border-border bg-card text-sm text-muted-foreground hover:text-foreground hover:border-foreground/20 transition-colors"
              >
                {suggestion}
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
