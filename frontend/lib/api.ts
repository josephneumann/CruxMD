/**
 * API client configuration and helpers for CruxMD.
 *
 * This module provides a configured fetch client for making API requests
 * to the backend. It handles base URL configuration and authentication.
 */

/**
 * Base URL for API requests.
 * In development, this points to the local FastAPI backend.
 * In production, it can be overridden via NEXT_PUBLIC_API_URL.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * API key for authenticating requests.
 * This should be set in environment variables for production.
 */
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "dev-api-key";

/**
 * Default headers for API requests.
 */
export const defaultHeaders: HeadersInit = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

/**
 * Configured fetch function for making API requests.
 * Automatically includes authentication and base URL.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      error.detail || response.statusText,
      error
    );
  }

  return response.json();
}

/**
 * Custom error class for API errors with status code and details.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}
