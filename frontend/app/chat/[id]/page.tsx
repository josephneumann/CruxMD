"use client";

/**
 * Chat Session Page - Conversational canvas for a specific chat session
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  ArrowUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { AutoResizeTextarea } from "@/components/chat/AutoResizeTextarea";
import { StreamingText } from "@/components/chat/StreamingText";
import { useThinkingAnimation } from "@/lib/hooks/use-thinking-animation";
import { THINKING_VERBS } from "@/lib/constants/chat";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  isStreaming?: boolean;
}

export default function ChatSessionPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [lottieData, setLottieData] = useState<object | null>(null);
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const thinkingVerb = useThinkingAnimation(isThinking);

  // Load Lottie animation
  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then(setLottieData);
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Handle initial message from URL params
  useEffect(() => {
    const initialMessage = searchParams.get("message");
    if (initialMessage && messages.length === 0) {
      handleNewMessage(decodeURIComponent(initialMessage));
    }
  }, [searchParams, messages.length]);

  const handleNewMessage = useCallback((content: string) => {
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const messageId = `assistant-${Date.now()}`;
      const assistantMessage: Message = {
        id: messageId,
        role: "assistant",
        content: "CruxMD is not available to the public yet. Try back later.",
        thinking: THINKING_VERBS[Math.floor(Math.random() * THINKING_VERBS.length)] + "...",
        isStreaming: true,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsThinking(false);
      setExpandedThinking((prev) => ({ ...prev, [messageId]: false }));
    }, 2000);
  }, []);

  const handleStreamingComplete = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, isStreaming: false } : m))
    );
  }, []);

  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isThinking) return;
    handleNewMessage(inputValue.trim());
    setInputValue("");
  }, [inputValue, isThinking, handleNewMessage]);

  const toggleThinking = useCallback((messageId: string) => {
    setExpandedThinking((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  }, []);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-8">
            {messages.map((message, index) => {
              const isLastAssistant =
                message.role === "assistant" && index === messages.length - 1;

              return (
                <div key={message.id} className="mb-8">
                  {message.role === "user" ? (
                    <div className="flex justify-end">
                      <div className="bg-muted rounded-2xl px-4 py-3 max-w-[80%]">
                        <p className="text-foreground">{message.content}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {/* Thinking section */}
                      {message.thinking && (
                        <button
                          onClick={() => toggleThinking(message.id)}
                          className="flex items-center justify-between w-full max-w-2xl bg-muted/50 hover:bg-muted rounded-xl px-4 py-3 text-left transition-colors"
                        >
                          <span className="text-sm text-muted-foreground">
                            {message.thinking}
                          </span>
                          {expandedThinking[message.id] ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          )}
                        </button>
                      )}

                      {/* Message content */}
                      <p className="text-foreground">
                        <StreamingText
                          text={message.content}
                          isStreaming={message.isStreaming ?? false}
                          onComplete={() => handleStreamingComplete(message.id)}
                        />
                      </p>

                      {/* Action buttons */}
                      {!message.isStreaming && (
                        <div className="flex items-center gap-1">
                          <ActionButton icon={Copy} label="Copy" />
                          <ActionButton icon={ThumbsUp} label="Good response" />
                          <ActionButton icon={ThumbsDown} label="Bad response" />
                          <ActionButton icon={RotateCcw} label="Retry" />
                        </div>
                      )}

                      {/* Spinner - always visible for last assistant message */}
                      {isLastAssistant && !isThinking && lottieData && (
                        <div className="w-8 h-8 mt-2">
                          <Lottie
                            animationData={lottieData}
                            loop={false}
                            style={{ width: "100%", height: "100%" }}
                          />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Thinking indicator */}
            {isThinking && (
              <div className="mb-8 space-y-3">
                <div className="bg-muted/50 rounded-xl px-4 py-3 w-fit">
                  <span className="text-sm text-muted-foreground animate-pulse">
                    {thinkingVerb}...
                  </span>
                </div>
                {lottieData && (
                  <div className="w-10 h-10">
                    <Lottie
                      animationData={lottieData}
                      loop={true}
                      style={{ width: "100%", height: "100%" }}
                    />
                  </div>
                )}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-border bg-background p-4">
          <div className="max-w-3xl mx-auto">
            <div className="bg-card rounded-2xl border border-border shadow-sm">
              <div className="px-4 py-4">
                <AutoResizeTextarea
                  value={inputValue}
                  onChange={setInputValue}
                  onSubmit={handleSubmit}
                  placeholder="Reply..."
                  disabled={isThinking}
                />
              </div>
              <div className="flex items-center justify-end px-4 pb-4">
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
        </div>
      </main>
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title={label}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
