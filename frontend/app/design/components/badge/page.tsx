import { Badge } from "@/components/ui/badge";
import { FlaskConical, Pill, Calendar } from "lucide-react";

export default function BadgePage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Badge</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Badges are used to highlight status, categories, or metadata. They come
          in multiple color variants and sizes.
        </p>
      </div>

      {/* Variants */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Variants</h2>
        <div className="rounded-lg border bg-card p-6 space-y-6">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Base Variants</p>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="primary">Primary</Badge>
              <Badge variant="secondary">Secondary</Badge>
              <Badge variant="sage">Sage</Badge>
              <Badge variant="periwinkle">Periwinkle</Badge>
              <Badge variant="plum">Plum</Badge>
              <Badge variant="outline">Outline</Badge>
              <Badge variant="neutral">Neutral</Badge>
            </div>
          </div>
          <div className="border-t pt-6 space-y-3">
            <p className="text-sm text-muted-foreground">Clinical Insight Variants</p>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant="info">Info</Badge>
              <Badge variant="warning">Warning</Badge>
              <Badge variant="critical">Critical</Badge>
              <Badge variant="positive">Positive</Badge>
            </div>
          </div>
          <div className="border-t pt-6 space-y-3">
            <p className="text-sm text-muted-foreground">Badge Sizes</p>
            <div className="flex flex-wrap items-center gap-3">
              <Badge size="sm" variant="primary">Small</Badge>
              <Badge size="md" variant="primary">Medium</Badge>
              <Badge size="lg" variant="primary">Large</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Use Cases */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Use Cases</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-4 space-y-3">
            <p className="text-sm font-medium">Status Indicators</p>
            <p className="text-xs text-muted-foreground">Match clinical insight colors</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="info">Info</Badge>
              <Badge variant="warning">Warning</Badge>
              <Badge variant="critical">Critical</Badge>
              <Badge variant="positive">Positive</Badge>
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4 space-y-3">
            <p className="text-sm font-medium">Categories</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="periwinkle" className="gap-1">
                <FlaskConical className="size-3" />
                Lab
              </Badge>
              <Badge variant="primary" className="gap-1">
                <Pill className="size-3" />
                Meds
              </Badge>
              <Badge variant="plum" className="gap-1">
                <Calendar className="size-3" />
                Encounters
              </Badge>
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4 space-y-3">
            <p className="text-sm font-medium">Counts</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary" size="sm">3</Badge>
              <Badge variant="primary" size="sm">12</Badge>
              <Badge variant="neutral" size="sm">99+</Badge>
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4 space-y-3">
            <p className="text-sm font-medium">Tags</p>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">Hypertension</Badge>
              <Badge variant="outline">Diabetes</Badge>
              <Badge variant="outline">CKD Stage 3</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Code Example */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Usage</h2>
        <div className="rounded-lg border bg-muted p-4">
          <pre className="text-sm font-mono overflow-x-auto">
            <code>{`import { Badge } from "@/components/ui/badge"
import { FlaskConical } from "lucide-react"

// Base variants
<Badge variant="primary">Primary</Badge>
<Badge variant="sage">Sage</Badge>
<Badge variant="outline">Outline</Badge>

// Clinical insight variants
<Badge variant="info">Info</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="critical">Critical</Badge>
<Badge variant="positive">Positive</Badge>

// With icon
<Badge variant="periwinkle" className="gap-1">
  <FlaskConical className="size-3" />
  Lab
</Badge>`}</code>
          </pre>
        </div>
      </div>

      {/* Props */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Props</h2>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-3 font-medium">Prop</th>
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Default</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="p-3 font-mono text-xs">variant</td>
                <td className="p-3 font-mono text-xs text-muted-foreground">
                  primary | secondary | sage | periwinkle | plum | outline | neutral | info | warning | critical | positive
                </td>
                <td className="p-3 font-mono text-xs">primary</td>
              </tr>
              <tr>
                <td className="p-3 font-mono text-xs">size</td>
                <td className="p-3 font-mono text-xs text-muted-foreground">
                  sm | md | lg
                </td>
                <td className="p-3 font-mono text-xs">md</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
