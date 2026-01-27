"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Github, Palette } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const wordmarkSrc = mounted && resolvedTheme === "dark"
    ? "/brand/wordmark-reversed.svg"
    : "/brand/wordmark-primary.svg";

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-border">
      <Link href="/">
        <Image
          src={wordmarkSrc}
          alt="CruxMD"
          width={120}
          height={28}
          priority
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
