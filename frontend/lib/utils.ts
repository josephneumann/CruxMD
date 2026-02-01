import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * FHIR HumanName type for patient display helpers.
 */
interface FhirHumanName {
  text?: string;
  given?: string[];
  family?: string;
}

/**
 * Minimal FHIR Patient type for display helpers.
 */
interface FhirPatientLike {
  name?: FhirHumanName[];
}

/**
 * Extract display name from a FHIR Patient resource.
 */
export function getPatientDisplayName(patient: FhirPatientLike): string {
  const name = patient.name?.[0];
  if (!name) return "Unknown";

  if (name.text) return name.text;

  const given = name.given?.join(" ") || "";
  const family = name.family || "";
  return `${given} ${family}`.trim() || "Unknown";
}

/**
 * Format a FHIR date string for display.
 */
export function formatFhirDate(dateString: string | undefined): string {
  if (!dateString) return "Unknown";
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateString;
  }
}

/**
 * Calculate age from a FHIR birthDate.
 */
export function calculateAge(birthDate: string | undefined): number | null {
  if (!birthDate) return null;
  try {
    const birth = new Date(birthDate);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--;
    }
    return age;
  } catch {
    return null;
  }
}

/**
 * Get patient initials for avatar display.
 */
export function getPatientInitials(patient: FhirPatientLike): string {
  const name = patient.name?.[0];
  if (!name) return "?";

  const given = name.given?.[0] || "";
  const family = name.family || "";

  const initials = `${given.charAt(0)}${family.charAt(0)}`.toUpperCase();
  return initials || "?";
}

/**
 * Extended FHIR Patient type with common fields.
 */
export interface FhirPatient extends FhirPatientLike {
  id?: string;
  birthDate?: string;
  gender?: "male" | "female" | "other" | "unknown";
  identifier?: Array<{
    system?: string;
    value?: string;
    type?: {
      coding?: Array<{
        system?: string;
        code?: string;
      }>;
    };
  }>;
}

/**
 * Get avatar URL for a patient based on their display name.
 * Strips diacritics and converts to a hyphenated slug.
 * Falls back gracefully via AvatarFallback if file doesn't exist.
 */
export function getPatientAvatarUrl(patient: FhirPatientLike): string {
  const name = getPatientDisplayName(patient);
  const slug = name
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, "-");
  return `/brand/avatars/${slug}.png`;
}

/**
 * Get MRN (Medical Record Number) from patient identifiers.
 */
export function getPatientMRN(patient: FhirPatient): string | null {
  const identifier = patient.identifier?.find(
    (id) =>
      id.type?.coding?.some((c) => c.code === "MR") ||
      id.system?.includes("mrn")
  );
  return identifier?.value || null;
}
