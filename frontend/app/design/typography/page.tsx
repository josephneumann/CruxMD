export default function TypographyPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Typography</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          CruxMD uses the Geist font family from Vercel—a modern, geometric sans-serif
          optimized for interfaces. Geist Mono is used for code and technical content.
        </p>
      </div>

      {/* Font Families */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Font Families</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-lg border bg-card p-6 space-y-4">
            <div>
              <h3 className="text-lg font-semibold">Geist Sans</h3>
              <p className="text-sm text-muted-foreground">Primary typeface</p>
            </div>
            <p className="text-3xl font-light">
              The quick brown fox jumps over the lazy dog
            </p>
            <p className="text-base">
              ABCDEFGHIJKLMNOPQRSTUVWXYZ<br />
              abcdefghijklmnopqrstuvwxyz<br />
              0123456789
            </p>
            <p className="text-sm font-mono text-muted-foreground">
              font-family: var(--font-geist-sans)
            </p>
          </div>

          <div className="rounded-lg border bg-card p-6 space-y-4">
            <div>
              <h3 className="text-lg font-semibold">Geist Mono</h3>
              <p className="text-sm text-muted-foreground">Code & technical content</p>
            </div>
            <p className="text-3xl font-mono font-light">
              The quick brown fox jumps over the lazy dog
            </p>
            <p className="text-base font-mono">
              ABCDEFGHIJKLMNOPQRSTUVWXYZ<br />
              abcdefghijklmnopqrstuvwxyz<br />
              0123456789
            </p>
            <p className="text-sm font-mono text-muted-foreground">
              font-family: var(--font-geist-mono)
            </p>
          </div>
        </div>
      </div>

      {/* Heading Scale */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Heading Scale</h2>
        <div className="space-y-6 rounded-lg border bg-card p-6">
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-5xl font-medium (48px)
            </p>
            <h1 className="text-5xl font-medium tracking-tight">
              Heading 1 — Hero
            </h1>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-4xl font-medium (36px)
            </p>
            <h2 className="text-4xl font-medium tracking-tight">
              Heading 2 — Page Title
            </h2>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-3xl font-medium (30px)
            </p>
            <h3 className="text-3xl font-medium">Heading 3 — Section</h3>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-2xl font-medium (24px)
            </p>
            <h4 className="text-2xl font-medium">Heading 4 — Subsection</h4>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-xl font-semibold (20px)
            </p>
            <h5 className="text-xl font-semibold">Heading 5 — Card Title</h5>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-lg font-semibold (18px)
            </p>
            <h6 className="text-lg font-semibold">Heading 6 — Minor Title</h6>
          </div>
        </div>
      </div>

      {/* Body Text */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Body Text</h2>
        <div className="space-y-6 rounded-lg border bg-card p-6">
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-xl (20px) — Lead paragraph
            </p>
            <p className="text-xl text-muted-foreground leading-relaxed">
              CruxMD is a clinical intelligence platform that helps physicians make
              faster, more informed decisions by combining patient context with AI.
            </p>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-base (16px) — Body text
            </p>
            <p className="text-base leading-relaxed">
              The platform uses a hybrid retrieval system combining vector search and
              knowledge graphs to assemble relevant patient context. This enables
              natural language conversations about patient data with full clinical
              context.
            </p>
          </div>
          <div className="border-b pb-6">
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-sm (14px) — Secondary text
            </p>
            <p className="text-sm text-muted-foreground">
              Patient data is stored in FHIR R4 format and indexed for semantic
              search. The system supports both structured queries and free-form
              clinical questions.
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-2 font-mono">
              text-xs (12px) — Caption / Fine print
            </p>
            <p className="text-xs text-muted-foreground">
              This is an AI-powered demo. Not for clinical use. Always verify
              information with authoritative sources.
            </p>
          </div>
        </div>
      </div>

      {/* Font Weights */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Font Weights</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { weight: "font-light", label: "Light (300)" },
            { weight: "font-normal", label: "Regular (400)" },
            { weight: "font-medium", label: "Medium (500)" },
            { weight: "font-semibold", label: "Semibold (600)" },
          ].map((item) => (
            <div key={item.weight} className="rounded-lg border bg-card p-4 text-center">
              <p className={`text-2xl ${item.weight} mb-2`}>Aa</p>
              <p className="text-xs text-muted-foreground">{item.label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Code Styling */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Code Styling</h2>
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-6">
            <p className="text-xs text-muted-foreground mb-3 font-mono">
              Inline code
            </p>
            <p className="text-base">
              Use the <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">Button</code> component
              for interactive actions. Import it from <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-sm">@/components/ui/button</code>.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <p className="text-xs text-muted-foreground mb-3 font-mono">
              Code block
            </p>
            <pre className="rounded-md bg-muted p-4 overflow-x-auto">
              <code className="text-sm font-mono">{`import { Button } from "@/components/ui/button"

export function MyComponent() {
  return (
    <Button variant="default" size="lg">
      Click me
    </Button>
  )
}`}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
