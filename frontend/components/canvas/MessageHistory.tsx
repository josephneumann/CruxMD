"use client";

import { useRef, useEffect } from "react";
import type { DisplayMessage } from "@/hooks";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";
import { ThinkingIndicator } from "./ThinkingIndicator";

interface MessageHistoryProps {
  messages: DisplayMessage[];
  isLoading: boolean;
  lottieData: object | null;
  onFollowUpSelect: (question: string) => void;
}

export function MessageHistory({
  messages,
  isLoading,
  lottieData,
  onFollowUpSelect,
}: MessageHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-8">
        {messages.map((message) =>
          message.role === "user" ? (
            <UserMessage key={message.id} message={message} />
          ) : (
            <AgentMessage
              key={message.id}
              message={message}
              onFollowUpSelect={onFollowUpSelect}
            />
          )
        )}

        {isLoading && <ThinkingIndicator lottieData={lottieData} />}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
