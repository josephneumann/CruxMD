import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const labResults = [
  { test: "White Blood Cells", value: "7.5", unit: "K/uL", range: "4.5-11.0", status: "normal", date: "01/25/2026" },
  { test: "Hemoglobin", value: "15.2", unit: "g/dL", range: "13.5-17.5", status: "normal", date: "01/25/2026" },
  { test: "Platelets", value: "425", unit: "K/uL", range: "150-400", status: "high", date: "01/25/2026", trend: "up" },
  { test: "Potassium", value: "6.2", unit: "mEq/L", range: "3.5-5.0", status: "critical", date: "01/25/2026" },
];

const medications = [
  { name: "Lisinopril", dosage: "10 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "01/15/2025", status: "active" },
  { name: "Metformin", dosage: "500 mg", frequency: "Twice daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "03/20/2025", status: "active" },
  { name: "Atorvastatin", dosage: "20 mg", frequency: "Once daily at bedtime", route: "Oral", prescriber: "Dr. Williams", startDate: "06/10/2024", status: "active" },
  { name: "Warfarin", dosage: "5 mg", frequency: "Once daily", route: "Oral", prescriber: "Dr. Anderson", startDate: "12/01/2024", status: "discontinued" },
];

function StatusBadge({ status }: { status: string }) {
  const variants: Record<string, "positive" | "warning" | "critical" | "neutral"> = {
    normal: "positive",
    high: "warning",
    low: "warning",
    critical: "critical",
    active: "positive",
    discontinued: "neutral",
  };
  const labels: Record<string, string> = {
    normal: "Normal",
    high: "High",
    low: "Low",
    critical: "Critical",
    active: "Active",
    discontinued: "Discontinued",
  };
  return <Badge variant={variants[status]} size="sm">{labels[status]}</Badge>;
}

function TrendIcon({ trend }: { trend?: string }) {
  if (trend === "up") return <TrendingUp className="size-4 text-[#D4A27F]" />;
  if (trend === "down") return <TrendingDown className="size-4 text-[#61AAF2]" />;
  return null;
}

function ValueCell({ value, unit, status }: { value: string; unit: string; status: string }) {
  const isAbnormal = status === "high" || status === "low" || status === "critical";
  return (
    <span className={isAbnormal ? "text-[#BF4D43] font-medium" : ""}>
      {value} <span className="text-muted-foreground">{unit}</span>
      {status === "high" && <TrendingUp className="inline size-3 ml-1" />}
      {status === "critical" && <span className="ml-1">!!!</span>}
    </span>
  );
}

function FlagBadge({ status }: { status: string }) {
  if (status === "high") return <Badge variant="warning" size="sm" className="ml-2 text-[10px] px-1.5">H</Badge>;
  if (status === "critical") return <Badge variant="critical" size="sm" className="ml-2 text-[10px] px-1.5">CRITICAL</Badge>;
  return null;
}

export default function TablePage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Table</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Tables display structured data with support for status badges, trend indicators,
          and color-coded values. Wrap in Card for grouped presentation.
        </p>
      </div>

      {/* Laboratory Results */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Laboratory Results</h2>
        <Card>
          <CardHeader>
            <CardTitle>Complete Blood Count (CBC)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Test</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Value</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Reference Range</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Trend</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {labResults.map((row) => (
                  <tr key={row.test} className={row.status === "critical" ? "bg-[#BF4D43]/5" : ""}>
                    <td className="p-4 font-medium">
                      {row.test}
                      <FlagBadge status={row.status} />
                    </td>
                    <td className="p-4">
                      <ValueCell value={row.value} unit={row.unit} status={row.status} />
                    </td>
                    <td className="p-4 text-muted-foreground">{row.range}</td>
                    <td className="p-4"><StatusBadge status={row.status} /></td>
                    <td className="p-4 text-muted-foreground">{row.date}</td>
                    <td className="p-4"><TrendIcon trend={row.trend} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Legend */}
            <div className="flex items-center gap-6 px-4 py-3 border-t text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-[#7D8B6F]" />
                Normal
              </span>
              <span className="flex items-center gap-1.5">
                <TrendingUp className="size-3" />
                Above Range
              </span>
              <span className="flex items-center gap-1.5">
                <TrendingDown className="size-3" />
                Below Range
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-[#BF4D43]" />
                Critical
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Current Medications */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Current Medications</h2>
        <Card>
          <CardHeader>
            <CardTitle>Current Medications</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Medication</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Dosage</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Frequency</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Route</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Prescriber</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Start Date</th>
                  <th className="text-left p-4 text-xs font-medium text-muted-foreground uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {medications.map((row) => (
                  <tr key={row.name}>
                    <td className="p-4 font-medium">{row.name}</td>
                    <td className="p-4">{row.dosage}</td>
                    <td className="p-4">{row.frequency}</td>
                    <td className="p-4">{row.route}</td>
                    <td className="p-4">{row.prescriber}</td>
                    <td className="p-4 text-muted-foreground">{row.startDate}</td>
                    <td className="p-4"><StatusBadge status={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>

      {/* Basic Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Table</h2>
        <p className="text-muted-foreground">
          Minimal table styling without card wrapper.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 text-sm font-medium">Name</th>
                <th className="text-left p-3 text-sm font-medium">Type</th>
                <th className="text-left p-3 text-sm font-medium">Default</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="p-3 font-mono text-sm">variant</td>
                <td className="p-3 text-sm text-muted-foreground">string</td>
                <td className="p-3 font-mono text-sm">"default"</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-sm">size</td>
                <td className="p-3 text-sm text-muted-foreground">string</td>
                <td className="p-3 font-mono text-sm">"md"</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Usage */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Usage</h2>
        <div className="rounded-lg border bg-muted p-4">
          <pre className="text-sm font-mono overflow-x-auto">
            <code>{`// Table with Card wrapper
<Card>
  <CardHeader>
    <CardTitle>Table Title</CardTitle>
  </CardHeader>
  <CardContent className="p-0">
    <table className="w-full">
      <thead>
        <tr className="border-b bg-muted/30">
          <th className="text-left p-4 text-xs font-medium
              text-muted-foreground uppercase tracking-wider">
            Column
          </th>
        </tr>
      </thead>
      <tbody className="divide-y">
        <tr>
          <td className="p-4">Value</td>
        </tr>
      </tbody>
    </table>
  </CardContent>
</Card>

// Status badges in tables
<Badge variant="positive" size="sm">Normal</Badge>
<Badge variant="warning" size="sm">High</Badge>
<Badge variant="critical" size="sm">Critical</Badge>`}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
