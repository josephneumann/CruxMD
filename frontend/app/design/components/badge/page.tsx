"use client";

import { Badge } from "@/components/ui/badge";
import { CodeBlock } from "@/components/design-system/CodeBlock";
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

      {/* Color Mapping */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Color Mapping</h2>
        <p className="text-muted-foreground">
          How badge variants map to design system colors.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="text-left p-3 font-medium">Variant</th>
                <th className="text-left p-3 font-medium">Background</th>
                <th className="text-left p-3 font-medium">Foreground</th>
                <th className="text-left p-3 font-medium">Use Case</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="p-3"><Badge variant="primary" size="sm">primary</Badge></td>
                <td className="p-3 font-mono text-xs">Book Cloth (#CC785C)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Primary actions, emphasis</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="secondary" size="sm">secondary</Badge></td>
                <td className="p-3 font-mono text-xs">Ivory Dark (#E5E4DF)</td>
                <td className="p-3 font-mono text-xs">Slate Dark (#191919)</td>
                <td className="p-3 text-muted-foreground">Subtle labels, counts</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="sage" size="sm">sage</Badge></td>
                <td className="p-3 font-mono text-xs">Sage (#7D8B6F)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Success, active status</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="periwinkle" size="sm">periwinkle</Badge></td>
                <td className="p-3 font-mono text-xs">Periwinkle (#8B8FC7)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Links, selections, labs</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="plum" size="sm">plum</Badge></td>
                <td className="p-3 font-mono text-xs">Dusty Plum (#5D4B63)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Premium, encounters</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="info" size="sm">info</Badge></td>
                <td className="p-3 font-mono text-xs">Focus Blue (#61AAF2)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Informational alerts</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="warning" size="sm">warning</Badge></td>
                <td className="p-3 font-mono text-xs">Kraft (#D4A27F)</td>
                <td className="p-3 font-mono text-xs">Slate Dark (#191919)</td>
                <td className="p-3 text-muted-foreground">Caution, attention needed</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="critical" size="sm">critical</Badge></td>
                <td className="p-3 font-mono text-xs">Error Red (#BF4D43)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Urgent, critical alerts</td>
              </tr>
              <tr>
                <td className="p-3"><Badge variant="positive" size="sm">positive</Badge></td>
                <td className="p-3 font-mono text-xs">Sage (#7D8B6F)</td>
                <td className="p-3 font-mono text-xs">#FFFFFF</td>
                <td className="p-3 text-muted-foreground">Favorable findings</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Code Example */}
      <CodeBlock
        collapsible
        label="View Code"
        code={`import { Badge } from "@/components/ui/badge"
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
</Badge>`}
      />

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
