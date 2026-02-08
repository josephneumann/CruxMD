import type { LucideIcon } from "lucide-react";
import { Search, CalendarClock, Network } from "lucide-react";
import { TOOL_NAMES } from "@/lib/types";

interface ToolConfig {
  icon: LucideIcon;
  /** Present-tense label for in-flight display */
  activeLabel: string;
  /** Past-tense label for completed log */
  doneLabel: string;
}

/** Translate FHIR resource types to human-readable terms */
const RESOURCE_TYPE_LABELS: Record<string, string> = {
  Condition: "conditions",
  MedicationRequest: "medications",
  MedicationStatement: "medications",
  Observation: "lab results",
  Procedure: "procedures",
  Encounter: "visits",
  AllergyIntolerance: "allergies",
  Immunization: "immunizations",
  CarePlan: "care plans",
  DiagnosticReport: "reports",
  DocumentReference: "clinical notes",
};

const TOOL_CONFIG: Record<string, ToolConfig> = {
  [TOOL_NAMES.QUERY_PATIENT_DATA]: {
    icon: Search,
    activeLabel: "Searching",
    doneLabel: "Searched",
  },
  [TOOL_NAMES.EXPLORE_CONNECTIONS]: {
    icon: Network,
    activeLabel: "Exploring connections",
    doneLabel: "Explored connections",
  },
  [TOOL_NAMES.GET_PATIENT_TIMELINE]: {
    icon: CalendarClock,
    activeLabel: "Looking at visit history",
    doneLabel: "Retrieved visit history",
  },
};

const DEFAULT_CONFIG: ToolConfig = { icon: Search, activeLabel: "Running tool", doneLabel: "Ran tool" };

/**
 * Extract the human-readable search term from a tool call's arguments JSON.
 * Returns null if no meaningful term can be extracted.
 */
function extractSearchTerm(name: string, argumentsJson: string): string | null {
  try {
    const args = JSON.parse(argumentsJson);

    switch (name) {
      case TOOL_NAMES.QUERY_PATIENT_DATA: {
        const resourceLabel = args.resource_type
          ? RESOURCE_TYPE_LABELS[args.resource_type] ?? null
          : null;
        const searchName = args.name ?? null;
        if (resourceLabel && searchName) return `${resourceLabel} — ${searchName}`;
        if (resourceLabel) return resourceLabel;
        if (searchName) return searchName;
        return null;
      }
      case TOOL_NAMES.EXPLORE_CONNECTIONS:
        // fhir_id and resource_type are internals — don't expose
        return null;
      case TOOL_NAMES.GET_PATIENT_TIMELINE: {
        const parts: string[] = [];
        if (args.start_date) parts.push(args.start_date);
        if (args.end_date) parts.push(args.end_date);
        return parts.length > 0 ? parts.join(" to ") : null;
      }
      default:
        return null;
    }
  } catch {
    return null;
  }
}

/** Format a tool call for the in-flight spinner status line. */
export function formatToolActive(name: string, argumentsJson: string): string {
  const config = TOOL_CONFIG[name] ?? DEFAULT_CONFIG;
  const term = extractSearchTerm(name, argumentsJson);
  return term ? `${config.activeLabel} — ${term}` : config.activeLabel;
}

/** Format a tool call for the completed log (past tense). */
export function formatToolDone(name: string, argumentsJson: string): string {
  const config = TOOL_CONFIG[name] ?? DEFAULT_CONFIG;
  const term = extractSearchTerm(name, argumentsJson);
  return term ? `${config.doneLabel} — ${term}` : config.doneLabel;
}

/** Get the icon for a tool name. */
export function getToolIcon(name: string): LucideIcon {
  return (TOOL_CONFIG[name] ?? DEFAULT_CONFIG).icon;
}
