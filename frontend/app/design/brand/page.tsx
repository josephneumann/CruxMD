import NextImage from "next/image";
import { Check, X } from "lucide-react";

function Principle({ number, title, description }: { number: number; title: string; description: string }) {
  return (
    <div className="rounded-lg border bg-card p-5">
      <div className="flex items-start gap-4">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-medium text-primary">
          {number}
        </span>
        <div>
          <h3 className="font-medium">{title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  );
}

function DoItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <Check className="mt-0.5 size-4 shrink-0 text-insight-positive" />
      <span className="text-sm">{children}</span>
    </div>
  );
}

function DontItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2">
      <X className="mt-0.5 size-4 shrink-0 text-insight-critical" />
      <span className="text-sm">{children}</span>
    </div>
  );
}

function VoiceExample({ context, tone }: { context: string; tone: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b last:border-0">
      <span className="text-sm font-medium">{context}</span>
      <span className="text-sm text-muted-foreground">{tone}</span>
    </div>
  );
}

export default function BrandPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Brand Identity</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          CruxMD exists at the crux—where clinical data becomes clinical insight.
          This guide covers the brand foundation, voice, and visual principles.
        </p>
      </div>

      {/* Brand Essence */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Brand Essence</h2>
        <div className="rounded-lg border bg-primary/5 border-primary/20 p-6">
          <p className="text-xl font-medium text-center">&ldquo;Human Presence. Machine Precision.&rdquo;</p>
        </div>
        <p className="text-muted-foreground">
          CruxMD handles the cognitive load of recall and pattern recognition so physicians
          can focus on what only humans can do: be present with patients.
        </p>
      </div>

      {/* Mission & Vision */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Mission & Vision</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider mb-2">Mission</h3>
            <p className="text-sm">
              To give physicians the confidence that nothing is missed, so they can focus on what matters: the patient in front of them.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wider mb-2">Vision</h3>
            <p className="text-sm">
              A world where clinical intelligence amplifies human care rather than replacing it—where technology handles the exhaustive so physicians can handle the irreplaceable.
            </p>
          </div>
        </div>
      </div>

      {/* Brand Statement */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Brand Statement</h2>
        <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground">
          CruxMD is a thinking partner for physicians who refuse to choose between thoroughness
          and presence. It&apos;s the quiet confidence of knowing nothing is missed—freeing clinicians
          to bring their full humanity to every patient encounter.
        </blockquote>
        <p className="text-sm text-muted-foreground">
          Premium without flash. Capable without noise. The tool that elevates care by getting out of the way.
        </p>
      </div>

      {/* Name Etymology */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Name Etymology</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-lg border bg-card p-4">
            <p className="font-mono text-lg font-medium">Crux</p>
            <p className="text-sm text-muted-foreground mt-1">
              The decisive or most important point; the heart of the matter
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="font-mono text-lg font-medium">MD</p>
            <p className="text-sm text-muted-foreground mt-1">
              Medical Doctor — the user, not the data. The physician is centered.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="font-mono text-lg font-medium">Together</p>
            <p className="text-sm text-muted-foreground mt-1">
              The decisive point for the physician. Where data becomes insight becomes action.
            </p>
          </div>
        </div>
      </div>

      {/* Brand Principles */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Brand Principles</h2>
        <div className="grid gap-4">
          <Principle
            number={1}
            title="Quiet Competence"
            description="The interface speaks through work, not words. No celebratory animations, no achievement badges. Trust is built through reliability, not reassurance."
          />
          <Principle
            number={2}
            title="Earned Confidence"
            description="Clinicians should feel certain, not hopeful. Every insight traces to source. The goal isn't to impress—it's to be trusted."
          />
          <Principle
            number={3}
            title="Creative Unblocking"
            description="When cognitive burden lifts, physicians rediscover curiosity. CruxMD creates space for questions that matter."
          />
          <Principle
            number={4}
            title="Understated Premium"
            description="Quality is in the details others don't notice: information hierarchy that feels obvious, interactions that require no explanation."
          />
          <Principle
            number={5}
            title="Human Presence, Machine Precision"
            description="The machine is precise so the doctor can be present. CruxMD handles the exhaustive so clinicians can handle the irreplaceable."
          />
        </div>
      </div>

      {/* Central Metaphor */}
      <div className="space-y-6">
        <div className="relative -mx-8 overflow-hidden rounded-none py-16 md:py-20 flex flex-col items-center justify-center">
          <NextImage
            src="/brand/backgrounds/office.png"
            alt=""
            fill
            className="object-cover object-center"
          />
          <div className="absolute inset-0 bg-background/70 dark:bg-background/80" />
          <h2 className="relative z-10 text-2xl font-medium mb-4">The Central Metaphor</h2>
          <p className="relative z-10 italic text-center text-lg max-w-2xl px-6">
            &ldquo;A well-organized study with natural wood elements and medical textbooks — with a view of a forested hillside in the early morning mist. Evoking the metaphor of seeing the forest through the trees.&rdquo;
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
          <div className="space-y-3">
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">The study</span>
              <span className="text-sm text-muted-foreground">Clean organization, logical hierarchy</span>
            </div>
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">Natural wood</span>
              <span className="text-sm text-muted-foreground">Organic warmth, grounded and tactile</span>
            </div>
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">Textbooks</span>
              <span className="text-sm text-muted-foreground">Typography like well-set literature</span>
            </div>
          </div>
          <div className="space-y-3">
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">The forest</span>
              <span className="text-sm text-muted-foreground">Depth of data, layered context to navigate</span>
            </div>
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">The trees</span>
              <span className="text-sm text-muted-foreground">Individual data points made clear and distinct</span>
            </div>
            <div className="flex gap-3">
              <span className="font-medium text-sm w-28 shrink-0">Morning mist</span>
              <span className="text-sm text-muted-foreground">Information reveals itself gradually, with clarity</span>
            </div>
          </div>
        </div>
      </div>

      {/* Voice & Tone */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Voice & Tone</h2>
        <p className="text-muted-foreground">
          CruxMD speaks with <strong>quiet competence</strong>. The voice stays consistent; tone adjusts to context.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Voice Attributes</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="font-medium">Confident</span>
                <span className="text-muted-foreground">&ldquo;Creatinine trending up.&rdquo;</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Direct</span>
                <span className="text-muted-foreground">&ldquo;3 active conditions.&rdquo;</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Calm</span>
                <span className="text-muted-foreground">&ldquo;Unable to retrieve labs.&rdquo;</span>
              </div>
              <div className="flex justify-between">
                <span className="font-medium">Helpful</span>
                <span className="text-muted-foreground">&ldquo;Related: renal function&rdquo;</span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Tone by Context</h3>
            <VoiceExample context="Success states" tone="Matter-of-fact, not celebratory" />
            <VoiceExample context="Error states" tone="Clear, actionable, never cute" />
            <VoiceExample context="Empty states" tone="Neutral, not sad or urging" />
            <VoiceExample context="Critical findings" tone="Serious but not alarming" />
          </div>
        </div>
      </div>

      {/* Writing Examples */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Writing Guidelines</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h3 className="font-medium text-insight-positive">Do</h3>
            <div className="space-y-3">
              <DoItem>&ldquo;Medications for John Smith&rdquo;</DoItem>
              <DoItem>&ldquo;Last updated 2 hours ago&rdquo;</DoItem>
              <DoItem>&ldquo;No medications on file.&rdquo;</DoItem>
              <DoItem>&ldquo;Unable to load labs. Check connection.&rdquo;</DoItem>
              <DoItem>&ldquo;Send message&rdquo; (specific action)</DoItem>
            </div>
          </div>
          <div className="space-y-4">
            <h3 className="font-medium text-insight-critical">Don&apos;t</h3>
            <div className="space-y-3">
              <DontItem>&ldquo;Patient Medications&rdquo; (generic)</DontItem>
              <DontItem>&ldquo;Synced!&rdquo; (exclamatory)</DontItem>
              <DontItem>&ldquo;No meds found! Add some?&rdquo; (pushy)</DontItem>
              <DontItem>&ldquo;Oops! We couldn&apos;t get your labs :(</DontItem>
              <DontItem>&ldquo;Submit&rdquo; or &ldquo;Click here&rdquo; (vague)</DontItem>
            </div>
          </div>
        </div>
      </div>

      {/* What CruxMD Is Not */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">What CruxMD Is Not</h2>
        <div className="rounded-lg border bg-card overflow-hidden">
          <div className="grid grid-cols-3 gap-4 p-4 border-b bg-muted/50 text-sm font-medium">
            <span>Rejection</span>
            <span>Meaning</span>
            <span>Avoid</span>
          </div>
          {[
            { rejection: "Not enterprise", meaning: "No admin complexity", avoid: "Permission matrices, role management" },
            { rejection: "Not startup-y", meaning: "No growth hacking", avoid: "\"Invite friends to unlock!\"" },
            { rejection: "Not gimmicky", meaning: "No AI theater", avoid: "Typing animations, \"thinking deeply...\"" },
            { rejection: "Not futuristic", meaning: "No sci-fi aesthetics", avoid: "Glowing edges, neon accents" },
            { rejection: "Not clinical-sterile", meaning: "No hospital coldness", avoid: "Pure white + blue, stock photos" },
          ].map((row) => (
            <div key={row.rejection} className="grid grid-cols-3 gap-4 p-4 border-b last:border-0 text-sm">
              <span className="font-medium">{row.rejection}</span>
              <span className="text-muted-foreground">{row.meaning}</span>
              <span className="text-muted-foreground">{row.avoid}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Visual Do's and Don'ts */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Visual Guidelines</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-4 text-insight-positive">Do</h3>
            <div className="space-y-3">
              <DoItem>Use Vibrant Forest sparingly for emphasis</DoItem>
              <DoItem>Let Ivory and White dominate</DoItem>
              <DoItem>Use subtle, purposeful transitions</DoItem>
              <DoItem>Give content room to breathe</DoItem>
              <DoItem>Use icons functionally</DoItem>
              <DoItem>Keep charts clean and data-forward</DoItem>
            </div>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-4 text-insight-critical">Don&apos;t</h3>
            <div className="space-y-3">
              <DontItem>Saturate interface with green</DontItem>
              <DontItem>Use pure gray (#808080)</DontItem>
              <DontItem>Animate everything</DontItem>
              <DontItem>Pack information densely everywhere</DontItem>
              <DontItem>Use icons decoratively</DontItem>
              <DontItem>Add 3D effects or gradients to charts</DontItem>
            </div>
          </div>
        </div>
      </div>

      {/* Reference */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Reference</h2>
        <p className="text-sm text-muted-foreground">
          Full brand identity documentation available at{" "}
          <code className="px-1.5 py-0.5 rounded bg-muted font-mono text-xs">docs/brand/brand-identity.md</code>
        </p>
      </div>
    </div>
  );
}
