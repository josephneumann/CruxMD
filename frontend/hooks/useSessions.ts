/**
 * useSessions - React hook for session state management.
 *
 * Manages paused conversation sessions, including fetching, resuming,
 * and filtering by status and patient.
 */

import { useState, useCallback, useEffect } from "react";
import type { SessionResponse, SessionStatus } from "@/lib/types";
import { isSessionListResponse } from "@/lib/types";

/** Error type for session operations */
export interface SessionError {
  message: string;
  retryable: boolean;
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
  /** Resume a paused session (sets status to active) */
  resumeSession: (sessionId: string) => Promise<void>;
}

/**
 * React hook for managing sessions state.
 *
 * @param status - Optional status filter (e.g., 'paused')
 * @param patientId - Optional patient ID filter
 * @returns Session state and controls
 */
export function useSessions(
  status?: SessionStatus,
  patientId?: string
): UseSessionsReturn {
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
      if (status) params.set("status", status);
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
  }, [status, patientId]);

  const resumeSession = useCallback(async (sessionId: string) => {
    setError(null);

    try {
      const response = await fetch(`/api/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "active" }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to resume session: ${response.status}`
        );
      }

      // Refresh list after resuming
      await fetchSessions();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to resume session";
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
    resumeSession,
  };
}
