"use client";

/**
 * Chat Session Page - Conversational canvas for a specific chat session.
 *
 * Patient is selected via query param (from the patients list page).
 */

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { PatientBadge } from "@/components/patient/PatientBadge";
import { ConversationalCanvas } from "@/components/canvas";
import type { PatientListItem } from "@/lib/types";
import { parsePatientList } from "@/lib/types";

export default function ChatSessionPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;
  const patientIdParam = searchParams.get("patient");
  const initialMessage = searchParams.get("message")
    ? decodeURIComponent(searchParams.get("message")!)
    : undefined;

  const [selectedPatient, setSelectedPatient] = useState<PatientListItem | null>(null);

  // Fetch patient info when a patient ID is provided via query param
  useEffect(() => {
    if (!patientIdParam) return;

    fetch("/api/patients")
      .then((res) => res.json())
      .then((data) => {
        const parsed = parsePatientList(data);
        const match = parsed.find((p) => p.id === patientIdParam);
        if (match) setSelectedPatient(match);
      })
      .catch((err) => {
        console.error("Failed to fetch patients:", err);
      });
  }, [patientIdParam]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col min-h-0">
        {/* Patient context bar */}
        <div className="sticky top-0 z-10 border-b border-border bg-background px-4 py-3 pl-12 md:pl-4">
          <PatientBadge patient={selectedPatient} />
        </div>

        <ConversationalCanvas
          patient={selectedPatient}
          sessionId={sessionId}
          initialMessage={initialMessage}
        />
      </main>
    </div>
  );
}
