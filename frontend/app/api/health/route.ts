import { NextResponse } from "next/server";
import { API_BASE_URL } from "@/lib/api";

/**
 * GET /api/health
 * Proxy to backend: GET /health
 */
export async function GET() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json(
        { status: "unhealthy", backend: false },
        { status: 503 }
      );
    }

    const data = await response.json();
    return NextResponse.json({
      status: "healthy",
      backend: true,
      backendStatus: data.status,
    });
  } catch {
    return NextResponse.json(
      { status: "unhealthy", backend: false, error: "Backend unreachable" },
      { status: 503 }
    );
  }
}
