"use client";

import { useRef, useEffect, useCallback } from "react";
import Image from "next/image";
import { useTheme } from "next-themes";
import type { DisplayMessage } from "@/hooks";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";
import { ThinkingIndicator } from "./ThinkingIndicator";

interface MessageHistoryProps {
  messages: DisplayMessage[];
  isLoading: boolean;
  lottieData: object | null;
  onFollowUpSelect: (question: string) => void;
  onRetry: (messageContent: string) => void;
}

export function MessageHistory({
  messages,
  isLoading,
  lottieData,
  onFollowUpSelect,
  onRetry,
}: MessageHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const { resolvedTheme } = useTheme();
  const markSrc = resolvedTheme === "dark" ? "/brand/logos/mark-reversed.svg" : "/brand/logos/mark-primary.svg";

  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolledUpRef = useRef(false);
  const prevMessageCountRef = useRef(messages.length);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    requestAnimationFrame(() => {
      const el = containerRef.current;
      if (el) {
        el.scrollTo({ top: el.scrollHeight, behavior });
      }
    });
  }, []);

  // Track user scroll intent — stop auto-scrolling if user scrolls up
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      userScrolledUpRef.current = distanceFromBottom > 100;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-scroll on new messages or streaming updates
  useEffect(() => {
    const messageCountChanged = messages.length !== prevMessageCountRef.current;
    prevMessageCountRef.current = messages.length;

    if (messageCountChanged) {
      // New message added — always scroll, reset scroll intent
      userScrolledUpRef.current = false;
      scrollToBottom("smooth");
    } else if (!userScrolledUpRef.current) {
      // Streaming content update — scroll instantly to keep up
      scrollToBottom("instant");
    }
  }, [messages, isLoading, scrollToBottom]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 pt-8 pb-36">
        {messages.map((message, index) =>
          message.role === "user" ? (
            <UserMessage key={message.id} message={message} />
          ) : (
            <AgentMessage
              key={message.id}
              message={message}
              onFollowUpSelect={onFollowUpSelect}
              onContentGrow={() => scrollToBottom("instant")}
              onRetry={() => {
                // Find the preceding user message and resend it
                for (let i = index - 1; i >= 0; i--) {
                  if (messages[i].role === "user") {
                    onRetry(messages[i].content);
                    break;
                  }
                }
              }}
            />
          )
        )}

        {isLoading && (() => {
          const streamingMsg = messages.find(
            (m) => m.streaming && m.streaming.phase !== "done"
          );
          return (
            <ThinkingIndicator
              reasoningText={streamingMsg?.streaming?.reasoningText}
              toolCalls={streamingMsg?.streaming?.toolCalls}
              lottieData={lottieData}
            />
          );
        })()}

        {/* Crux mark — static when idle */}
        {!isLoading && (
          <div className="flex justify-start mt-2 mb-4">
            <Image
              src={markSrc}
              alt=""
              width={28}
              height={28}
              className="opacity-40"
            />
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
