"use client";

import { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PatientSummaryCard } from "@/components/patient/PatientSummaryCard";
import { PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { cn } from "@/lib/utils";
import {
  Heart,
  Activity,
  Thermometer,
  Droplets,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  Pill,
  Stethoscope,
  FileText,
  TestTube,
  FlaskConical,
} from "lucide-react";

const cardComponents = [
  {
    name: "Card",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Container wrapper with shadow and border",
  },
  {
    name: "CardHeader",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Header section with grid layout for title/action",
  },
  {
    name: "CardTitle",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Title element with semibold text",
  },
  {
    name: "CardDescription",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Muted description text",
  },
  {
    name: "CardContent",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Main content area",
  },
  {
    name: "CardFooter",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Footer section for actions",
  },
  {
    name: "CardAction",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Action button slot in header",
  },
];

export default function CardPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Card</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Cards are containers that group related content and actions. They use
          a composable pattern with multiple sub-components for flexible layouts.
        </p>
      </div>

      {/* Basic Examples */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Examples</h2>
        <div className="flex flex-wrap gap-4">
          {/* Basic Card */}
          <Card className="w-80 relative">
            <Badge variant="jade" size="sm" className="absolute top-3 right-3">Active</Badge>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="size-4" />
                Patient Summary
              </CardTitle>
              <CardDescription>Last updated 2 hours ago</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Patient is a 45-year-old male with history of hypertension.
              </p>
            </CardContent>
          </Card>

          {/* Card with Footer */}
          <Card className="w-80 relative">
            <Badge variant="teal" size="sm" className="absolute top-3 right-3">New</Badge>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TestTube className="size-4" />
                Lab Results
              </CardTitle>
              <CardDescription>Complete blood count</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                All values within normal range.
              </p>
            </CardContent>
            <CardFooter className="gap-2">
              <Button size="sm">View Details</Button>
              <Button size="sm" variant="outline">Download</Button>
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* Card Grid */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Card Grid</h2>
        <PreviewGrid cols={3}>
          <Card className="relative">
            <Badge variant="secondary" size="sm" className="absolute top-3 right-3">12</Badge>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Pill className="size-4" />
                Medications
              </CardTitle>
              <CardDescription>Active prescriptions</CardDescription>
            </CardHeader>
          </Card>
          <Card className="relative">
            <Badge variant="secondary" size="sm" className="absolute top-3 right-3">3</Badge>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="size-4" />
                Allergies
              </CardTitle>
              <CardDescription>Known allergies</CardDescription>
            </CardHeader>
          </Card>
          <Card className="relative">
            <Badge variant="secondary" size="sm" className="absolute top-3 right-3">5</Badge>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Stethoscope className="size-4" />
                Conditions
              </CardTitle>
              <CardDescription>Active diagnoses</CardDescription>
            </CardHeader>
          </Card>
        </PreviewGrid>
      </div>

      {/* Clinical Observation Cards */}
      <ClinicalObservationCardsDemo />

      {/* Patient Summary Card */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Patient Summary Card</h2>
        <p className="text-muted-foreground">
          A comprehensive card for displaying patient information at a glance.
          This is the same component used on the Patients list page.
        </p>
        <div className="max-w-md">
          <PatientSummaryCard
            patient={{
              id: "demo-patient",
              fhir_id: "demo-patient",
              data: {
                name: [{ given: ["Emily"], family: "Johnson" }],
                birthDate: "1975-06-22",
                gender: "female",
              },
            }}
          />
        </div>
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={cardComponents} />
      </div>
    </div>
  );
}

// Interactive Vital Sign Card Component
interface VitalSignCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit: string;
  time: string;
  trend: "up" | "down" | "stable";
  status: "normal" | "warning" | "critical";
  statusLabel: string;
  note?: string;
  defaultExpanded?: boolean;
}

function VitalSignCard({
  icon,
  label,
  value,
  unit,
  time,
  trend,
  status,
  statusLabel,
  note,
  defaultExpanded = true,
}: VitalSignCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  const isAbnormal = status === "warning" || status === "critical";
  const trendIcon = trend === "up" ? (
    <TrendingUp className={cn("size-3", isAbnormal ? "text-destructive" : "text-muted-foreground/40")} />
  ) : trend === "down" ? (
    <TrendingDown className={cn("size-3", status === "normal" ? "text-[#388E3C]" : "text-[#388E3C]")} />
  ) : (
    <Minus className="size-3 text-muted-foreground/40" />
  );

  const badgeVariant = status === "normal" ? "positive" : status === "warning" ? "warning" : "critical";

  return (
    <Card
      className={cn(
        "cursor-pointer transition-all duration-200 select-none w-[180px]",
        isAbnormal && "border-destructive/50",
        expanded ? "h-[160px] p-3" : "px-3 py-2"
      )}
      onClick={() => setExpanded(!expanded)}
    >
      {expanded ? (
        <div className="flex flex-col h-full">
          {/* Header row */}
          <div className="flex items-center justify-between">
            {icon}
            {trendIcon}
          </div>

          {/* Value + time block */}
          <div className="mt-1.5">
            <div>
              <span className="text-2xl font-semibold leading-none">{value}</span>
              <span className="text-xs text-muted-foreground ml-1">{unit}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{time}</p>
          </div>

          {/* Label */}
          <p className="text-sm font-medium leading-tight mt-1.5">{label}</p>

          {/* Note if present */}
          {note && (
            <p className="text-xs text-muted-foreground leading-tight">{note}</p>
          )}

          {/* Spacer to push badge to bottom */}
          <div className="flex-1 min-h-2" />

          {/* Status badge at bottom */}
          <Badge variant={badgeVariant} size="sm" className="self-start">
            {statusLabel}
          </Badge>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-semibold">{value}</span>
          <span className="text-xs text-muted-foreground">{unit}</span>
          <div className="flex-1" />
          {trendIcon}
        </div>
      )}
    </Card>
  );
}

function ClinicalObservationCardsDemo() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-medium">Clinical Observation Cards</h2>
      <p className="text-muted-foreground">
        Interactive cards for displaying clinical measurements and lab results. Click any card to toggle between expanded and collapsed states.
      </p>

      <div className="flex flex-wrap gap-3 items-start">
        <VitalSignCard
          icon={<Heart className="size-4 text-primary" strokeWidth={1.5} />}
          label="Heart Rate"
          value="72"
          unit="bpm"
          time="10:30 AM"
          trend="stable"
          status="normal"
          statusLabel="Normal"
        />

        <VitalSignCard
          icon={<Activity className="size-4 text-destructive" strokeWidth={1.5} />}
          label="Blood Pressure"
          value="132/85"
          unit="mmHg"
          time="10:30 AM"
          trend="up"
          status="critical"
          statusLabel="Stage 1 HTN"
          note="Trending up last 3 visits"
        />

        <VitalSignCard
          icon={<Thermometer className="size-4 text-[#5A7D7C]" strokeWidth={1.5} />}
          label="Temperature"
          value="98.6"
          unit="°F"
          time="10:30 AM"
          trend="stable"
          status="normal"
          statusLabel="Normal"
        />

        <VitalSignCard
          icon={<Droplets className="size-4 text-[#5A7D7C]" strokeWidth={1.5} />}
          label="O₂ Saturation"
          value="98"
          unit="%"
          time="10:30 AM"
          trend="stable"
          status="normal"
          statusLabel="Normal"
        />

        <VitalSignCard
          icon={<FlaskConical className="size-4 text-[#CCA43B]" strokeWidth={1.5} />}
          label="HbA1c"
          value="7.2"
          unit="%"
          time="Jan 15"
          trend="down"
          status="normal"
          statusLabel="Normal"
          note="Down from 7.8% in Oct"
        />
      </div>

      <p className="text-sm text-muted-foreground">
        <span className="font-medium">Tip:</span> Click any card above to see the collapsed state.
      </p>
    </div>
  );
}
