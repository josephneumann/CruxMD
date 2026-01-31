"use client";

/**
 * Chat Session Page - Conversational canvas for a specific chat session.
 *
 * Uses the real useChat hook wired to the backend agent API.
 * Patient selection is required before chatting (will be replaced
 * by session-model-based patient binding in a future task).
 */

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { PatientSelector } from "@/components/patient/PatientSelector";
import { ConversationalCanvas } from "@/components/canvas";
import type { PatientListItem } from "@/lib/types";
import { parsePatientList } from "@/lib/types";

export default function ChatSessionPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const sessionId = params.id as string;
  const initialMessage = searchParams.get("message")
    ? decodeURIComponent(searchParams.get("message")!)
    : undefined;

  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);

  // Fetch patients list
  useEffect(() => {
    fetch("/api/patients")
      .then((res) => res.json())
      .then((data) => {
        const parsed = parsePatientList(data);
        setPatients(parsed);
      })
      .catch(() => {
        // Patients endpoint unavailable — selector will be empty
      });
  }, []);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col min-h-0">
        {/* Patient context bar */}
        <div className="border-b border-border px-4 py-3">
          <div className="max-w-3xl mx-auto">
            <PatientSelector
              patients={patients}
              selectedPatientId={selectedPatientId}
              onPatientChange={setSelectedPatientId}
            />
          </div>
        </div>

        <ConversationalCanvas
          patientId={selectedPatientId}
          initialMessage={initialMessage}
        />
      </main>
    </div>
  );
}
