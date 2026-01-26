import Image from "next/image";
import Link from "next/link";
import { Github } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4 border-b border-border">
        <Link href="/">
          <Image
            src="/brand/wordmark-primary.svg"
            alt="CruxMD"
            width={140}
            height={32}
            priority
          />
        </Link>
        <nav className="flex items-center gap-4">
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
      </header>

      {/* Hero */}
      <main className="flex flex-col items-center justify-center px-8 py-24 bg-muted/30">
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

        {/* Title */}
        <h1 className="text-4xl md:text-5xl font-medium text-foreground text-center mb-4">
          CruxMD
        </h1>

        {/* Tagline */}
        <p className="text-lg text-muted-foreground text-center max-w-xl mb-8">
          Clinical intelligence for physicians. A thinking partner that handles
          the cognitive load so you can focus on what matters: the patient.
        </p>

        {/* CTAs */}
        <div className="flex items-center gap-4">
          <Button asChild size="lg">
            <Link href="/chat">Start Chat</Link>
          </Button>
          <Button asChild variant="outline" size="lg">
            <Link href="/design-system">View Documentation</Link>
          </Button>
        </div>
      </main>

      {/* Footer */}
      <footer className="flex items-center justify-center px-8 py-6 text-sm text-muted-foreground">
        <p>Clinical Intelligence Platform</p>
      </footer>
    </div>
  );
}
