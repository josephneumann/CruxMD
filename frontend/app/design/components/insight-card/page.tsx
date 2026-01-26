import { InsightCard } from "@/components/clinical/InsightCard";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { Info, AlertTriangle, AlertCircle, CheckCircle } from "lucide-react";
import Link from "next/link";

const insightProps = [
  {
    name: "insight",
    type: "Insight",
    default: "—",
    description: "The insight data object",
    required: true,
  },
  {
    name: "className",
    type: "string",
    default: "—",
    description: "Additional CSS classes",
  },
];

const insightTypeProps = [
  {
    name: "type",
    type: '"info" | "warning" | "critical" | "positive"',
    default: "—",
    description: "Severity level determining color scheme",
    required: true,
  },
  {
    name: "title",
    type: "string",
    default: "—",
    description: "Title of the insight",
    required: true,
  },
  {
    name: "content",
    type: "string",
    default: "—",
    description: "Main content/description",
    required: true,
  },
  {
    name: "citations",
    type: "string[]",
    default: "[]",
    description: "Optional source citations",
  },
];

export default function InsightCardPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">InsightCard</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          InsightCard displays clinical insights with color-coded severity levels.
          It builds on the Alert component with specialized styling for medical
          contexts.
        </p>
      </div>

      {/* Severity Types */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Severity Types</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Info"
            description="General information (blue)"
            code={`<InsightCard
  insight={{
    type: "info",
    title: "Patient Information",
    content: "Patient has an upcoming appointment scheduled.",
  }}
/>`}
          >
            <InsightCard
              insight={{
                type: "info",
                title: "Patient Information",
                content: "Patient has an upcoming appointment scheduled.",
              }}
            />
          </ComponentPreview>

          <ComponentPreview
            title="Warning"
            description="Caution indicators (amber)"
            code={`<InsightCard
  insight={{
    type: "warning",
    title: "Drug Interaction",
    content: "Potential interaction between current medications.",
  }}
/>`}
          >
            <InsightCard
              insight={{
                type: "warning",
                title: "Drug Interaction",
                content: "Potential interaction between current medications.",
              }}
            />
          </ComponentPreview>

          <ComponentPreview
            title="Critical"
            description="Urgent alerts (red)"
            code={`<InsightCard
  insight={{
    type: "critical",
    title: "Critical Lab Value",
    content: "Potassium level is critically elevated at 6.2 mEq/L.",
  }}
/>`}
          >
            <InsightCard
              insight={{
                type: "critical",
                title: "Critical Lab Value",
                content: "Potassium level is critically elevated at 6.2 mEq/L.",
              }}
            />
          </ComponentPreview>

          <ComponentPreview
            title="Positive"
            description="Favorable findings (green)"
            code={`<InsightCard
  insight={{
    type: "positive",
    title: "Treatment Response",
    content: "Patient is responding well to the current treatment plan.",
  }}
/>`}
          >
            <InsightCard
              insight={{
                type: "positive",
                title: "Treatment Response",
                content: "Patient is responding well to the current treatment plan.",
              }}
            />
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* With Citations */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Citations</h2>
        <ComponentPreview
          title="Source citations"
          description="InsightCard with reference citations"
          code={`<InsightCard
  insight={{
    type: "warning",
    title: "Medication Dosage",
    content: "Consider reducing metformin dose due to renal function.",
    citations: ["UpToDate", "FDA Label"],
  }}
/>`}
        >
          <InsightCard
            insight={{
              type: "warning",
              title: "Medication Dosage",
              content: "Consider reducing metformin dose due to renal function.",
              citations: ["UpToDate", "FDA Label"],
            }}
          />
        </ComponentPreview>
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

      {/* Props Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Component Props</h2>
        <PropsTable props={insightProps} />
      </div>

      {/* Insight Type */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Insight Type</h2>
        <PropsTable props={insightTypeProps} />
      </div>
    </div>
  );
}
