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
  StreamToolCallEvent,
  StreamToolResultEvent,
  ReasoningEffort,
} from "@/lib/types";
import { isChatResponse, DEFAULT_MODEL } from "@/lib/types";

/** Streaming phase for progressive UI updates */
export type StreamPhase = "tool_calling" | "reasoning" | "narrative" | "done";

/** A tool call with its result (populated when complete) */
export interface ToolCallState {
  name: string;
  callId: string;
  arguments: string;
  result?: string;
}

/** Streaming state attached to an in-flight assistant message */
export interface StreamingState {
  phase: StreamPhase;
  reasoningText: string;
  narrativeText: string;
  /** Tool calls made during this response */
  toolCalls: ToolCallState[];
  /** How long reasoning took in ms (set when phase transitions to done) */
  reasoningDurationMs?: number;
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
  /** Current reasoning effort level */
  reasoningEffort: ReasoningEffort;
  /** Change the reasoning effort */
  setReasoningEffort: (effort: ReasoningEffort) => void;
}

/** Generate a unique message ID */
function generateMessageId(): string {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

// ---------------------------------------------------------------------------
// Streaming state reducer — pure function for SSE event → state transitions
// ---------------------------------------------------------------------------

type StreamAction =
  | { type: "tool_call"; data: StreamToolCallEvent }
  | { type: "tool_result"; data: StreamToolResultEvent }
  | { type: "reasoning"; data: StreamDeltaEvent }
  | { type: "narrative"; data: StreamDeltaEvent }
  | { type: "done"; data: StreamDoneEvent; reasoningDurationMs?: number }
  | { type: "error" };

const INITIAL_STREAMING_STATE: StreamingState = {
  phase: "reasoning",
  reasoningText: "",
  narrativeText: "",
  toolCalls: [],
};

/**
 * Apply an SSE event to a message's streaming state.
 * Returns a new message object (or the same one if no update needed).
 */
function applyStreamEvent(
  msg: DisplayMessage,
  action: StreamAction,
): DisplayMessage {
  const s = msg.streaming ?? { ...INITIAL_STREAMING_STATE };

  switch (action.type) {
    case "tool_call":
      return {
        ...msg,
        streaming: {
          ...s,
          phase: "tool_calling",
          toolCalls: [
            ...s.toolCalls,
            {
              name: action.data.name,
              callId: action.data.call_id,
              arguments: action.data.arguments,
            },
          ],
        },
      };

    case "tool_result":
      return {
        ...msg,
        streaming: {
          ...s,
          toolCalls: s.toolCalls.map((tc) =>
            tc.callId === action.data.call_id
              ? { ...tc, result: action.data.output }
              : tc
          ),
        },
      };

    case "reasoning": {
      const updated: StreamingState = {
        ...s,
        phase: "reasoning",
        reasoningText: s.reasoningText + action.data.delta,
      };
      return { ...msg, streaming: updated, content: updated.narrativeText };
    }

    case "narrative": {
      const updated: StreamingState = {
        ...s,
        phase: "narrative",
        narrativeText: s.narrativeText + action.data.delta,
      };
      return { ...msg, streaming: updated, content: updated.narrativeText };
    }

    case "done":
      return {
        ...msg,
        content: action.data.response.narrative,
        agentResponse: action.data.response,
        streaming: {
          phase: "done",
          reasoningText: s.reasoningText,
          narrativeText: action.data.response.narrative,
          toolCalls: s.toolCalls,
          reasoningDurationMs: action.reasoningDurationMs,
        },
        pending: false,
      };

    case "error":
      return { ...msg, streaming: undefined, pending: false };
  }
}

/** Update a specific message in the messages array by ID using applyStreamEvent. */
function updateMessage(
  messages: DisplayMessage[],
  targetId: string,
  action: StreamAction,
): DisplayMessage[] {
  const idx = messages.findIndex((m) => m.id === targetId);
  if (idx === -1) return messages;
  const next = [...messages];
  next[idx] = applyStreamEvent(messages[idx], action);
  return next;
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
 * @param sessionId - Optional session ID to persist messages to.
 * @returns Chat state and controls
 */
export function useChat(patientId: string | null, sessionId?: string): UseChatReturn {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ChatError | null>(null);
  const [model, setModel] = useState<ModelId>(DEFAULT_MODEL);
  const [reasoningEffort, setReasoningEffort] = useState<ReasoningEffort>("medium");

  // Store conversation_id across messages
  const conversationIdRef = useRef<string | null>(null);

  // Store last failed message for retry
  const lastFailedMessageRef = useRef<string | null>(null);

  // Track previous patientId to detect changes
  const previousPatientIdRef = useRef<string | null>(null);

  // Track previous sessionId to detect changes
  const previousSessionIdRef = useRef<string | undefined>(undefined);

  // Track if session has been initialized
  const sessionInitializedRef = useRef(false);

  // Track the actual database session ID (may differ from URL sessionId)
  const dbSessionIdRef = useRef<string | null>(null);

  // AbortController for cancelling in-flight streams
  const abortControllerRef = useRef<AbortController | null>(null);

  // Track when reasoning started for duration calculation
  const reasoningStartRef = useRef<number | null>(null);

  // Ref to access latest messages without adding to dependency arrays
  const messagesRef = useRef<DisplayMessage[]>(messages);
  messagesRef.current = messages;

  // Abort in-flight stream on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Initialize or load session
  useEffect(() => {
    if (!sessionId || !patientId) return;
    if (sessionInitializedRef.current && previousSessionIdRef.current === sessionId) return;

    sessionInitializedRef.current = false;
    previousSessionIdRef.current = sessionId;

    // Try to load existing session or create new one
    const initSession = async () => {
      try {
        // First, try to get existing session
        const getRes = await fetch(`/api/sessions/${sessionId}`);

        if (getRes.ok) {
          // Session exists, load its messages
          const session = await getRes.json();
          dbSessionIdRef.current = session.id;
          if (session.messages && session.messages.length > 0) {
            const loadedMessages: DisplayMessage[] = session.messages.map((msg: ChatMessage, idx: number) => ({
              id: `loaded_${idx}_${Date.now()}`,
              role: msg.role,
              content: msg.content,
              timestamp: new Date(),
              pending: false,
            }));
            setMessages(loadedMessages);
          }
          sessionInitializedRef.current = true;
        } else if (getRes.status === 404) {
          // Session doesn't exist, create it
          const createRes = await fetch("/api/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ patient_id: patientId }),
          });
          if (createRes.ok) {
            const newSession = await createRes.json();
            dbSessionIdRef.current = newSession.id;
          } else {
            console.error("Failed to create session:", await createRes.text());
          }
          sessionInitializedRef.current = true;
        }
      } catch (err) {
        console.error("Failed to initialize session:", err);
      }
    };

    initSession();
  }, [sessionId, patientId]);

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
      sessionInitializedRef.current = false;
      dbSessionIdRef.current = null;
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

            if (evt.event === "tool_call") {
              setMessages((prev) => updateMessage(prev, assistantMessageId, {
                type: "tool_call",
                data: data as StreamToolCallEvent,
              }));
            } else if (evt.event === "tool_result") {
              setMessages((prev) => updateMessage(prev, assistantMessageId, {
                type: "tool_result",
                data: data as StreamToolResultEvent,
              }));
            } else if (evt.event === "reasoning" || evt.event === "narrative") {
              if (evt.event === "reasoning" && reasoningStartRef.current === null) {
                reasoningStartRef.current = Date.now();
              }
              setMessages((prev) => updateMessage(prev, assistantMessageId, {
                type: evt.event as "reasoning" | "narrative",
                data: data as StreamDeltaEvent,
              }));
            } else if (evt.event === "done") {
              const parsed = data as StreamDoneEvent;
              conversationIdRef.current = parsed.conversation_id;
              const reasoningDurationMs = reasoningStartRef.current
                ? Date.now() - reasoningStartRef.current
                : undefined;
              reasoningStartRef.current = null;
              setMessages((prev) => updateMessage(prev, assistantMessageId, {
                type: "done",
                data: parsed,
                reasoningDurationMs,
              }));
              lastFailedMessageRef.current = null;
              return true;
            } else if (evt.event === "error") {
              const parsed = data as StreamErrorEvent;
              setMessages((prev) => updateMessage(prev, assistantMessageId, {
                type: "error",
              }));
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
          toolCalls: [],
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
          session_id: dbSessionIdRef.current ?? undefined,
          conversation_history:
            conversationHistory.length > 0 ? conversationHistory : undefined,
          model,
          reasoning_effort: reasoningEffort !== "medium" ? reasoningEffort : undefined,
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
    [patientId, sessionId, model, reasoningEffort, sendStreaming, sendNonStreaming]
  );

  const retry = useCallback(async (): Promise<void> => {
    if (lastFailedMessageRef.current) {
      await sendMessage(lastFailedMessageRef.current);
    }
  }, [sendMessage]);

  // NOTE: Client-side persistence is disabled. The backend now handles message
  // persistence in the chat endpoint (fire-and-forget pattern). This prevents
  // race conditions where frontend overwrites backend-persisted messages.

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
    reasoningEffort,
    setReasoningEffort,
  };
}
