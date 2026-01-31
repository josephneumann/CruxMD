/**
 * Patients API route - proxies patient list requests to the backend.
 */

import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL, getAuthHeaders } from "@/lib/api";

export async function GET(request: NextRequest) {
  try {
    let authHeaders: HeadersInit;
    try {
      authHeaders = await getAuthHeaders();
    } catch {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }

    const { searchParams } = request.nextUrl;
    const skip = searchParams.get("skip") || "0";
    const limit = searchParams.get("limit") || "50";

    const response = await fetch(
      `${API_BASE_URL}/api/patients?skip=${skip}&limit=${limit}`,
      {
        headers: authHeaders,
      }
    );

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch patients" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Patients API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
