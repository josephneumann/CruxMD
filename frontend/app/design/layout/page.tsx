"use client";

import { CodeBlock } from "@/components/design-system/CodeBlock";

export default function LayoutPage() {
  const spacingScale = [
    { token: "0", value: "0px", use: "None" },
    { token: "1", value: "4px", use: "Tight grouping, icon padding" },
    { token: "2", value: "8px", use: "Related elements, input padding" },
    { token: "3", value: "12px", use: "Standard gap" },
    { token: "4", value: "16px", use: "Component internal padding" },
    { token: "5", value: "20px", use: "Card padding" },
    { token: "6", value: "24px", use: "Section spacing" },
    { token: "8", value: "32px", use: "Large gaps" },
    { token: "10", value: "40px", use: "Section breaks" },
    { token: "12", value: "48px", use: "Major section breaks" },
    { token: "16", value: "64px", use: "Page-level spacing" },
    { token: "20", value: "80px", use: "Hero sections" },
    { token: "24", value: "96px", use: "Massive spacing" },
  ];

  const radiusScale = [
    { token: "sm", value: "4px", use: "Small buttons, chips, badges" },
    { token: "md", value: "6px", use: "Inputs, small cards" },
    { token: "lg", value: "8px", use: "Cards, modals (default)" },
    { token: "xl", value: "12px", use: "Large cards, panels" },
    { token: "full", value: "9999px", use: "Circular elements, pills" },
  ];

  const breakpoints = [
    { name: "sm", width: "640px", columns: 4, gutter: "16px", margin: "16px" },
    { name: "md", width: "768px", columns: 8, gutter: "24px", margin: "24px" },
    { name: "lg", width: "1024px", columns: 12, gutter: "24px", margin: "32px" },
    { name: "xl", width: "1280px", columns: 12, gutter: "32px", margin: "48px" },
    { name: "2xl", width: "1536px", columns: 12, gutter: "32px", margin: "auto" },
  ];

  const contentWidths = [
    { type: "Prose/narrative", width: "680px", use: "Long-form text, articles" },
    { type: "Chat interface", width: "800px", use: "Conversational UI" },
    { type: "Data-heavy views", width: "1200px", use: "Tables, dashboards" },
    { type: "Full-width", width: "1400px", use: "Maximum content width" },
  ];

  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Layout & Spacing</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          A consistent spacing system based on a 4px base unit. Use these tokens
          for margins, padding, and gaps to maintain visual rhythm.
        </p>
      </div>

      {/* Spacing Scale */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Spacing Scale</h2>
        <p className="text-muted-foreground">
          Based on a <strong>4px base unit</strong>. Tailwind classes map directly to these values.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 text-sm font-medium">Token</th>
                <th className="text-left p-3 text-sm font-medium">Value</th>
                <th className="text-left p-3 text-sm font-medium">Visual</th>
                <th className="text-left p-3 text-sm font-medium">Use Case</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {spacingScale.map((item) => (
                <tr key={item.token}>
                  <td className="p-3 font-mono text-sm">space-{item.token}</td>
                  <td className="p-3 font-mono text-sm text-muted-foreground">{item.value}</td>
                  <td className="p-3">
                    {item.value !== "0px" && (
                      <div
                        className="bg-primary/30 h-3 rounded-sm"
                        style={{ width: item.value }}
                      />
                    )}
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">{item.use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Border Radius */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Border Radius</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {radiusScale.map((item) => (
            <div key={item.token} className="rounded-lg border bg-card p-4 text-center">
              <div
                className="mx-auto mb-3 size-16 bg-primary/20 border-2 border-primary"
                style={{ borderRadius: item.value }}
              />
              <p className="font-mono text-sm">rounded-{item.token}</p>
              <p className="text-xs text-muted-foreground">{item.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{item.use}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Grid System */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Grid System</h2>
        <p className="text-muted-foreground">
          12-column grid with responsive breakpoints. Gutters and margins adjust at each breakpoint.
        </p>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 text-sm font-medium">Breakpoint</th>
                <th className="text-left p-3 text-sm font-medium">Min Width</th>
                <th className="text-left p-3 text-sm font-medium">Columns</th>
                <th className="text-left p-3 text-sm font-medium">Gutter</th>
                <th className="text-left p-3 text-sm font-medium">Margin</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {breakpoints.map((bp) => (
                <tr key={bp.name}>
                  <td className="p-3 font-mono text-sm">{bp.name}</td>
                  <td className="p-3 font-mono text-sm text-muted-foreground">{bp.width}</td>
                  <td className="p-3 text-sm">{bp.columns}</td>
                  <td className="p-3 font-mono text-sm text-muted-foreground">{bp.gutter}</td>
                  <td className="p-3 font-mono text-sm text-muted-foreground">{bp.margin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Content Width */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Content Width</h2>
        <p className="text-muted-foreground">
          Optimal content widths for readability. Prose should never exceed 75 characters per line.
        </p>
        <div className="space-y-4">
          {contentWidths.map((item) => (
            <div key={item.type} className="rounded-lg border bg-card p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">{item.type}</span>
                <span className="font-mono text-sm text-muted-foreground">max-w: {item.width}</span>
              </div>
              <div
                className="h-3 bg-primary/20 rounded-sm mb-2"
                style={{ width: `min(100%, ${item.width})` }}
              />
              <p className="text-sm text-muted-foreground">{item.use}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Density Guidelines */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Density Guidelines</h2>
        <p className="text-muted-foreground">
          <strong>Spacious but not sparse.</strong> The interface should feel like there&apos;s room to think.
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Compact</h3>
            <p className="text-sm text-muted-foreground mb-2">For data-dense contexts</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>Row height: 12px padding</li>
              <li>Use in: Tables, lists, dense data</li>
            </ul>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Comfortable</h3>
            <p className="text-sm text-muted-foreground mb-2">Default for most UI</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>Gaps: 16-24px</li>
              <li>Use in: Chat messages, forms, cards</li>
            </ul>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Generous</h3>
            <p className="text-sm text-muted-foreground mb-2">For featured content</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>Padding: 20-24px</li>
              <li>Use in: Cards, modals, panels</li>
            </ul>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Expansive</h3>
            <p className="text-sm text-muted-foreground mb-2">For hero/marketing sections</p>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>Spacing: 48-80px</li>
              <li>Use in: Headers, landing pages</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Component Sizing */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Component Sizing</h2>
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="text-left p-3 text-sm font-medium">Component</th>
                <th className="text-left p-3 text-sm font-medium">Height</th>
                <th className="text-left p-3 text-sm font-medium">Horizontal Padding</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              <tr>
                <td className="p-3 text-sm">Button (sm)</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">32px</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">12px</td>
              </tr>
              <tr>
                <td className="p-3 text-sm">Button (md)</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">40px</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">16px</td>
              </tr>
              <tr>
                <td className="p-3 text-sm">Button (lg)</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">48px</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">20px</td>
              </tr>
              <tr>
                <td className="p-3 text-sm">Input</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">40px</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">12px</td>
              </tr>
              <tr>
                <td className="p-3 text-sm">Card</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">auto</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">20px (all sides)</td>
              </tr>
              <tr>
                <td className="p-3 text-sm">Modal</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">auto</td>
                <td className="p-3 font-mono text-sm text-muted-foreground">24px (all sides)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Usage */}
      <CodeBlock
        collapsible
        label="View Code"
        code={`// Tailwind spacing classes map to the scale
<div className="p-4">      {/* 16px padding */}
<div className="p-5">      {/* 20px padding */}
<div className="gap-6">    {/* 24px gap */}
<div className="mt-12">    {/* 48px top margin */}

// Border radius
<div className="rounded-lg">  {/* 8px - default for cards */}
<div className="rounded-md">  {/* 6px - inputs */}
<div className="rounded-sm">  {/* 4px - small elements */}

// Content width constraints
<div className="max-w-prose">     {/* ~65ch, for text */}
<div className="max-w-3xl">       {/* 768px */}
<div className="max-w-5xl">       {/* 1024px */}`}
      />
    </div>
  );
}
