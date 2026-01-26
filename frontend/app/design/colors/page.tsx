import { ColorSwatch, ColorGroup } from "@/components/design-system/ColorSwatch";

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
    { name: "Book Cloth", value: "#CC785C", description: "Primary brand" },
    { name: "Kraft", value: "#D4A27F", description: "Warning accents" },
    { name: "Manilla", value: "#EBDBBC", description: "Warm highlights" },
  ],
  accent: [
    { name: "Sage", value: "#7D8B6F", description: "Positive, success states" },
    { name: "Periwinkle", value: "#8B8FC7", description: "Links, selections" },
    { name: "Ochre", value: "#CCA43B", description: "Pending, warm highlights" },
    { name: "Dusty Plum", value: "#5D4B63", description: "Depth, premium accents" },
  ],
  utility: [
    { name: "Focus Blue", value: "#61AAF2", description: "Info/focus states" },
    { name: "Error Red", value: "#BF4D43", description: "Destructive/critical" },
    { name: "White", value: "#FFFFFF", description: "Cards/surfaces" },
    { name: "Black", value: "#000000", description: "Pure black" },
  ],
};

const SEMANTIC_TOKENS = {
  light: [
    { name: "--background", value: "#FAFAF7", description: "Page background" },
    { name: "--foreground", value: "#191919", description: "Primary text" },
    { name: "--card", value: "#FFFFFF", description: "Card background" },
    { name: "--primary", value: "#CC785C", description: "Primary actions" },
    { name: "--secondary", value: "#E5E4DF", description: "Secondary bg" },
    { name: "--muted", value: "#F0F0EB", description: "Muted background" },
    { name: "--muted-foreground", value: "#666663", description: "Muted text" },
    { name: "--accent", value: "#EBDBBC", description: "Accent background" },
    { name: "--border", value: "#E5E4DF", description: "Border color" },
    { name: "--destructive", value: "#BF4D43", description: "Error states" },
    { name: "--ring", value: "#CC785C", description: "Focus ring" },
  ],
  dark: [
    { name: "--background", value: "#191919", description: "Page background" },
    { name: "--foreground", value: "#FAFAF7", description: "Primary text" },
    { name: "--card", value: "#40403E", description: "Card background" },
    { name: "--primary", value: "#CC785C", description: "Primary actions" },
    { name: "--secondary", value: "#40403E", description: "Secondary bg" },
    { name: "--muted", value: "#262625", description: "Muted background" },
    { name: "--muted-foreground", value: "#BFBFBA", description: "Muted text" },
    { name: "--accent", value: "#40403E", description: "Accent background" },
    { name: "--border", value: "#40403E", description: "Border color" },
    { name: "--destructive", value: "#D4645A", description: "Error states" },
    { name: "--ring", value: "#CC785C", description: "Focus ring" },
  ],
};

const INSIGHT_COLORS = {
  light: [
    { name: "Info", value: "#61AAF2", description: "General information" },
    { name: "Warning", value: "#D4A27F", description: "Caution indicators" },
    { name: "Critical", value: "#BF4D43", description: "Urgent alerts" },
    { name: "Positive", value: "#7D8B6F", description: "Favorable findings" },
  ],
  dark: [
    { name: "Info", value: "#7BBAF5", description: "General information" },
    { name: "Warning", value: "#EBDBBC", description: "Caution indicators" },
    { name: "Critical", value: "#D4645A", description: "Urgent alerts" },
    { name: "Positive", value: "#9AAB8F", description: "Favorable findings" },
  ],
};

const CHART_COLORS = {
  light: [
    { name: "Chart 1", value: "#CC785C", description: "Primary data" },
    { name: "Chart 2", value: "#7D8B6F", description: "Secondary data" },
    { name: "Chart 3", value: "#8B8FC7", description: "Tertiary data" },
    { name: "Chart 4", value: "#D4A27F", description: "Quaternary data" },
    { name: "Chart 5", value: "#61AAF2", description: "Quinary data" },
  ],
  dark: [
    { name: "Chart 1", value: "#D4907A", description: "Primary data" },
    { name: "Chart 2", value: "#9AAB8F", description: "Secondary data" },
    { name: "Chart 3", value: "#A5A9D6", description: "Tertiary data" },
    { name: "Chart 4", value: "#EBDBBC", description: "Quaternary data" },
    { name: "Chart 5", value: "#7BBAF5", description: "Quinary data" },
  ],
};

export default function ColorsPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Colors</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          The CruxMD color palette is based on Anthropic&apos;s brand colors, featuring
          warm terracotta tones balanced with neutral slates and ivories. Click any
          swatch to copy the hex value.
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
              Secondary accents that complement the warm brand palette. Sage and Ochre extend
              the warm tones; Periwinkle and Dusty Plum provide cool counterpoints for
              interactive states and visual depth.
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {PALETTE.accent.map((color) => (
              <ColorSwatch
                key={color.name}
                name={color.name}
                value={color.value}
                description={color.description}
                large
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
            has specific background, border, and icon colors.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          <div className="space-y-3">
            <h3 className="text-lg font-medium">Light Mode</h3>
            <div className="grid grid-cols-2 gap-3">
              {INSIGHT_COLORS.light.map((color) => (
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
            <div className="grid grid-cols-2 gap-3">
              {INSIGHT_COLORS.dark.map((color) => (
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
