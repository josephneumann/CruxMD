/**
 * Chat SSE stream proxy - forwards backend SSE stream to the client.
 *
 * Authenticates the request server-side so the API key stays hidden,
 * then pipes the backend text/event-stream response through unchanged.
 */

import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";
import type { ChatRequest } from "@/lib/types";

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as ChatRequest;

    if (!body.patient_id || !body.message) {
      return NextResponse.json(
        { error: "patient_id and message are required" },
        { status: 400 },
      );
    }

    let authHeaders: HeadersInit;
    try {
      authHeaders = await getAuthHeaders();
    } catch {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 },
      );
    }

    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = "Chat stream request failed";

      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorMessage;
      } catch {
        // Use default error message
      }

      return NextResponse.json(
        { error: errorMessage },
        { status: response.status },
      );
    }

    // Pipe the SSE stream through to the client
    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    console.error("Chat stream API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}
