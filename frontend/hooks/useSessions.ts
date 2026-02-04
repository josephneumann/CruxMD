/**
 * useSessions - React hook for session state management.
 *
 * Manages conversation sessions, including fetching, deleting,
 * and filtering by patient.
 */

import { useState, useCallback, useEffect } from "react";
import type { SessionResponse } from "@/lib/types";
import { isSessionListResponse } from "@/lib/types";

/** Error type for session operations */
export interface SessionError {
  message: string;
  retryable: boolean;
}

/** Session update payload */
export interface SessionUpdatePayload {
  name?: string;
  summary?: string;
  status?: "active" | "completed";
}

/** Return type for useSessions hook */
export interface UseSessionsReturn {
  /** All sessions matching the filter */
  sessions: SessionResponse[];
  /** Total count of matching sessions */
  total: number;
  /** Whether sessions are currently being loaded */
  isLoading: boolean;
  /** Current error state, null if no error */
  error: SessionError | null;
  /** Clear the error state */
  clearError: () => void;
  /** Refresh the sessions list */
  refresh: () => Promise<void>;
  /** Delete a session */
  deleteSession: (sessionId: string) => Promise<void>;
  /** Update a session */
  updateSession: (sessionId: string, updates: SessionUpdatePayload) => Promise<void>;
}

/**
 * React hook for managing sessions state.
 *
 * @param patientId - Optional patient ID filter
 * @returns Session state and controls
 */
export function useSessions(patientId?: string): UseSessionsReturn {
  const [sessions, setSessions] = useState<SessionResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<SessionError | null>(null);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const fetchSessions = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (patientId) params.set("patient_id", patientId);
      params.set("limit", "100"); // Get more sessions at once

      const queryString = params.toString();
      const url = `/api/sessions${queryString ? `?${queryString}` : ""}`;

      const response = await fetch(url);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Request failed with status ${response.status}`
        );
      }

      const data: unknown = await response.json();

      if (!isSessionListResponse(data)) {
        throw new Error("Invalid response from server");
      }

      setSessions(data.items);
      setTotal(data.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred";
      setError({ message, retryable: true });
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  const deleteSession = useCallback(async (sessionId: string) => {
    setError(null);

    try {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: "DELETE",
      });

      if (!response.ok && response.status !== 204) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to delete session: ${response.status}`
        );
      }

      // Refresh list after deleting
      await fetchSessions();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete session";
      setError({ message, retryable: true });
    }
  }, [fetchSessions]);

  const updateSession = useCallback(async (sessionId: string, updates: SessionUpdatePayload) => {
    setError(null);

    try {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to update session: ${response.status}`
        );
      }

      // Refresh list after updating
      await fetchSessions();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update session";
      setError({ message, retryable: true });
    }
  }, [fetchSessions]);

  // Fetch on mount and when filters change
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    total,
    isLoading,
    error,
    clearError,
    refresh: fetchSessions,
    deleteSession,
    updateSession,
  };
}
