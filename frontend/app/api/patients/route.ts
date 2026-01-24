import { NextResponse } from "next/server";
import { API_BASE_URL, defaultHeaders } from "@/lib/api";

/**
 * GET /api/patients
 * Proxy to backend: GET /api/patients
 */
export async function GET() {
  const response = await fetch(`${API_BASE_URL}/api/patients`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!response.ok) {
    return NextResponse.json(
      { error: "Failed to fetch patients" },
      { status: response.status }
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
