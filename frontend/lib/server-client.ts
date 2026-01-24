/**
 * Server-side API client configuration.
 *
 * This module provides a pre-configured client for server components
 * that includes authentication headers.
 */

import { createClient, createConfig } from "./generated/client";
import type { Auth } from "./generated/client";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Get API key for server-side requests.
 * Server components should use this client for authenticated API calls.
 */
function getApiKey(): string {
  const key = process.env.API_KEY;
  if (!key) {
    console.warn("API_KEY not set, using empty string");
    return "";
  }
  return key;
}

/**
 * Pre-configured client for server-side usage with authentication.
 */
export const serverClient = createClient(
  createConfig({
    baseUrl: API_BASE_URL,
    auth: (auth: Auth) => {
      // Return the API key for X-API-Key header auth
      if (auth.type === "apiKey") {
        return getApiKey();
      }
      return undefined;
    },
  })
);
