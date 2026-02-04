"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Image from "next/image";
import { useTheme } from "next-themes";
import { useChat } from "@/hooks";
import { MessageHistory } from "./MessageHistory";
import { ChatInput } from "./ChatInput";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  getPatientDisplayName,
  getPatientInitials,
  getPatientAvatarUrl,
  formatFhirDate,
  calculateAge,
} from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface ConversationalCanvasProps {
  patient: PatientListItem | null;
  initialMessage?: string;
}

export function ConversationalCanvas({ patient, initialMessage }: ConversationalCanvasProps) {
  const patientId = patient?.id ?? null;
  const { messages, sendMessage, isLoading, error, clearError, retry, model, setModel, reasoningEffort, setReasoningEffort } = useChat(patientId);
  const [inputValue, setInputValue] = useState("");
  const [lottieLight, setLottieLight] = useState<object | null>(null);
  const [lottieDark, setLottieDark] = useState<object | null>(null);
  const { resolvedTheme } = useTheme();
  const initialSentRef = useRef(false);

  // Load both Lottie animations
  useEffect(() => {
    fetch("/brand/animations/crux-spin.json")
      .then((res) => res.json())
      .then(setLottieLight)
      .catch((err) => console.error("Failed to load animation:", err));
    fetch("/brand/animations/crux-spin-reversed.json")
      .then((res) => res.json())
      .then(setLottieDark)
      .catch((err) => console.error("Failed to load reversed animation:", err));
  }, []);

  const lottieData = resolvedTheme === "dark" ? lottieDark : lottieLight;

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
        <div className="flex-1 flex items-center justify-center max-w-3xl mx-auto w-full">
          <p className="text-muted-foreground">Select a patient to begin a conversation.</p>
        </div>
      ) : messages.length === 0 && !isLoading ? (
        <div className="flex-1 flex items-center justify-center max-w-3xl mx-auto w-full">
          {patient ? (
            <PatientEmptyState patient={patient} />
          ) : (
            <p className="text-muted-foreground">Send a message to start the conversation.</p>
          )}
        </div>
      ) : (
        <MessageHistory
          messages={messages}
          isLoading={isLoading}
          lottieData={lottieData}
          onFollowUpSelect={handleFollowUpSelect}
          onRetry={handleFollowUpSelect}
        />
      )}

      <ChatInput
        value={inputValue}
        onChange={setInputValue}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        disabled={!patientId}
        model={model}
        onModelChange={setModel}
        reasoningEffort={reasoningEffort}
        onReasoningEffortChange={setReasoningEffort}
      />
    </div>
  );
}

function PatientEmptyState({ patient }: { patient: PatientListItem }) {
  const { data } = patient;
  const name = getPatientDisplayName(data);
  const initials = getPatientInitials(data);
  const avatarSrc = getPatientAvatarUrl(data);
  const age = calculateAge(data.birthDate);
  const dob = data.birthDate ? formatFhirDate(data.birthDate) : null;

  return (
    <div className="flex flex-col items-center text-center">
      <Avatar className="size-32 mb-4">
        <AvatarImage src={avatarSrc} alt={name} className="object-cover" />
        <AvatarFallback className="bg-primary/20 text-primary text-xl font-medium">
          {initials}
        </AvatarFallback>
      </Avatar>
      <h2 className="text-lg font-semibold text-foreground">{name}</h2>
      <p className="text-sm text-muted-foreground mt-1">
        {age !== null && `${age}y`}
        {age !== null && data.gender && ", "}
        {data.gender && <span className="capitalize">{data.gender}</span>}
        {dob && ` · DOB: ${dob}`}
      </p>
    </div>
  );
}
