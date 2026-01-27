"use client";

/**
 * Chat Session Page - Conversational canvas for a specific chat session
 * Styled like Claude.ai with thinking indicator and message thread
 */

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import Image from "next/image";
import dynamic from "next/dynamic";
import {
  ChevronDown,
  ChevronUp,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
  ArrowUp,
  Plus,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { cn } from "@/lib/utils";

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

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thinking?: string;
}

export default function ChatSessionPage() {
  const params = useParams();
  const sessionId = params.id as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingText, setThinkingText] = useState("");
  const [thinkingVerbIndex, setThinkingVerbIndex] = useState(0);
  const [lottieData, setLottieData] = useState<object | null>(null);
  const [expandedThinking, setExpandedThinking] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load Lottie animation data
  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then((data) => setLottieData(data));
  }, []);

  // Cycle through thinking verbs while thinking
  useEffect(() => {
    if (!isThinking) return;
    const interval = setInterval(() => {
      setThinkingVerbIndex((prev) => (prev + 1) % THINKING_VERBS.length);
    }, 2000);
    return () => clearInterval(interval);
  }, [isThinking]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  // Simulate initial message from URL param or localStorage
  useEffect(() => {
    // Check if there's an initial message stored for this session
    const storedMessage = sessionStorage.getItem(`chat-init-${sessionId}`);
    if (storedMessage) {
      sessionStorage.removeItem(`chat-init-${sessionId}`);
      handleNewMessage(storedMessage);
    }
  }, [sessionId]);

  const handleNewMessage = async (content: string) => {
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);
    setThinkingText("Thinking about the clinical context...");

    // Simulate AI response (replace with actual API call)
    setTimeout(() => {
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: "Hey Joe! Everything's working. What can I help you with today?",
        thinking: "Thinking about the purpose of a test prompt.",
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsThinking(false);
      // Auto-expand thinking for the latest message
      setExpandedThinking((prev) => ({ ...prev, [assistantMessage.id]: false }));
    }, 2000);
  };

  const handleSubmit = () => {
    if (!inputValue.trim() || isThinking) return;
    handleNewMessage(inputValue);
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const toggleThinking = (messageId: string) => {
    setExpandedThinking((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
  };

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <main className="flex-1 flex flex-col">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 py-8">
            {messages.map((message, index) => {
              const isLastAssistantMessage =
                message.role === "assistant" &&
                index === messages.length - 1;

              return (
                <div key={message.id} className="mb-8">
                  {message.role === "user" ? (
                    // User message - right aligned
                    <div className="flex justify-end">
                      <div className="bg-muted rounded-2xl px-4 py-3 max-w-[80%]">
                        <p className="text-foreground">{message.content}</p>
                      </div>
                    </div>
                  ) : (
                    // Assistant message - left aligned with thinking and actions
                    <div className="space-y-3">
                      {/* Thinking section (collapsible) */}
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
                      <p className="text-foreground">{message.content}</p>

                      {/* Action buttons */}
                      <div className="flex items-center gap-1">
                        <ActionButton icon={Copy} label="Copy" />
                        <ActionButton icon={ThumbsUp} label="Good response" />
                        <ActionButton icon={ThumbsDown} label="Bad response" />
                        <ActionButton icon={RotateCcw} label="Retry" />
                      </div>

                      {/* Static mark - show below last assistant message when not thinking */}
                      {isLastAssistantMessage && !isThinking && (
                        <div className="mt-2">
                          <Image
                            src="/brand/mark-primary.svg"
                            alt=""
                            width={32}
                            height={32}
                            className="dark:hidden"
                          />
                          <Image
                            src="/brand/mark-reversed.svg"
                            alt=""
                            width={32}
                            height={32}
                            className="hidden dark:block"
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
                {/* Thinking pill */}
                <div className="flex items-center gap-2 bg-muted/50 rounded-xl px-4 py-3 w-fit">
                  <span className="text-sm text-muted-foreground animate-pulse">
                    {THINKING_VERBS[thinkingVerbIndex]}...
                  </span>
                </div>

                {/* Spinner */}
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

        {/* Input area - fixed at bottom */}
        <div className="border-t border-border bg-background p-4">
          <div className="max-w-3xl mx-auto">
            <div className="bg-card rounded-2xl border border-border shadow-sm">
              {/* Text input */}
              <div className="px-4 py-4">
                <textarea
                  ref={textareaRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Reply..."
                  className="w-full bg-transparent text-foreground placeholder:text-muted-foreground resize-none outline-none text-base min-h-[24px] max-h-[200px]"
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
        </div>
      </main>
    </div>
  );
}

// Action button component
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
