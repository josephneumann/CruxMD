import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { InsightCard } from "@/components/clinical/InsightCard";
import { PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { Info, AlertCircle, AlertTriangle, CheckCircle } from "lucide-react";
import Link from "next/link";

const insightTypeProps = [
  {
    name: "type",
    type: '"info" | "warning" | "critical" | "positive"',
    default: "—",
    description: "Severity level determining color scheme",
  },
  {
    name: "title",
    type: "string",
    default: "—",
    description: "Title of the insight",
  },
  {
    name: "content",
    type: "string",
    default: "—",
    description: "Main content/description",
  },
  {
    name: "citations",
    type: "string[]",
    default: "[]",
    description: "Optional source citations",
  },
];

export default function AlertPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Alert</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Alerts display important messages with color-coded severity levels.
          Use InsightCard for clinical contexts with the left accent bar pattern.
        </p>
      </div>

      {/* Clinical Insights */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Clinical Insights</h2>
        <p className="text-muted-foreground">
          InsightCard provides severity-based styling for medical contexts.
        </p>
        <PreviewGrid cols={2}>
          <InsightCard
            insight={{
              type: "info",
              title: "Patient Information",
              content: "Patient has an upcoming appointment scheduled.",
            }}
          />
          <InsightCard
            insight={{
              type: "warning",
              title: "Drug Interaction",
              content: "Potential interaction between current medications.",
            }}
          />
          <InsightCard
            insight={{
              type: "critical",
              title: "Critical Lab Value",
              content: "Potassium level is critically elevated at 6.2 mEq/L.",
            }}
          />
          <InsightCard
            insight={{
              type: "positive",
              title: "Treatment Response",
              content: "Patient is responding well to the current treatment plan.",
            }}
          />
        </PreviewGrid>
      </div>

      {/* With Citations */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Citations</h2>
        <div className="max-w-xl">
          <InsightCard
            insight={{
              type: "warning",
              title: "Medication Dosage",
              content: "Consider reducing metformin dose due to renal function.",
              citations: ["UpToDate", "FDA Label"],
            }}
          />
        </div>
      </div>

      {/* Color Reference */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Color Reference</h2>
        <p className="text-sm text-muted-foreground">
          See the full <Link href="/design/colors" className="text-primary hover:underline">Colors page</Link> for
          complete insight color documentation including dark mode values.
        </p>
        <div className="grid grid-cols-4 gap-4">
          {[
            { type: "Info", color: "#61AAF2", icon: Info },
            { type: "Warning", color: "#D4A27F", icon: AlertTriangle },
            { type: "Critical", color: "#BF4D43", icon: AlertCircle },
            { type: "Positive", color: "#7D8B6F", icon: CheckCircle },
          ].map((item) => (
            <div
              key={item.type}
              className="flex items-center gap-3 rounded-r-lg border-l-4 p-3"
              style={{ backgroundColor: `${item.color}15`, borderLeftColor: item.color }}
            >
              <item.icon className="size-4" style={{ color: item.color }} />
              <div>
                <span className="text-sm font-medium">{item.type}</span>
                <span className="block text-xs font-mono text-muted-foreground">{item.color}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Base Alert */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Base Alert</h2>
        <p className="text-sm text-muted-foreground">
          The underlying shadcn/ui Alert component. Use for non-clinical system messages.
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          <Alert>
            <Info className="size-4" />
            <AlertTitle>Default</AlertTitle>
            <AlertDescription>
              Standard informational message.
            </AlertDescription>
          </Alert>

          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Destructive</AlertTitle>
            <AlertDescription>
              Error or critical failure message.
            </AlertDescription>
          </Alert>
        </div>
      </div>

      {/* Insight Props */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">InsightCard Props</h2>
        <PropsTable props={insightTypeProps} />
      </div>
    </div>
  );
}
