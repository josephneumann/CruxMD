import Image from "next/image";
import Link from "next/link";
import { Github, Palette } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border">
      <Link href="/">
        <Image
          src="/brand/logos/wordmark-primary.svg"
          alt="CruxMD"
          width={120}
          height={28}
          priority
          className="dark:hidden"
        />
        <Image
          src="/brand/logos/wordmark-reversed.svg"
          alt="CruxMD"
          width={120}
          height={28}
          priority
          className="hidden dark:block"
        />
      </Link>
      <nav className="flex items-center gap-4">
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
    </header>
  );
}
