import Image from "next/image";
import Link from "next/link";
import {
  Lock,
  Clock,
  Code,
  Layers,
  AlertCircle,
  MessageSquare,
  Database,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { InsightCard } from "@/components/clinical/InsightCard";
import { Header } from "@/components/Header";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main>
        {/* Hero */}
        <section className="flex flex-col items-center justify-center px-8 py-20 md:py-28 bg-muted/30">
          {/* X Mark */}
          <div className="mb-8">
            <Image
              src="/brand/mark-primary.svg"
              alt=""
              width={80}
              height={80}
              priority
            />
          </div>

          {/* Headline */}
          <h1 className="text-3xl md:text-5xl font-medium text-foreground text-center max-w-3xl mb-6 leading-tight">
            Clinical Intelligence Platform
          </h1>

          {/* Subhead */}
          <p className="text-lg md:text-xl text-muted-foreground text-center max-w-2xl mb-10">
            CruxMD reviews every lab, every medication, every past encounter —
            so you can stop double-checking and start thinking.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Button asChild size="lg">
              <Link href="/chat">Start Chat</Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <a href="#how-it-works">See how it works</a>
            </Button>
          </div>
        </section>

        {/* Trust Bar */}
        <section className="px-8 py-8 border-b border-border">
          <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Lock className="size-4" />
              <span>Synthetic data only — no PHI</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="size-4" />
              <span>Context in seconds, not minutes</span>
            </div>
            <div className="flex items-center gap-2">
              <Code className="size-4" />
              <span>FHIR R4 native architecture</span>
            </div>
          </div>
        </section>

        {/* Problem / Solution */}
        <section className="px-8 py-16 md:py-24">
          <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-12 md:gap-16">
            {/* Problem */}
            <div className="border-l-4 border-primary/30 pl-6">
              <h2 className="text-2xl font-medium text-foreground mb-4">
                Modern medicine is drowning in data.
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Every patient encounter means hundreds of data points. Labs,
                medications, allergies, past visits, specialist notes —
                scattered across systems. The fear of missing something critical
                never goes away.
              </p>
            </div>

            {/* Solution */}
            <div className="border-l-4 border-accent pl-6">
              <h2 className="text-2xl font-medium text-foreground mb-4">
                CruxMD reviews everything. You focus on the patient.
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                A thinking partner that synthesizes complete patient context —
                every detail surfaced, every pattern identified, every follow-up
                suggested. Not another dashboard. Clinical intelligence that
                handles the exhaustive so you can handle the irreplaceable.
              </p>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="px-8 py-16 md:py-24 bg-muted/30">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
              Built for clinical thinking
            </h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Feature 1 */}
              <Card>
                <CardHeader>
                  <Layers className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Complete patient context</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Every condition, medication, lab result, and clinical note —
                    synthesized into a coherent narrative. Ask "What's going on
                    with this patient?" and get a comprehensive answer.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 2 */}
              <Card>
                <CardHeader>
                  <AlertCircle className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Meaningful clinical insights</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Abnormal trends flagged. Drug interactions surfaced.
                    Critical findings highlighted. Insights that matter,
                    delivered without alert fatigue.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 3 */}
              <Card>
                <CardHeader>
                  <MessageSquare className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Ask questions in plain English</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    "What's driving the kidney decline?" "Is the diabetes
                    well-controlled?" The interface adapts to your clinical
                    questions — no clicking through tabs.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 4 */}
              <Card>
                <CardHeader>
                  <Database className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Works with your data</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Built on FHIR R4. Load patient bundles directly — no custom
                    integrations. The universal language of healthcare data.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section id="how-it-works" className="px-8 py-16 md:py-24 scroll-mt-16">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
              How it works
            </h2>

            <div className="flex flex-col md:flex-row items-start md:items-center gap-8 md:gap-4">
              {/* Step 1 */}
              <div className="flex-1 flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium mb-4">
                  1
                </div>
                <h3 className="font-medium text-foreground mb-2">
                  Load patient data
                </h3>
                <p className="text-sm text-muted-foreground">
                  Import FHIR bundles from your EHR or explore with synthetic
                  patients.
                </p>
              </div>

              {/* Connector */}
              <div className="hidden md:block w-12 h-px bg-border" />

              {/* Step 2 */}
              <div className="flex-1 flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium mb-4">
                  2
                </div>
                <h3 className="font-medium text-foreground mb-2">
                  Ask a clinical question
                </h3>
                <p className="text-sm text-muted-foreground">
                  "Summarize this patient." "What's concerning in the labs?" "Is
                  the HbA1c trending better?"
                </p>
              </div>

              {/* Connector */}
              <div className="hidden md:block w-12 h-px bg-border" />

              {/* Step 3 */}
              <div className="flex-1 flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium mb-4">
                  3
                </div>
                <h3 className="font-medium text-foreground mb-2">
                  Get actionable context
                </h3>
                <p className="text-sm text-muted-foreground">
                  CruxMD surfaces relevant data, highlights insights, and
                  suggests follow-up questions — all in one conversation.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Product Preview */}
        <section className="px-8 py-16 md:py-24 bg-muted/30">
          <div className="max-w-2xl mx-auto">
            <p className="text-sm text-muted-foreground text-center mb-4">
              Example insight from CruxMD:
            </p>
            <InsightCard
              insight={{
                type: "warning",
                title: "Creatinine trend with context",
                content:
                  "Creatinine 1.2 → 1.5 → 1.8 mg/dL over 3 months. Of note: wife mentioned at last visit that he's been more fatigued. Long-standing hypertension, on lisinopril 20mg. Hasn't had nephrology follow-up since 2023.",
                citations: [
                  "Observation/lab-001",
                  "Encounter/note-2024-11",
                  "MedicationStatement/lisinopril",
                ],
              }}
            />
          </div>
        </section>

        {/* Social Proof */}
        <section className="px-8 py-16 md:py-24">
          <Card className="max-w-xl mx-auto">
            <CardContent className="pt-6">
              <blockquote className="text-lg italic text-foreground">
                "For the first time, I stopped worrying about what I might have
                missed. CruxMD reviewed the chart faster than I could open the
                tabs."
              </blockquote>
              <p className="mt-4 text-sm text-muted-foreground">
                — Dr. Sarah Chen, Internal Medicine
                <span className="block text-xs mt-1">
                  [Fictional — replace with real testimonial]
                </span>
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Final CTA */}
        <section className="bg-primary text-primary-foreground px-8 py-16 md:py-20">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4">
              Ready to stop missing things?
            </h2>
            <p className="text-primary-foreground/80 mb-8">
              Start with a synthetic patient. No signup required.
            </p>
            <Button variant="secondary" size="lg" asChild>
              <Link href="/chat">Start Chat</Link>
            </Button>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border px-8 py-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <Image
            src="/brand/wordmark-primary.svg"
            alt="CruxMD"
            width={100}
            height={24}
          />
          <nav className="flex gap-6 text-sm text-muted-foreground">
            <a
              href="https://github.com/josephneumann/CruxMD"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              GitHub
            </a>
            <Link
              href="/design-system"
              className="hover:text-foreground transition-colors"
            >
              Documentation
            </Link>
          </nav>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-6">
          For demonstration purposes only. Not for clinical use.
        </p>
      </footer>
    </div>
  );
}
