"use client";

import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import type { Insight, InsightType } from "@/lib/types";
import { INSIGHT_TYPES } from "@/lib/types";
import {
  Info,
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  TestTube,
  Calendar,
  Pill,
  FileText,
  Stethoscope,
} from "lucide-react";

/**
 * Maps insight types to their corresponding icons.
 */
const INSIGHT_ICONS: Record<InsightType, React.ComponentType<{ className?: string }>> = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
  positive: CheckCircle,
};

/**
 * Maps insight types to their Tailwind color classes.
 * Uses the semantic insight color tokens from globals.css.
 * Higher opacity backgrounds for better visual distinction between severity types.
 */
const INSIGHT_STYLES: Record<InsightType, string> = {
  info: "border-insight-info bg-insight-info/20 dark:bg-insight-info/30 text-foreground [&>svg]:text-insight-info",
  warning: "border-insight-warning bg-insight-warning/20 dark:bg-insight-warning/30 text-foreground [&>svg]:text-insight-warning",
  critical: "border-insight-critical bg-insight-critical/20 dark:bg-insight-critical/30 text-foreground [&>svg]:text-insight-critical",
  positive: "border-insight-positive bg-insight-positive/20 dark:bg-insight-positive/30 text-foreground [&>svg]:text-insight-positive",
};

/**
 * Citation type detection and icon mapping.
 */
type CitationType = "labs" | "encounter" | "medications" | "notes" | "vitals" | "other";

const CITATION_ICONS: Record<CitationType, React.ComponentType<{ className?: string }>> = {
  labs: TestTube,
  encounter: Calendar,
  medications: Pill,
  notes: FileText,
  vitals: Stethoscope,
  other: FileText,
};

/**
 * Detect citation type from citation text.
 */
function detectCitationType(citation: string): CitationType {
  const lower = citation.toLowerCase();
  if (lower.includes("lab") || lower.includes("metabolic") || lower.includes("cbc") || lower.includes("panel")) {
    return "labs";
  }
  if (lower.includes("encounter") || lower.includes("visit") || lower.includes("appointment")) {
    return "encounter";
  }
  if (lower.includes("medication") || lower.includes("drug") || lower.includes("prescription")) {
    return "medications";
  }
  if (lower.includes("note") || lower.includes("documentation")) {
    return "notes";
  }
  if (lower.includes("vital") || lower.includes("bp") || lower.includes("heart rate")) {
    return "vitals";
  }
  return "other";
}

export interface InsightCardProps {
  /** The insight data to render */
  insight: Insight;
  /** Additional CSS classes */
  className?: string;
}

/**
 * InsightCard renders a clinical insight with color-coded severity.
 *
 * Uses shadcn/ui Alert as base, with custom styling for each insight type:
 * - info (blue): General information
 * - warning (yellow/amber): Caution indicators
 * - critical (red): Urgent clinical alerts
 * - positive (green): Favorable findings
 */
export function InsightCard({ insight, className }: InsightCardProps) {
  const { type, title, content, citations } = insight;

  // Validate type at runtime (in case of malformed data from API)
  const validType = INSIGHT_TYPES.includes(type) ? type : "info";
  const Icon = INSIGHT_ICONS[validType];
  const styles = INSIGHT_STYLES[validType];

  return (
    <Alert className={cn(styles, className)}>
      <Icon className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{content}</p>
        {citations && citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {citations.map((citation, index) => {
              const citationType = detectCitationType(citation);
              const CitationIcon = CITATION_ICONS[citationType];
              return (
                <span
                  key={index}
                  className="inline-flex items-center gap-1.5 rounded-md bg-background/50 dark:bg-background/30 px-2 py-1 text-xs text-muted-foreground"
                >
                  <CitationIcon className="size-3" />
                  {citation}
                </span>
              );
            })}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
}

export default InsightCard;
