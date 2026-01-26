"use client";

import { useState } from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { cn } from "@/lib/utils";
import {
  MoreHorizontal,
  Heart,
  Activity,
  Thermometer,
  Wind,
  Droplets,
  TrendingUp,
  Minus,
  AlertCircle,
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

      {/* Basic Card */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Card</h2>
        <ComponentPreview
          title="Simple card"
          description="Card with header and content"
          code={`<Card>
  <CardHeader>
    <CardTitle>Patient Summary</CardTitle>
    <CardDescription>Last updated 2 hours ago</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Patient is a 45-year-old male with history of hypertension.</p>
  </CardContent>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Patient Summary</CardTitle>
              <CardDescription>Last updated 2 hours ago</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Patient is a 45-year-old male with history of hypertension.
              </p>
            </CardContent>
          </Card>
        </ComponentPreview>
      </div>

      {/* With Footer */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Footer</h2>
        <ComponentPreview
          title="Card with footer"
          description="Card with action buttons in the footer"
          code={`<Card>
  <CardHeader>
    <CardTitle>Lab Results</CardTitle>
    <CardDescription>Complete blood count</CardDescription>
  </CardHeader>
  <CardContent>
    <p>All values within normal range.</p>
  </CardContent>
  <CardFooter className="gap-2">
    <Button size="sm">View Details</Button>
    <Button size="sm" variant="outline">Download PDF</Button>
  </CardFooter>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Lab Results</CardTitle>
              <CardDescription>Complete blood count</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                All values within normal range.
              </p>
            </CardContent>
            <CardFooter className="gap-2">
              <Button size="sm">View Details</Button>
              <Button size="sm" variant="outline">Download PDF</Button>
            </CardFooter>
          </Card>
        </ComponentPreview>
      </div>

      {/* With Header Action */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Header Action</h2>
        <ComponentPreview
          title="Card with action button"
          description="Using CardAction for a menu button"
          code={`<Card>
  <CardHeader>
    <CardTitle>Recent Visits</CardTitle>
    <CardDescription>3 visits in the last month</CardDescription>
    <CardAction>
      <Button variant="ghost" size="icon-sm">
        <MoreHorizontal className="size-4" />
      </Button>
    </CardAction>
  </CardHeader>
  <CardContent>
    <p>View the patient's recent visit history.</p>
  </CardContent>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Recent Visits</CardTitle>
              <CardDescription>3 visits in the last month</CardDescription>
              <CardAction>
                <Button variant="ghost" size="icon-sm">
                  <MoreHorizontal className="size-4" />
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                View the patient&apos;s recent visit history.
              </p>
            </CardContent>
          </Card>
        </ComponentPreview>
      </div>

      {/* Card Grid */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Card Grid</h2>
        <PreviewGrid cols={3}>
          <Card>
            <CardHeader>
              <CardTitle>Medications</CardTitle>
              <CardDescription>Active prescriptions</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">12</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Allergies</CardTitle>
              <CardDescription>Known allergies</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">3</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Conditions</CardTitle>
              <CardDescription>Active diagnoses</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">5</p>
            </CardContent>
          </Card>
        </PreviewGrid>
      </div>

      {/* Vital Signs */}
      <VitalSignsDemo />

      {/* Patient Summary Card */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Patient Summary Card</h2>
        <p className="text-muted-foreground">
          A comprehensive card for displaying patient information at a glance.
        </p>
        <div className="max-w-md">
          <Card className="p-5">
            <div className="flex items-start gap-4">
              <Avatar className="size-12 bg-primary/20">
                <AvatarFallback className="bg-primary/20 text-primary font-medium">
                  J
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">Johnson, Emily</h3>
                    <p className="text-sm text-muted-foreground">Dr. Williams</p>
                  </div>
                  <Badge variant="sage" size="sm">Low Risk</Badge>
                </div>
                <div className="mt-2 space-y-0.5 text-sm text-muted-foreground">
                  <p>MRN: MRN-789012</p>
                  <p>49y, Female • DOB: 06/22/1975</p>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t space-y-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="size-4 text-destructive mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Allergies</p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    <Badge variant="outline" size="sm">Penicillin</Badge>
                    <Badge variant="outline" size="sm">Latex</Badge>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm">
                  <span className="font-medium">Conditions:</span>{" "}
                  <span className="text-muted-foreground">
                    Hypertension, Type 2 Diabetes
                  </span>
                </p>
              </div>
            </div>
          </Card>
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
  ) : (
    <Minus className="size-3 text-muted-foreground/40" />
  );

  const badgeVariant = status === "normal" ? "sage" : status === "warning" ? "ochre" : "primary";
  const badgeClassName = status === "critical" ? "bg-destructive text-destructive-foreground" : "";

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
          <Badge variant={badgeVariant} size="sm" className={cn("self-start", badgeClassName)}>
            {statusLabel}
          </Badge>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-sm font-semibold">{value}</span>
          <span className="text-xs text-muted-foreground">{unit}</span>
          {trendIcon}
        </div>
      )}
    </Card>
  );
}

function VitalSignsDemo() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-medium">Vital Signs Cards</h2>
      <p className="text-muted-foreground">
        Interactive cards for displaying vital sign measurements. Click any card to toggle between expanded and collapsed states.
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
          icon={<Thermometer className="size-4 text-[#8B8FC7]" strokeWidth={1.5} />}
          label="Temperature"
          value="98.6"
          unit="°F"
          time="10:30 AM"
          trend="stable"
          status="normal"
          statusLabel="Normal"
        />

        <VitalSignCard
          icon={<Droplets className="size-4 text-[#8B8FC7]" strokeWidth={1.5} />}
          label="O₂ Saturation"
          value="98"
          unit="%"
          time="10:30 AM"
          trend="stable"
          status="normal"
          statusLabel="Normal"
        />
      </div>

      <p className="text-sm text-muted-foreground">
        <span className="font-medium">Tip:</span> Click any card above to see the collapsed state.
      </p>
    </div>
  );
}
