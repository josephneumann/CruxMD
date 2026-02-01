/**
 * useChat - React hook for chat state management.
 *
 * Manages conversation state, message history, and API interactions
 * for the clinical reasoning chat interface.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type {
  ChatMessage,
  ChatRequest,
  ChatResponse,
  AgentResponse,
  ModelId,
} from "@/lib/types";
import { isChatResponse, DEFAULT_MODEL } from "@/lib/types";

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
 * React hook for managing chat state and API interactions.
 *
 * @param patientId - The patient ID to chat about. When this changes,
 *                    the conversation is reset.
 * @returns Chat state and controls
 *
 * @example
 * ```tsx
 * function ChatComponent({ patientId }: { patientId: string }) {
 *   const { messages, sendMessage, isLoading, error } = useChat(patientId);
 *
 *   return (
 *     <div>
 *       {messages.map((msg) => (
 *         <Message key={msg.id} message={msg} />
 *       ))}
 *       {isLoading && <LoadingIndicator />}
 *       {error && <ErrorBanner error={error} />}
 *       <MessageInput onSend={sendMessage} disabled={isLoading} />
 *     </div>
 *   );
 * }
 * ```
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

  // Reset conversation when patient changes
  useEffect(() => {
    if (previousPatientIdRef.current !== patientId) {
      // Patient changed - clear everything
      setMessages([]);
      setError(null);
      setIsLoading(false);
      conversationIdRef.current = null;
      lastFailedMessageRef.current = null;
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
  }, []);

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      if (!patientId) {
        setError({
          message: "No patient selected",
          retryable: false,
        });
        return;
      }

      if (!content.trim()) {
        return;
      }

      // Clear any previous error
      setError(null);
      lastFailedMessageRef.current = content;

      // Create optimistic user message
      const userMessage: DisplayMessage = {
        id: generateMessageId(),
        role: "user",
        content: content.trim(),
        timestamp: new Date(),
        pending: false,
      };

      // Add user message to state
      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        // Build conversation history from existing messages (excluding pending)
        const conversationHistory: ChatMessage[] = messages
          .filter((msg) => !msg.pending)
          .map((msg) => ({
            role: msg.role,
            content: msg.content,
          }));

        // Build request
        const request: ChatRequest = {
          patient_id: patientId,
          message: content.trim(),
          conversation_id: conversationIdRef.current ?? undefined,
          conversation_history:
            conversationHistory.length > 0 ? conversationHistory : undefined,
          model,
        };

        // Make API call to Next.js API route
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const errorMessage =
            errorData.error || `Request failed with status ${response.status}`;

          // Determine if error is retryable
          const retryable = response.status >= 500 || response.status === 429;

          throw new Error(
            JSON.stringify({ message: errorMessage, retryable })
          );
        }

        const data: unknown = await response.json();

        // Validate response
        if (!isChatResponse(data)) {
          throw new Error(
            JSON.stringify({
              message: "Invalid response from server",
              retryable: true,
            })
          );
        }

        const chatResponse = data as ChatResponse;

        // Store conversation_id for future messages
        conversationIdRef.current = chatResponse.conversation_id;

        // Create assistant message with full agent response
        const assistantMessage: DisplayMessage = {
          id: generateMessageId(),
          role: "assistant",
          content: chatResponse.response.narrative,
          timestamp: new Date(),
          agentResponse: chatResponse.response,
          pending: false,
        };

        // Add assistant message
        setMessages((prev) => [...prev, assistantMessage]);

        // Clear last failed message on success
        lastFailedMessageRef.current = null;
      } catch (err) {
        // Parse error details
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

        // Remove the optimistic user message on error
        setMessages((prev) => prev.filter((msg) => msg.id !== userMessage.id));
      } finally {
        setIsLoading(false);
      }
    },
    [patientId, messages, model]
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
    model,
    setModel,
  };
}
