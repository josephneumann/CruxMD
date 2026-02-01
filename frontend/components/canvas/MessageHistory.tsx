"use client";

import { useRef, useEffect } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import type { DisplayMessage } from "@/hooks";
import { UserMessage } from "./UserMessage";
import { AgentMessage } from "./AgentMessage";
import { ThinkingIndicator } from "./ThinkingIndicator";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

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

        {isLoading && (() => {
          const streamingMsg = messages.find(
            (m) => m.streaming && m.streaming.phase === "reasoning"
          );
          return (
            <ThinkingIndicator
              reasoningText={streamingMsg?.streaming?.reasoningText}
            />
          );
        })()}

        {/* Crux mark — spinning while loading, static when idle */}
        <div className="flex justify-start mt-2 mb-4">
          {isLoading && lottieData ? (
            <div className="w-8 h-8">
              <Lottie
                animationData={lottieData}
                loop
                style={{ width: "100%", height: "100%" }}
              />
            </div>
          ) : (
            <Image
              src="/brand/mark-primary.svg"
              alt=""
              width={28}
              height={28}
              className="opacity-40"
            />
          )}
        </div>

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
