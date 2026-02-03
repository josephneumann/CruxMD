import Image from "next/image";
import Link from "next/link";
import {
  Sparkles,
  Zap,
  Layers,
  Github,
  Palette,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Header } from "@/components/Header";
import { DemoSection } from "@/components/demo/DemoSection";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <Header />

      <main>
        {/* Hero */}
        <section className="relative flex flex-col items-center justify-center px-8 py-20 md:py-28 overflow-hidden">
          {/* Background image */}
          <Image
            src="/brand/forest-background-watercolor.png"
            alt=""
            fill
            className="object-cover object-center"
            priority
          />
          {/* Overlay for text readability */}
          <div className="absolute inset-0 bg-background/75 dark:bg-background/85" />

          {/* Content */}
          <div className="relative z-10 flex flex-col items-center">
            {/* X Mark */}
            <div className="mb-8">
              <Image
                src="/brand/mark-primary.svg"
                alt=""
                width={80}
                height={80}
                priority
                className="dark:hidden"
              />
              <Image
                src="/brand/mark-reversed.svg"
                alt=""
                width={80}
                height={80}
                priority
                className="hidden dark:block"
              />
            </div>

            {/* Headline */}
            <h1 className="text-3xl md:text-5xl font-medium text-foreground text-center max-w-3xl mb-6 leading-tight">
              Human Presence<br />Machine Precision
            </h1>

            {/* CTA */}
            <Button asChild size="lg">
              <Link href="/chat">Start Now</Link>
            </Button>
          </div>
        </section>

        {/* Trust Bar */}
        <section className="px-8 py-8 border-b border-border">
          <div className="max-w-4xl mx-auto flex flex-col md:flex-row items-center justify-center gap-6 md:gap-12 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4" />
              <span>SOTA clinical models</span>
            </div>
            <div className="flex items-center gap-2">
              <Layers className="size-4" />
              <span>Adapts to your preferences</span>
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
                A swarm of agents for routine work
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Dozens of specialized AI agents work in parallel — reviewing charts,
                flagging abnormals, drafting notes, checking interactions. Each agent
                is an expert at one thing, and together they handle the cognitive
                overhead that buries clinicians in busywork.
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

        {/* Scroll-Triggered Demo */}
        <DemoSection />

        {/* Testimonials */}
        <section className="px-8 py-16 md:py-24">
          <h2 className="text-2xl md:text-3xl font-medium text-foreground text-center mb-12">
            Trusted by over 15,000 doctors
          </h2>
          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-12">
            <div className="flex flex-col items-center">
              <Image
                src="/brand/doctor-watercolor-portrait-1.png"
                alt="Dr. Brian Wilcox"
                width={200}
                height={200}
                className="h-24 w-24 rounded-full object-cover mb-[-3rem] relative z-10"
              />
              <Card className="w-full pt-14">
                <CardContent>
                  <blockquote className="text-lg italic text-foreground text-center">
                    &ldquo;For the first time, I stopped worrying about what I might have
                    missed. I walked into every room knowing the full picture.&rdquo;
                  </blockquote>
                  <div className="mt-4 text-center">
                    <p className="text-sm font-medium text-foreground">Dr. Brian Wilcox, MD</p>
                    <p className="text-xs text-muted-foreground">Internal Medicine</p>
                  </div>
                </CardContent>
              </Card>
            </div>
            <div className="flex flex-col items-center">
              <Image
                src="/brand/doctor-watercolor-portrait-2.png"
                alt="Dr. Priya Patel"
                width={200}
                height={200}
                className="h-24 w-24 rounded-full object-cover mb-[-3rem] relative z-10"
              />
              <Card className="w-full pt-14">
                <CardContent>
                  <blockquote className="text-lg italic text-foreground text-center">
                    &ldquo;I am blown away by how CruxMD seems to know my patients as
                    well as I do, and routinely catches things I wouldn&apos;t.&rdquo;
                  </blockquote>
                  <div className="mt-4 text-center">
                    <p className="text-sm font-medium text-foreground">Dr. Priya Patel, MD</p>
                    <p className="text-xs text-muted-foreground">Family Medicine</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="relative border-t border-border px-8 py-20 md:py-28 overflow-hidden">
          <Image
            src="/brand/medical-office-2.png"
            alt=""
            fill
            className="object-cover object-center"
          />
          <div className="absolute inset-0 bg-background/75 dark:bg-background/85" />
          <div className="relative z-10 max-w-2xl mx-auto text-center">
            <h2 className="text-2xl md:text-3xl font-medium text-foreground mb-2">
              Hire CruxMD to your staff
            </h2>
            <p className="text-muted-foreground mb-8">
              Be present with every patient.
            </p>
            <Button size="lg" asChild>
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
            className="dark:hidden"
          />
          <Image
            src="/brand/wordmark-reversed.svg"
            alt="CruxMD"
            width={100}
            height={24}
            className="hidden dark:block"
          />
          <nav className="flex items-center gap-2">
            <Button variant="ghost" size="icon" asChild>
              <Link href="/design" aria-label="Design System">
                <Palette className="size-5" />
              </Link>
            </Button>
            <Button variant="ghost" size="icon" asChild>
              <a
                href="https://github.com/josephneumann/CruxMD"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="View on GitHub"
              >
                <Github className="size-5" />
              </a>
            </Button>
          </nav>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-6">
          © {new Date().getFullYear()} CruxMD
        </p>
      </footer>
    </div>
  );
}
