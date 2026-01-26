"use client";

/**
 * Chat page - Main conversational canvas styled like Claude.ai
 */

import { useEffect, useState, useCallback } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  Plus,
  Clock,
  ArrowUp,
  FileText,
  FlaskConical,
  Pill,
  AlertTriangle,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PatientSelector } from "@/components/patient";
import { type PatientListItem, parsePatientList } from "@/lib/types";
import { listPatientsApiPatientsGet } from "@/lib/generated";
import { createClient, createConfig } from "@/lib/generated/client";
import { getPatientDisplayName } from "@/lib/utils";

// Client-side API client
const apiClient = createClient(
  createConfig({
    baseUrl: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  })
);

export default function ChatPage() {
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");

  // Fetch patients
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

      const patientList = parsePatientList(result.data);
      setPatients(patientList);

      // Auto-select first patient if available
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

  useEffect(() => {
    fetchPatients();
  }, [fetchPatients]);

  const selectedPatient = patients.find((p) => p.id === selectedPatientId);
  const patientName = selectedPatient
    ? getPatientDisplayName(selectedPatient.data)
    : null;

  // Get time-based greeting
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-border">
        <Link href="/">
          <Image
            src="/brand/wordmark-primary.svg"
            alt="CruxMD"
            width={120}
            height={28}
            priority
          />
        </Link>
        <PatientSelector
          patients={patients}
          selectedPatientId={selectedPatientId}
          onPatientChange={setSelectedPatientId}
          disabled={loading}
        />
      </header>

      {/* Main content - centered */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 pb-32">
        {/* Error state */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-4 text-destructive mb-8 max-w-md text-center">
            {error}
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="flex items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        )}

        {/* Main chat interface */}
        {!loading && (
          <div className="w-full max-w-2xl flex flex-col items-center">
            {/* Greeting with mark */}
            <div className="flex items-center gap-3 mb-8">
              <Image
                src="/brand/mark-primary.svg"
                alt=""
                width={40}
                height={40}
              />
              <h1 className="text-3xl md:text-4xl font-light text-foreground">
                {patientName ? (
                  <>
                    {getGreeting()},{" "}
                    <span className="font-normal">{patientName.split(" ")[0]}</span>
                  </>
                ) : (
                  "Select a patient"
                )}
              </h1>
            </div>

            {/* Input card */}
            <div className="w-full bg-card rounded-2xl border border-border shadow-sm">
              {/* Text input area */}
              <div className="px-4 py-4">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={
                    patientName
                      ? "Ask about this patient..."
                      : "Select a patient to begin..."
                  }
                  disabled={!selectedPatient}
                  className="w-full bg-transparent text-foreground placeholder:text-muted-foreground resize-none outline-none text-base min-h-[24px] max-h-[200px]"
                  rows={1}
                  onInput={(e) => {
                    const target = e.target as HTMLTextAreaElement;
                    target.style.height = "auto";
                    target.style.height = `${target.scrollHeight}px`;
                  }}
                />
              </div>

              {/* Bottom toolbar */}
              <div className="flex items-center justify-between px-4 pb-4">
                {/* Left actions */}
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    disabled={!selectedPatient}
                  >
                    <Plus className="h-5 w-5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                    disabled={!selectedPatient}
                  >
                    <Clock className="h-5 w-5" />
                  </Button>
                </div>

                {/* Right actions */}
                <div className="flex items-center gap-2">
                  {/* Model selector placeholder */}
                  <Button
                    variant="ghost"
                    className="h-8 px-3 text-sm text-muted-foreground hover:text-foreground gap-1"
                    disabled
                  >
                    GPT-4o
                    <ChevronDown className="h-4 w-4" />
                  </Button>

                  {/* Send button */}
                  <Button
                    size="icon"
                    className="h-8 w-8 rounded-lg"
                    disabled={!selectedPatient || !inputValue.trim()}
                  >
                    <ArrowUp className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </div>

            {/* Quick action chips */}
            {selectedPatient && (
              <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
                <QuickActionChip icon={FileText} label="Summarize" />
                <QuickActionChip icon={FlaskConical} label="Review labs" />
                <QuickActionChip icon={Pill} label="Medications" />
                <QuickActionChip icon={AlertTriangle} label="Risk factors" />
              </div>
            )}

            {/* Disclaimer */}
            <p className="text-xs text-muted-foreground text-center mt-8 max-w-md">
              For demonstration purposes only. Not for clinical use. Always
              verify information with primary sources.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}

// Quick action chip component
function QuickActionChip({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-border bg-card hover:bg-muted/50 text-sm text-foreground transition-colors">
      <Icon className="h-4 w-4 text-primary" />
      {label}
    </button>
  );
}
