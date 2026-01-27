"use client";

import { Check, Copy } from "lucide-react";
import { ColorSwatch, ColorGroup } from "@/components/design-system/ColorSwatch";
import { useCopyToClipboardMulti } from "@/lib/hooks/use-copy-to-clipboard";

interface InsightColorCardProps {
  name: string;
  value: string;
  foreground: string;
  description: string;
}

function InsightColorCard({ name, value, foreground, description }: InsightColorCardProps) {
  const { copiedKey, copy } = useCopyToClipboardMulti<"bg" | "fg">();

  return (
    <div
      className="group rounded-lg border overflow-hidden transition-all hover:shadow-md hover:scale-[1.01]"
      style={{ backgroundColor: value }}
    >
      <div className="flex items-center gap-3 p-3">
        <span
          className="text-sm font-medium flex-1"
          style={{ color: foreground }}
        >
          {name}
        </span>
        <p className="text-xs opacity-75" style={{ color: foreground }}>
          {description}
        </p>
      </div>
      <div className="flex border-t border-white/20">
        <button
          onClick={() => copy(value, "bg")}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-mono transition-all hover:bg-black/10"
          style={{ color: foreground }}
        >
          {copiedKey === "bg" ? (
            <>
              <Check className="size-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              bg: {value}
            </>
          )}
        </button>
        <div className="w-px bg-white/20" />
        <button
          onClick={() => copy(foreground, "fg")}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 text-xs font-mono transition-all hover:bg-black/10"
          style={{ color: foreground }}
        >
          {copiedKey === "fg" ? (
            <>
              <Check className="size-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="size-3 opacity-0 group-hover:opacity-100 transition-opacity" />
              fg: {foreground}
            </>
          )}
        </button>
      </div>
    </div>
  );
}

const PALETTE = {
  slate: [
    { name: "Slate Dark", value: "#191919", description: "Primary text" },
    { name: "Slate Medium", value: "#262625", description: "Dark surfaces" },
    { name: "Slate Light", value: "#40403E", description: "Dark borders" },
  ],
  cloud: [
    { name: "Cloud Dark", value: "#666663", description: "Muted foreground" },
    { name: "Cloud Medium", value: "#91918D", description: "Secondary text" },
    { name: "Cloud Light", value: "#BFBFBA", description: "Dark muted text" },
  ],
  ivory: [
    { name: "Ivory Dark", value: "#E5E4DF", description: "Borders" },
    { name: "Ivory Medium", value: "#F0F0EB", description: "Muted background" },
    { name: "Ivory Light", value: "#FAFAF7", description: "Page background" },
  ],
  warm: [
    { name: "Vibrant Forest", value: "#2F5E52", description: "Primary brand" },
    { name: "Golden Resin", value: "#D9A036", description: "Warning accents" },
    { name: "Alabaster", value: "#F0EAD6", description: "Warm highlights" },
  ],
  accent: [
    { name: "Jade Green", value: "#388E3C", description: "Positive, success states" },
    { name: "Glacier Teal", value: "#5A7D7C", description: "Links, selections" },
    { name: "Midnight Pine", value: "#1B3A34", description: "Depth, premium accents" },
  ],
  utility: [
    { name: "Steel Blue", value: "#4A7A8C", description: "Info/focus states" },
    { name: "Berry Red", value: "#C24E42", description: "Destructive/critical" },
    { name: "White", value: "#FFFFFF", description: "Cards/surfaces" },
    { name: "Black", value: "#000000", description: "Pure black" },
  ],
};

const SEMANTIC_TOKENS = {
  light: [
    { name: "--background", value: "#FAFAF7", description: "Page background" },
    { name: "--foreground", value: "#191919", description: "Primary text" },
    { name: "--card", value: "#FFFFFF", description: "Card background" },
    { name: "--primary", value: "#2F5E52", description: "Primary actions" },
    { name: "--secondary", value: "#E5E4DF", description: "Secondary bg" },
    { name: "--muted", value: "#F0F0EB", description: "Muted background" },
    { name: "--muted-foreground", value: "#666663", description: "Muted text" },
    { name: "--accent", value: "#F0EAD6", description: "Accent background" },
    { name: "--border", value: "#E5E4DF", description: "Border color" },
    { name: "--destructive", value: "#C24E42", description: "Error states" },
    { name: "--ring", value: "#2F5E52", description: "Focus ring" },
  ],
  dark: [
    { name: "--background", value: "#191919", description: "Page background" },
    { name: "--foreground", value: "#FAFAF7", description: "Primary text" },
    { name: "--card", value: "#40403E", description: "Card background" },
    { name: "--primary", value: "#3A7A6A", description: "Primary actions" },
    { name: "--secondary", value: "#40403E", description: "Secondary bg" },
    { name: "--muted", value: "#262625", description: "Muted background" },
    { name: "--muted-foreground", value: "#BFBFBA", description: "Muted text" },
    { name: "--accent", value: "#40403E", description: "Accent background" },
    { name: "--border", value: "#40403E", description: "Border color" },
    { name: "--destructive", value: "#D46F65", description: "Error states" },
    { name: "--ring", value: "#3A7A6A", description: "Focus ring" },
  ],
};

const INSIGHT_COLORS = {
  light: [
    { name: "Info", value: "#4A7A8C", foreground: "#FFFFFF", description: "General information" },
    { name: "Warning", value: "#D9A036", foreground: "#191919", description: "Caution indicators" },
    { name: "Critical", value: "#C24E42", foreground: "#FFFFFF", description: "Urgent alerts" },
    { name: "Positive", value: "#388E3C", foreground: "#FFFFFF", description: "Favorable findings" },
  ],
  dark: [
    { name: "Info", value: "#749BB0", foreground: "#191919", description: "General information" },
    { name: "Warning", value: "#EBC47C", foreground: "#191919", description: "Caution indicators" },
    { name: "Critical", value: "#D46F65", foreground: "#FFFFFF", description: "Urgent alerts" },
    { name: "Positive", value: "#66BB6A", foreground: "#191919", description: "Favorable findings" },
  ],
};

const CHART_COLORS = {
  light: [
    { name: "Chart 1", value: "#2F5E52", description: "Primary data" },
    { name: "Chart 2", value: "#D9A036", description: "Secondary data" },
    { name: "Chart 3", value: "#C24E42", description: "Tertiary data" },
    { name: "Chart 4", value: "#4A7A8C", description: "Quaternary data" },
    { name: "Chart 5", value: "#388E3C", description: "Quinary data" },
  ],
  dark: [
    { name: "Chart 1", value: "#4A9A88", description: "Primary data" },
    { name: "Chart 2", value: "#EBC47C", description: "Secondary data" },
    { name: "Chart 3", value: "#D46F65", description: "Tertiary data" },
    { name: "Chart 4", value: "#749BB0", description: "Quaternary data" },
    { name: "Chart 5", value: "#66BB6A", description: "Quinary data" },
  ],
};

export default function ColorsPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Colors</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          The CruxMD color palette features organic greens, teals, and golds
          balanced with neutral slates and ivories. Click any swatch to copy the hex value.
        </p>
      </div>

      {/* Core Palette */}
      <div className="space-y-8">
        <h2 className="text-2xl font-medium">Core Palette</h2>
        <ColorGroup title="Slate (Darks)" colors={PALETTE.slate} />
        <ColorGroup title="Cloud (Grays)" colors={PALETTE.cloud} />
        <ColorGroup title="Ivory (Lights)" colors={PALETTE.ivory} />
        <ColorGroup title="Warm (Brand)" colors={PALETTE.warm} />

        {/* Accent Colors with expanded description */}
        <div className="space-y-3">
          <div>
            <h3 className="text-lg font-medium">Accent Colors</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Secondary accents that complement the forest brand palette. Jade Green signals
              success; Glacier Teal and Midnight Pine provide depth for interactive states
              and visual hierarchy.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {PALETTE.accent.map((color) => (
              <ColorSwatch
                key={color.name}
                name={color.name}
                value={color.value}
                description={color.description}
              />
            ))}
          </div>
        </div>

        <ColorGroup title="Utility" colors={PALETTE.utility} />
      </div>

      {/* Semantic Tokens */}
      <div className="space-y-8">
        <div className="space-y-2">
          <h2 className="text-2xl font-medium">Semantic Tokens</h2>
          <p className="text-muted-foreground">
            These CSS variables adapt automatically between light and dark modes.
          </p>
          <div className="rounded-lg border bg-muted/50 p-4 text-sm">
            <p className="font-medium mb-2">Design Notes</p>
            <ul className="text-muted-foreground space-y-1">
              <li><strong>Dark mode accent</strong> — Intentionally neutral (Slate) rather than warm for better contrast and reduced eye strain</li>
              <li><strong>Secondary = Border</strong> — In light mode, secondary background matches border color for seamless subtle backgrounds</li>
            </ul>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Light Mode</h3>
            <div className="space-y-2">
              {SEMANTIC_TOKENS.light.map((token) => (
                <div
                  key={token.name}
                  className="flex items-center gap-3 rounded-md border p-2"
                >
                  <div
                    className="size-8 rounded border shrink-0"
                    style={{ backgroundColor: token.value }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-mono truncate">{token.name}</p>
                    <p className="text-xs text-muted-foreground">{token.description}</p>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground shrink-0">
                    {token.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-lg font-medium">Dark Mode</h3>
            <div className="space-y-2">
              {SEMANTIC_TOKENS.dark.map((token) => (
                <div
                  key={token.name}
                  className="flex items-center gap-3 rounded-md border p-2"
                >
                  <div
                    className="size-8 rounded border shrink-0"
                    style={{ backgroundColor: token.value }}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-mono truncate">{token.name}</p>
                    <p className="text-xs text-muted-foreground">{token.description}</p>
                  </div>
                  <span className="text-xs font-mono text-muted-foreground shrink-0">
                    {token.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Clinical Insight Colors */}
      <div className="space-y-8">
        <div className="space-y-2">
          <h2 className="text-2xl font-medium">Clinical Insight Colors</h2>
          <p className="text-muted-foreground">
            Color-coded severity levels for clinical alerts and insights. Each type
            has specific background and foreground colors for proper contrast.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-3">
            <h3 className="text-lg font-medium">Light Mode</h3>
            <div className="space-y-2">
              {INSIGHT_COLORS.light.map((color) => (
                <InsightColorCard
                  key={color.name}
                  name={color.name}
                  value={color.value}
                  foreground={color.foreground}
                  description={color.description}
                />
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-lg font-medium">Dark Mode</h3>
            <div className="space-y-2">
              {INSIGHT_COLORS.dark.map((color) => (
                <InsightColorCard
                  key={color.name}
                  name={color.name}
                  value={color.value}
                  foreground={color.foreground}
                  description={color.description}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Chart Colors */}
      <div className="space-y-8">
        <div className="space-y-2">
          <h2 className="text-2xl font-medium">Chart Colors</h2>
          <p className="text-muted-foreground">
            A harmonious palette for data visualization. Dark mode uses lighter
            variants for better contrast on dark backgrounds.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-3">
            <h3 className="text-lg font-medium">Light Mode</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {CHART_COLORS.light.map((color) => (
                <ColorSwatch
                  key={color.name}
                  name={color.name}
                  value={color.value}
                  description={color.description}
                />
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-lg font-medium">Dark Mode</h3>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {CHART_COLORS.dark.map((color) => (
                <ColorSwatch
                  key={color.name}
                  name={color.name}
                  value={color.value}
                  description={color.description}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
