import Link from "next/link";
import { Palette, Type, Component, Smile, BookOpen, Image } from "lucide-react";

const sections = [
  {
    title: "Brand",
    description: "Brand identity, voice, principles, and visual guidelines",
    href: "/design/brand",
    icon: BookOpen,
  },
  {
    title: "Assets",
    description: "Logos, wordmarks, and downloadable brand assets",
    href: "/design/assets",
    icon: Image,
  },
  {
    title: "Colors",
    description: "Brand palette, semantic tokens, and clinical insight colors",
    href: "/design/colors",
    icon: Palette,
  },
  {
    title: "Typography",
    description: "Geist font family, heading scale, and body text styles",
    href: "/design/typography",
    icon: Type,
  },
  {
    title: "Components",
    description: "Buttons, cards, tables, charts, and interactive elements",
    href: "/design/components",
    icon: Component,
  },
  {
    title: "Icons",
    description: "Lucide icon set used throughout the application",
    href: "/design/icons",
    icon: Smile,
  },
];

export default function DesignOverviewPage() {
  return (
    <div className="space-y-12">
      {/* Hero */}
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">CruxMD Design System</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          A comprehensive guide to the colors, typography, and components that make up the
          CruxMD clinical intelligence platform. Built on Anthropic&apos;s brand palette with
          warm, professional aesthetics.
        </p>
      </div>

      {/* Design Philosophy */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Design Philosophy</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold mb-2">Warm & Professional</h3>
            <p className="text-sm text-muted-foreground">
              The palette uses warm terracotta and ivory tones inspired by Anthropic&apos;s
              brand, creating an approachable yet trustworthy aesthetic for clinical contexts.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold mb-2">Clinical Clarity</h3>
            <p className="text-sm text-muted-foreground">
              Information hierarchy is paramount. Color-coded insight cards communicate
              urgency at a glance: blue for info, yellow for warning, red for critical,
              green for positive.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold mb-2">Accessible by Default</h3>
            <p className="text-sm text-muted-foreground">
              All color combinations meet WCAG contrast requirements. Dark mode is fully
              supported with carefully tuned values for each semantic token.
            </p>
          </div>
          <div className="rounded-lg border bg-card p-6">
            <h3 className="font-semibold mb-2">Component-First</h3>
            <p className="text-sm text-muted-foreground">
              Built on shadcn/ui primitives with Radix UI accessibility. Components are
              composable, theme-aware, and designed for consistency across the platform.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Explore</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <Link
                key={section.href}
                href={section.href}
                className="group flex items-start gap-4 rounded-lg border bg-card p-6 transition-colors hover:bg-muted/50"
              >
                <div className="rounded-md bg-primary/10 p-2.5">
                  <Icon className="size-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold group-hover:text-primary transition-colors">
                    {section.title}
                  </h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    {section.description}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
