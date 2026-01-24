"use client";

/**
 * Chat page - Main conversational canvas.
 *
 * This page provides the primary interface for interacting with patient data
 * through the AI assistant. It includes:
 * - Patient selection
 * - Patient context header
 * - Medical disclaimer
 * - Chat interface (placeholder for now)
 */

import { useEffect, useState, useCallback } from "react";
import { MedicalDisclaimer } from "@/components/layout";
import { PatientSelector, PatientHeader } from "@/components/patient";
import { type PatientListItem, parsePatientList } from "@/lib/types";
import { listPatientsApiPatientsGet } from "@/lib/generated";
import { createClient, createConfig } from "@/lib/generated/client";

// Client-side API client (no auth for patient list in demo)
const apiClient = createClient(
  createConfig({
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  })
);

export default function ChatPage() {
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch patients - memoized to satisfy exhaustive-deps
  const fetchPatients = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await listPatientsApiPatientsGet({
        client: apiClient,
      });

      if (result.error) {
        throw new Error("Failed to fetch patients");
      }

      // Validate and parse the response using type guard
      const patientList = parsePatientList(result.data);
      setPatients(patientList);

      // Auto-select first patient if available and none selected
      if (patientList.length > 0) {
        setSelectedPatientId((current) => current ?? patientList[0].id);
      }
    } catch (err) {
      console.error("Error fetching patients:", err);
      setError(err instanceof Error ? err.message : "Failed to load patients");
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch patients on mount
  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const selectedPatient = patients.find((p) => p.id === selectedPatientId);

  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          <h1 className="text-xl font-semibold">CruxMD</h1>
          <PatientSelector
            patients={patients}
            selectedPatientId={selectedPatientId}
            onPatientChange={setSelectedPatientId}
            disabled={loading}
          />
        </div>
      </header>

      {/* Main content */}
      <main className="container flex-1 px-4 py-6">
        <div className="mx-auto max-w-4xl space-y-6">
          {/* Medical Disclaimer */}
          <MedicalDisclaimer />

          {/* Error state */}
          {error && (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">
              {error}
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            </div>
          )}

          {/* Patient Header */}
          {!loading && selectedPatient && (
            <PatientHeader patient={selectedPatient} />
          )}

          {/* Chat placeholder */}
          {!loading && selectedPatient && (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              <p className="text-lg font-medium">Chat Interface Coming Soon</p>
              <p className="mt-2">
                The conversational canvas will appear here.
              </p>
            </div>
          )}

          {/* No patients state */}
          {!loading && !error && patients.length === 0 && (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              <p className="text-lg font-medium">No Patients Found</p>
              <p className="mt-2">
                Load patient data using the FHIR API to get started.
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
