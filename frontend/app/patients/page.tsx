"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Search, User } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import {
  getPatientDisplayName,
  getPatientInitials,
  getPatientAvatarUrl,
  formatFhirDate,
  calculateAge,
} from "@/lib/utils";
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

      <main className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto w-full px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-semibold text-foreground pl-6 md:pl-0">Patients</h1>
          </div>

          {/* Search bar */}
          <div className="relative mb-6">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search patients..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-12 h-12 text-base bg-muted/50 border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>

          {/* Patient count */}
          {!loading && filtered.length > 0 && (
            <div className="flex items-center gap-2 mb-2 text-sm h-8">
              <span className="text-muted-foreground">
                {filtered.length} patient{filtered.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}

          {loading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="flex items-center gap-4 py-4 px-3 animate-pulse">
                  <div className="h-10 w-10 rounded-full bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-32 rounded bg-muted" />
                    <div className="h-3 w-48 rounded bg-muted" />
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
            <div className="space-y-0">
              {filtered.map((patient) => {
                const { data } = patient;
                const name = getPatientDisplayName(data);
                const initials = getPatientInitials(data);
                const avatarSrc = getPatientAvatarUrl(data);
                const age = calculateAge(data.birthDate);
                const dob = data.birthDate ? formatFhirDate(data.birthDate) : null;
                const gender = data.gender;

                // Build secondary info string
                const infoParts: string[] = [];
                if (age !== null) infoParts.push(`${age}y`);
                if (gender) infoParts.push(gender.charAt(0).toUpperCase() + gender.slice(1));
                if (dob) infoParts.push(`DOB: ${dob}`);
                const secondaryInfo = infoParts.join(" · ");

                return (
                  <div
                    key={patient.id}
                    onClick={() => handlePatientClick(patient)}
                    className="flex items-center gap-3 py-3 px-3 rounded-lg cursor-pointer transition-colors hover:bg-muted/50"
                  >
                    {/* Avatar */}
                    <Avatar className="h-10 w-10 shrink-0">
                      <AvatarImage src={avatarSrc} alt={name} className="object-cover" />
                      <AvatarFallback className="bg-primary/10 text-primary text-sm font-medium">
                        {initials}
                      </AvatarFallback>
                    </Avatar>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-foreground truncate">{name}</div>
                      <div className="text-sm text-muted-foreground">{secondaryInfo}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
