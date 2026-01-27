/**
 * API client configuration for CruxMD.
 *
 * Server-side only configuration for making authenticated API requests.
 * The generated SDK in lib/generated/ should be used for type-safe API calls.
 */

import { auth } from "@/lib/auth";
import { headers } from "next/headers";

/**
 * Base URL for API requests.
 * Uses NEXT_PUBLIC_ for client components that need to know the API origin.
 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Get default headers for authenticated API requests.
 * Server-side only - extracts bearer token from the current session.
 */
export async function getAuthHeaders(): Promise<HeadersInit> {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    throw new Error("No active session");
  }

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.session.token}`,
  };
}
