import Image from "next/image";
import Link from "next/link";
import {
  Shield,
  Clock,
  Zap,
  Layers,
  AlertCircle,
  MessageSquare,
  Brain,
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
            The decisive point of care
          </h1>

          {/* Subhead */}
          <p className="text-lg md:text-xl text-muted-foreground text-center max-w-2xl mb-10">
            CruxMD handles the exhaustive review of every lab, medication, and clinical note —
            so you can be fully present with every patient.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Button asChild size="lg">
              <Link href="/chat">Open CruxMD</Link>
            </Button>
            <Button asChild variant="ghost" size="lg">
              <a href="#how-it-works">Learn more</a>
            </Button>
          </div>
        </section>

        {/* Trust Bar */}
        <section className="px-8 py-8 border-b border-border">
          <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Shield className="size-4" />
              <span>HIPAA compliant infrastructure</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="size-4" />
              <span>Complete context in seconds</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="size-4" />
              <span>Integrates with your EHR</span>
            </div>
          </div>
        </section>

        {/* Problem / Solution */}
        <section className="px-8 py-16 md:py-24">
          <div className="max-w-5xl mx-auto grid md:grid-cols-2 gap-12 md:gap-16">
            {/* Problem */}
            <div className="border-l-4 border-primary/30 pl-6">
              <h2 className="text-2xl font-medium text-foreground mb-4">
                The cognitive burden of modern medicine
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Thousands of data points per patient. Labs scattered across systems.
                Specialist notes buried in charts. The constant, quiet fear of missing
                something critical — while trying to maintain the human connection
                that defines great care.
              </p>
            </div>

            {/* Solution */}
            <div className="border-l-4 border-accent pl-6">
              <h2 className="text-2xl font-medium text-foreground mb-4">
                A thinking partner that never misses
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                CruxMD synthesizes complete patient context — every pattern identified,
                every trend surfaced, every connection made. The machine handles the
                exhaustive so you can handle the irreplaceable: the patient in front of you.
              </p>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section className="px-8 py-16 md:py-24 bg-muted/30">
          <div className="max-w-6xl mx-auto">
            <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
              Clinical intelligence, not another dashboard
            </h2>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Feature 1 */}
              <Card>
                <CardHeader>
                  <Layers className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Complete patient synthesis</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Every condition, medication, lab result, and clinical note —
                    woven into a coherent narrative. Ask any question and receive
                    a comprehensive, sourced answer.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 2 */}
              <Card>
                <CardHeader>
                  <AlertCircle className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Insights without alert fatigue</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Abnormal trends flagged in context. Drug interactions surfaced
                    with clinical relevance. Critical findings delivered calmly,
                    clearly, with the information you need to act.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 3 */}
              <Card>
                <CardHeader>
                  <MessageSquare className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Conversational interface</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    Ask questions the way you think about patients.
                    &ldquo;What&apos;s driving the renal decline?&rdquo;
                    &ldquo;Is the A1c trending better?&rdquo;
                    No clicking through tabs or memorizing workflows.
                  </p>
                </CardContent>
              </Card>

              {/* Feature 4 */}
              <Card>
                <CardHeader>
                  <Brain className="h-8 w-8 text-primary mb-2" />
                  <CardTitle>Temporal reasoning</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground text-sm">
                    CruxMD understands time. Lab trends over months. Medication
                    changes and their effects. The clinical story that unfolds
                    across encounters, synthesized automatically.
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
              Fits your workflow
            </h2>

            <div className="flex flex-col md:flex-row items-start md:items-center gap-8 md:gap-4">
              {/* Step 1 */}
              <div className="flex-1 flex flex-col items-center text-center">
                <div className="w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-medium mb-4">
                  1
                </div>
                <h3 className="font-medium text-foreground mb-2">
                  Select a patient
                </h3>
                <p className="text-sm text-muted-foreground">
                  CruxMD connects to your EHR. Patient context loads automatically
                  when you open a chart.
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
                  Ask your question
                </h3>
                <p className="text-sm text-muted-foreground">
                  &ldquo;Summarize this patient.&rdquo; &ldquo;What should I be worried about?&rdquo;
                  &ldquo;How has the kidney function changed?&rdquo;
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
                  Review with confidence
                </h3>
                <p className="text-sm text-muted-foreground">
                  Every insight traces to source. Click through to the original
                  data. Trust, then verify.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Product Preview */}
        <section className="px-8 py-16 md:py-24 bg-muted/30">
          <div className="max-w-2xl mx-auto">
            <p className="text-sm text-muted-foreground text-center mb-4">
              Insights surfaced in context
            </p>
            <InsightCard
              insight={{
                type: "warning",
                title: "Creatinine trend requires attention",
                content:
                  "Creatinine 1.2 → 1.5 → 1.8 mg/dL over 3 months. Wife mentioned increased fatigue at last visit. On lisinopril 20mg for long-standing hypertension. Last nephrology follow-up was 14 months ago.",
                citations: [
                  "Labs: Basic Metabolic Panel",
                  "Encounter: Nov 2024",
                  "Medications: Active",
                ],
              }}
            />
          </div>
        </section>

        {/* Testimonial */}
        <section className="px-8 py-16 md:py-24">
          <Card className="max-w-xl mx-auto">
            <CardContent className="pt-6">
              <blockquote className="text-lg italic text-foreground">
                &ldquo;For the first time, I stopped worrying about what I might have
                missed. I walked into every room knowing the full picture.&rdquo;
              </blockquote>
              <p className="mt-4 text-sm text-muted-foreground">
                — Internal Medicine Physician
              </p>
            </CardContent>
          </Card>
        </section>

        {/* Final CTA */}
        <section className="bg-primary text-primary-foreground px-8 py-16 md:py-20">
          <div className="max-w-2xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium mb-4">
              Be present with every patient
            </h2>
            <p className="text-primary-foreground/80 mb-8">
              Let CruxMD handle the exhaustive. You handle the irreplaceable.
            </p>
            <Button variant="secondary" size="lg" asChild>
              <Link href="/chat">Get Started</Link>
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
            <Link
              href="/design"
              className="hover:text-foreground transition-colors"
            >
              Design System
            </Link>
          </nav>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-6">
          © {new Date().getFullYear()} CruxMD
        </p>
      </footer>
    </div>
  );
}
