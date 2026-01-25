/**
 * Chat API route - proxies chat requests to the backend with authentication.
 *
 * This server-side route handles authentication so the API key is never
 * exposed to the client. It validates the request, forwards it to the
 * backend, and returns the response.
 */

import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import type { ChatRequest, ChatResponse } from "@/lib/types";
import { isChatResponse } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as ChatRequest;

    // Basic validation
    if (!body.patient_id || !body.message) {
      return NextResponse.json(
        { error: "patient_id and message are required" },
        { status: 400 }
      );
    }

    // Forward to backend with authentication
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = "Chat request failed";

      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        // Use default error message
      }

      return NextResponse.json(
        { error: errorMessage },
        { status: response.status }
      );
    }

    const data: unknown = await response.json();

    // Validate response structure
    if (!isChatResponse(data)) {
      console.error("Invalid response from backend:", data);
      return NextResponse.json(
        { error: "Invalid response from server" },
        { status: 500 }
      );
    }

    return NextResponse.json(data satisfies ChatResponse);
  } catch (error) {
    console.error("Chat API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
