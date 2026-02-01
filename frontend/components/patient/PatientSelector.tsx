"use client";

/**
 * Patient selector dropdown — minimal inline style (text + chevron).
 */

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check, User } from "lucide-react";
import { getPatientDisplayName, formatFhirDate } from "@/lib/utils";
import type { PatientListItem } from "@/lib/types";

interface PatientSelectorProps {
  patients: PatientListItem[];
  selectedPatientId: string | null;
  onPatientChange: (patientId: string) => void;
  disabled?: boolean;
}

export function PatientSelector({
  patients,
  selectedPatientId,
  onPatientChange,
  disabled = false,
}: PatientSelectorProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const selected = patients.find((p) => p.id === selectedPatientId);
  const label = selected
    ? getPatientDisplayName(selected.data)
    : "Select a patient";

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled || patients.length === 0}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <User className="h-3.5 w-3.5" />
        {label}
        <ChevronDown className="h-3 w-3" />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-2 w-72 rounded-lg border border-border bg-popover shadow-lg py-1 z-50">
          {patients.map((patient) => {
            const name = getPatientDisplayName(patient.data);
            const dob = patient.data.birthDate
              ? formatFhirDate(patient.data.birthDate)
              : null;
            const isSelected = patient.id === selectedPatientId;

            return (
              <button
                key={patient.id}
                onClick={() => {
                  onPatientChange(patient.id);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-3 px-3 py-2.5 text-left cursor-pointer rounded-md hover:bg-accent/80 transition-colors"
              >
                <div className="w-4 flex-shrink-0">
                  {isSelected && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </div>
                <div>
                  <div className="text-sm font-medium">{name}</div>
                  {dob && (
                    <div className="text-xs text-muted-foreground">
                      DOB: {dob}
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
