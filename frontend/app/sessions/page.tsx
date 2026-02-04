"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PauseCircle, Search, RefreshCw } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SessionCard } from "@/components/session/SessionCard";
import { useSessions } from "@/hooks";
import type { PatientListItem } from "@/lib/types";
import { parsePatientList } from "@/lib/types";

export default function SessionsPage() {
  const router = useRouter();
  const { sessions, isLoading, error, refresh, resumeSession } = useSessions("paused");
  const [patients, setPatients] = useState<Map<string, PatientListItem>>(new Map());
  const [patientsLoading, setPatientsLoading] = useState(true);
  const [search, setSearch] = useState("");

  // Fetch all patients to resolve names
  useEffect(() => {
    fetch("/api/patients?limit=1000")
      .then((res) => res.json())
      .then((data) => {
        const patientList = parsePatientList(data);
        const patientMap = new Map<string, PatientListItem>();
        for (const p of patientList) {
          patientMap.set(p.id, p);
        }
        setPatients(patientMap);
      })
      .catch((err) => {
        console.error("Failed to fetch patients:", err);
      })
      .finally(() => setPatientsLoading(false));
  }, []);

  // Filter sessions by patient name search
  const filteredSessions = sessions.filter((session) => {
    if (!search) return true;
    const patient = patients.get(session.patient_id);
    if (!patient) return false;
    const name = getPatientDisplayName(patient).toLowerCase();
    return name.includes(search.toLowerCase());
  });

  const handleResume = useCallback(async (sessionId: string) => {
    await resumeSession(sessionId);
    // Navigate to the chat with this session
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      router.push(`/chat/${sessionId}?patient=${session.patient_id}`);
    }
  }, [resumeSession, sessions, router]);

  const loading = isLoading || patientsLoading;

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col min-h-0">
        <div className="sticky top-0 z-10 border-b border-border bg-background px-6 py-4">
          <div className="flex items-center justify-between mb-3 pl-6 md:pl-0">
            <h1 className="text-lg font-semibold text-foreground">Paused Sessions</h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={refresh}
              disabled={isLoading}
              className="gap-1"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search by patient name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="mb-4 p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
              {error.message}
            </div>
          )}

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border bg-card p-5 animate-pulse"
                >
                  <div className="space-y-3">
                    <div className="flex items-center gap-2">
                      <div className="h-4 w-4 rounded-full bg-muted" />
                      <div className="h-4 w-32 rounded bg-muted" />
                    </div>
                    <div className="h-10 rounded bg-muted" />
                    <div className="flex items-center justify-between">
                      <div className="h-3 w-16 rounded bg-muted" />
                      <div className="h-8 w-20 rounded bg-muted" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <PauseCircle className="h-10 w-10 mb-3" />
              <p className="text-sm">
                {search
                  ? "No paused sessions match your search."
                  : "No paused sessions. Start a conversation with a patient to create one."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredSessions.map((session) => (
                <SessionCard
                  key={session.id}
                  session={session}
                  patient={patients.get(session.patient_id)}
                  onResume={handleResume}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

/**
 * Get patient display name from FHIR data
 */
function getPatientDisplayName(patient?: PatientListItem): string {
  if (!patient?.data?.name?.[0]) return "Unknown Patient";

  const name = patient.data.name[0];
  const given = name.given?.join(" ") || "";
  const family = name.family || "";

  return `${given} ${family}`.trim() || "Unknown Patient";
}
