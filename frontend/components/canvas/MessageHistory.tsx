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
  const markSrc = resolvedTheme === "dark" ? "/brand/mark-reversed.svg" : "/brand/mark-primary.svg";

  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
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
              onContentGrow={scrollToBottom}
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
