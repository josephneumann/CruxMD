"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useChat } from "@/hooks";
import { MessageHistory } from "./MessageHistory";
import { ChatInput } from "./ChatInput";

interface ConversationalCanvasProps {
  patientId: string | null;
  initialMessage?: string;
}

export function ConversationalCanvas({ patientId, initialMessage }: ConversationalCanvasProps) {
  const { messages, sendMessage, isLoading, error, clearError, retry } = useChat(patientId);
  const [inputValue, setInputValue] = useState("");
  const [lottieData, setLottieData] = useState<object | null>(null);
  const initialSentRef = useRef(false);

  // Load Lottie animation
  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then(setLottieData)
      .catch((err) => console.error("Failed to load animation:", err));
  }, []);

  // Send initial message from URL if provided
  useEffect(() => {
    if (initialMessage && !initialSentRef.current && patientId) {
      initialSentRef.current = true;
      sendMessage(initialMessage);
    }
  }, [initialMessage, patientId, sendMessage]);

  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isLoading) return;
    const msg = inputValue.trim();
    setInputValue("");
    sendMessage(msg);
  }, [inputValue, isLoading, sendMessage]);

  const handleFollowUpSelect = useCallback(
    (question: string) => {
      if (isLoading) return;
      sendMessage(question);
    },
    [isLoading, sendMessage]
  );

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Error banner */}
      {error && (
        <div className="bg-destructive/10 border-b border-destructive/20 px-4 py-3">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <p className="text-sm text-destructive">{error.message}</p>
            <div className="flex items-center gap-2">
              {error.retryable && (
                <button
                  onClick={retry}
                  className="text-sm text-destructive underline hover:no-underline"
                >
                  Retry
                </button>
              )}
              <button
                onClick={clearError}
                className="text-sm text-destructive/60 hover:text-destructive"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* No patient selected state */}
      {!patientId ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">Select a patient to begin a conversation.</p>
        </div>
      ) : messages.length === 0 && !isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">Send a message to start the conversation.</p>
        </div>
      ) : (
        <MessageHistory
          messages={messages}
          isLoading={isLoading}
          lottieData={lottieData}
          onFollowUpSelect={handleFollowUpSelect}
        />
      )}

      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        disabled={isLoading || !patientId}
      />
    </div>
  );
}
