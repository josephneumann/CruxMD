import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, defaultHeaders } from "@/lib/api";

/**
 * POST /api/fhir/load-bundle
 * Proxy to backend: POST /api/fhir/load-bundle
 */
export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(`${API_BASE_URL}/api/fhir/load-bundle`, {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    return NextResponse.json(
      { error: error.detail || "Failed to load bundle" },
      { status: response.status }
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
