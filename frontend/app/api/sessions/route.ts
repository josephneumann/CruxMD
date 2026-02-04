/**
 * Sessions API route - proxies session list/create requests to the backend.
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
    const params = new URLSearchParams();

    const skip = searchParams.get("skip");
    const limit = searchParams.get("limit");
    const status = searchParams.get("status");
    const patientId = searchParams.get("patient_id");

    if (skip) params.set("skip", skip);
    if (limit) params.set("limit", limit);
    if (status) params.set("status", status);
    if (patientId) params.set("patient_id", patientId);

    const queryString = params.toString();
    const url = `${API_BASE_URL}/api/sessions${queryString ? `?${queryString}` : ""}`;

    const response = await fetch(url, {
      headers: authHeaders,
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: "Failed to fetch sessions" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Sessions API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
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

    const body = await request.json();

    const response = await fetch(`${API_BASE_URL}/api/sessions`, {
      method: "POST",
      headers: {
        ...authHeaders,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return NextResponse.json(
        { error: errorData.detail || "Failed to create session" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    console.error("Sessions API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
