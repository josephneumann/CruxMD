"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, User } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { Input } from "@/components/ui/input";
import { PatientSummaryCard } from "@/components/patient/PatientSummaryCard";
import { getPatientDisplayName } from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";
import { parsePatientList } from "@/lib/types";

export default function PatientsPage() {
  const router = useRouter();
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetch("/api/patients")
      .then((res) => res.json())
      .then((data) => {
        setPatients(parsePatientList(data));
      })
      .catch((err) => {
        console.error("Failed to fetch patients:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = patients.filter((p) => {
    if (!search) return true;
    const name = getPatientDisplayName(p.data).toLowerCase();
    return name.includes(search.toLowerCase());
  });

  function handlePatientClick(patient: PatientListItem) {
    const sessionId = crypto.randomUUID();
    router.push(`/chat/${sessionId}?patient=${patient.id}`);
  }

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <main className="flex-1 flex flex-col min-h-0">
        <div className="sticky top-0 z-10 border-b border-border bg-background px-6 py-4">
          <h1 className="text-lg font-semibold text-foreground mb-3 pl-6 md:pl-0">Patients</h1>
          <div className="relative max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search patients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-border bg-card p-5 animate-pulse"
                >
                  <div className="flex items-start gap-4">
                    <div className="h-12 w-12 rounded-full bg-muted" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-28 rounded bg-muted" />
                      <div className="h-3 w-36 rounded bg-muted" />
                      <div className="h-3 w-20 rounded bg-muted" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
              <User className="h-10 w-10 mb-3" />
              <p className="text-sm">
                {search ? "No patients match your search." : "No patients found."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((patient) => (
                <PatientSummaryCard
                  key={patient.id}
                  patient={patient}
                  onClick={() => handlePatientClick(patient)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
