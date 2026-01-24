import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, defaultHeaders } from "@/lib/api";

interface RouteParams {
  params: Promise<{ patientId: string }>;
}

/**
 * GET /api/patients/:patientId
 * Proxy to backend: GET /api/patients/:patientId
 */
export async function GET(_request: NextRequest, { params }: RouteParams) {
  const { patientId } = await params;

  const response = await fetch(`${API_BASE_URL}/api/patients/${patientId}`, {
    headers: defaultHeaders,
    cache: "no-store",
  });

  if (!response.ok) {
    if (response.status === 404) {
      return NextResponse.json(
        { error: "Patient not found" },
        { status: 404 }
      );
    }
    return NextResponse.json(
      { error: "Failed to fetch patient" },
      { status: response.status }
    );
  }

  const data = await response.json();
  return NextResponse.json(data);
}
