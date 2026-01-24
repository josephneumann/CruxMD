/**
 * API client configuration for CruxMD.
 *
 * Server-side only configuration for making authenticated API requests.
 * The generated SDK in lib/generated/ should be used for type-safe API calls.
 */

/**
 * Base URL for API requests.
 * Uses NEXT_PUBLIC_ for client components that need to know the API origin.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * API key for server-side requests only.
 * This is NOT exposed to the client (no NEXT_PUBLIC_ prefix).
 */
export function getApiKey(): string {
  const key = process.env.API_KEY;
  if (!key) {
    throw new Error("API_KEY environment variable is required");
  }
  return key;
}

/**
 * Get default headers for authenticated API requests.
 * Server-side only - do not use in client components.
 */
export function getAuthHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    "X-API-Key": getApiKey(),
  };
}
