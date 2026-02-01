/**
 * useChat - React hook for chat state management.
 *
 * Manages conversation state, message history, and API interactions
 * for the clinical reasoning chat interface. Streams responses via SSE
 * with fallback to non-streaming endpoint.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  AgentResponse,
  ModelId,
  StreamDeltaEvent,
  StreamDoneEvent,
  StreamErrorEvent,
} from "@/lib/types";
import { isChatResponse, DEFAULT_MODEL } from "@/lib/types";

/** Streaming phase for progressive UI updates */
export type StreamPhase = "reasoning" | "narrative" | "done";

/** Streaming state attached to an in-flight assistant message */
export interface StreamingState {
  phase: StreamPhase;
  reasoningText: string;
  narrativeText: string;
}

/** Extended message type that includes agent response metadata */
export interface DisplayMessage extends ChatMessage {
  /** Unique ID for React keys and optimistic updates */
  id: string;
  /** Timestamp when message was created */
  timestamp: Date;
  /** Full agent response for assistant messages (includes insights, visualizations, etc.) */
  agentResponse?: AgentResponse;
  /** Whether this message is currently being sent */
  pending?: boolean;
  /** Streaming state while response is being generated */
  streaming?: StreamingState;
}

/** Error type for chat operations */
export interface ChatError {
  message: string;
  retryable: boolean;
}

/** Return type for useChat hook */
export interface UseChatReturn {
  /** All messages in the conversation */
  messages: DisplayMessage[];
  /** Send a new message to the chat */
  sendMessage: (content: string) => Promise<void>;
  /** Whether a message is currently being sent */
  isLoading: boolean;
  /** Current error state, null if no error */
  error: ChatError | null;
  /** Clear the error state */
  clearError: () => void;
  /** Retry the last failed message */
  retry: () => Promise<void>;
  /** Clear all messages and start fresh */
  clearMessages: () => void;
  /** Cancel the current streaming response */
  cancelStream: () => void;
  /** Currently selected model */
  model: ModelId;
  /** Change the model */
  setModel: (model: ModelId) => void;
}

/** Generate a unique message ID */
function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Parse SSE lines from a text chunk. Handles buffered partial lines.
 * Returns parsed events and any remaining incomplete line.
 */
function parseSSEChunk(
  buffer: string,
  chunk: string
): { events: Array<{ event: string; data: string }>; remaining: string } {
  const text = buffer + chunk;
  const events: Array<{ event: string; data: string }> = [];
  const lines = text.split("\n");

  // Last element may be an incomplete line
  const remaining = lines.pop() ?? "";

  let currentEvent = "";
  let currentData = "";

  for (const line of lines) {
    if (line.startsWith("event: ")) {
      currentEvent = line.slice(7).trim();
    } else if (line.startsWith("data: ")) {
      currentData = line.slice(6);
    } else if (line === "") {
      // Empty line = end of event
      if (currentEvent && currentData) {
        events.push({ event: currentEvent, data: currentData });
      }
      currentEvent = "";
      currentData = "";
    }
  }

  return { events, remaining };
}

/**
 * React hook for managing chat state and API interactions.
 *
 * @param patientId - The patient ID to chat about. When this changes,
 *                    the conversation is reset.
 * @returns Chat state and controls
 */
export function useChat(patientId: string | null): UseChatReturn {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ChatError | null>(null);
  const [model, setModel] = useState<ModelId>(DEFAULT_MODEL);

  // Store conversation_id across messages
  const conversationIdRef = useRef<string | null>(null);

  // Store last failed message for retry
  const lastFailedMessageRef = useRef<string | null>(null);

  // Track previous patientId to detect changes
  const previousPatientIdRef = useRef<string | null>(null);

  // AbortController for cancelling in-flight streams
  const abortControllerRef = useRef<AbortController | null>(null);

  // Ref to access latest messages without adding to dependency arrays
  const messagesRef = useRef<DisplayMessage[]>(messages);
  messagesRef.current = messages;

  // Abort in-flight stream on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Reset conversation when patient changes
  useEffect(() => {
    if (previousPatientIdRef.current !== patientId) {
      setMessages([]);
      setError(null);
      setIsLoading(false);
      conversationIdRef.current = null;
      lastFailedMessageRef.current = null;
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      previousPatientIdRef.current = patientId;
    }
  }, [patientId]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
    conversationIdRef.current = null;
    lastFailedMessageRef.current = null;
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsLoading(false);
    // Finalize any in-flight streaming message by clearing streaming state
    setMessages((prev) =>
      prev.map((msg) =>
        msg.streaming
          ? { ...msg, streaming: undefined, pending: false }
          : msg
      )
    );
  }, []);

  /**
   * Send via SSE streaming endpoint. Returns true on success, false if
   * streaming failed and caller should fall back to non-streaming.
   */
  const sendStreaming = useCallback(
    async (
      request: ChatRequest,
      assistantMessageId: string,
      signal: AbortSignal
    ): Promise<boolean> => {
      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal,
      });

      if (!response.ok || !response.body) {
        return false;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let sseBuffer = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const { events, remaining } = parseSSEChunk(sseBuffer, chunk);
          sseBuffer = remaining;

          for (const evt of events) {
            let data: unknown;
            try {
              data = JSON.parse(evt.data);
            } catch {
              continue; // Skip malformed SSE data
            }

            if (evt.event === "reasoning" || evt.event === "narrative") {
              const parsed = data as StreamDeltaEvent;
              const phase = evt.event as StreamPhase;

              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === assistantMessageId);
                if (idx === -1) return prev;
                const msg = prev[idx];
                const s = msg.streaming ?? {
                  phase: "reasoning",
                  reasoningText: "",
                  narrativeText: "",
                };
                const updated: StreamingState = {
                  ...s,
                  phase,
                  ...(phase === "reasoning"
                    ? { reasoningText: s.reasoningText + parsed.delta }
                    : { narrativeText: s.narrativeText + parsed.delta }),
                };
                const next = [...prev];
                next[idx] = {
                  ...msg,
                  streaming: updated,
                  content: updated.narrativeText,
                };
                return next;
              });
            } else if (evt.event === "done") {
              const parsed = data as StreamDoneEvent;
              conversationIdRef.current = parsed.conversation_id;

              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === assistantMessageId);
                if (idx === -1) return prev;
                const msg = prev[idx];
                const next = [...prev];
                next[idx] = {
                  ...msg,
                  content: parsed.response.narrative,
                  agentResponse: parsed.response,
                  streaming: {
                    phase: "done" as StreamPhase,
                    reasoningText: msg.streaming?.reasoningText ?? "",
                    narrativeText: parsed.response.narrative,
                  },
                  pending: false,
                };
                return next;
              });
              lastFailedMessageRef.current = null;
              return true;
            } else if (evt.event === "error") {
              const parsed = data as StreamErrorEvent;
              // Clean up streaming state before throwing
              setMessages((prev) => {
                const idx = prev.findIndex((m) => m.id === assistantMessageId);
                if (idx === -1) return prev;
                const next = [...prev];
                next[idx] = {
                  ...prev[idx],
                  streaming: undefined,
                  pending: false,
                };
                return next;
              });
              throw new Error(parsed.detail);
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // If we got here without a done event, treat as failure
      return false;
    },
    []
  );

  /**
   * Fallback: send via non-streaming endpoint.
   */
  const sendNonStreaming = useCallback(
    async (
      request: ChatRequest,
      assistantMessageId: string,
      signal: AbortSignal
    ): Promise<void> => {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.error || `Request failed with status ${response.status}`;
        const retryable = response.status >= 500 || response.status === 429;
        throw new Error(JSON.stringify({ message: errorMessage, retryable }));
      }

      const data: unknown = await response.json();

      if (!isChatResponse(data)) {
        throw new Error(
          JSON.stringify({
            message: "Invalid response from server",
            retryable: true,
          })
        );
      }

      const chatResponse = data as ChatResponse;
      conversationIdRef.current = chatResponse.conversation_id;

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== assistantMessageId) return msg;
          return {
            ...msg,
            content: chatResponse.response.narrative,
            agentResponse: chatResponse.response,
            streaming: undefined,
            pending: false,
          };
        })
      );

      lastFailedMessageRef.current = null;
    },
    []
  );

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (!patientId) {
        setError({ message: "No patient selected", retryable: false });
        return;
      }

      if (!content.trim()) return;

      // Abort any existing stream
      abortControllerRef.current?.abort();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setError(null);
      lastFailedMessageRef.current = content;

      const userMessage: DisplayMessage = {
        id: generateMessageId(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
        pending: false,
      };

      const assistantMessageId = generateMessageId();
      const assistantMessage: DisplayMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        pending: true,
        streaming: {
          phase: "reasoning",
          reasoningText: "",
          narrativeText: "",
        },
      };

      setMessages((prev) => [...prev, userMessage, assistantMessage]);
      setIsLoading(true);

      try {
        const conversationHistory: ChatMessage[] = messagesRef.current
          .filter((msg) => !msg.pending)
          .map((msg) => ({ role: msg.role, content: msg.content }));

        const request: ChatRequest = {
          patient_id: patientId,
          message: content.trim(),
          conversation_id: conversationIdRef.current ?? undefined,
          conversation_history:
            conversationHistory.length > 0 ? conversationHistory : undefined,
          model,
        };

        // Try streaming first, fall back to non-streaming
        let success = false;
        try {
          success = await sendStreaming(
            request,
            assistantMessageId,
            controller.signal
          );
        } catch (err) {
          if (controller.signal.aborted) throw err;
          // Stream failed — fall through to fallback
        }

        if (!success && !controller.signal.aborted) {
          // Reset the assistant message for fallback
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                    ...msg,
                    content: "",
                    streaming: undefined,
                    pending: true,
                  }
                : msg
            )
          );
          await sendNonStreaming(request, assistantMessageId, controller.signal);
        }
      } catch (err) {
        if (controller.signal.aborted) {
          // User cancelled — don't set error, just clean up
          return;
        }

        let chatError: ChatError;
        if (err instanceof Error) {
          try {
            chatError = JSON.parse(err.message) as ChatError;
          } catch {
            chatError = {
              message: err.message || "An unexpected error occurred",
              retryable: true,
            };
          }
        } else {
          chatError = {
            message: "An unexpected error occurred",
            retryable: true,
          };
        }

        setError(chatError);
        // Remove both the user message and the placeholder assistant message
        setMessages((prev) =>
          prev.filter(
            (msg) =>
              msg.id !== userMessage.id && msg.id !== assistantMessageId
          )
        );
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        setIsLoading(false);
      }
    },
    [patientId, model, sendStreaming, sendNonStreaming]
  );

  const retry = useCallback(async (): Promise<void> => {
    if (lastFailedMessageRef.current) {
      await sendMessage(lastFailedMessageRef.current);
    }
  }, [sendMessage]);

  return {
    messages,
    sendMessage,
    isLoading,
    error,
    clearError,
    retry,
    clearMessages,
    cancelStream,
    model,
    setModel,
  };
}
