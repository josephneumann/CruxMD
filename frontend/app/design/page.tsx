import Link from "next/link";
import { Palette, Type, Component, Smile } from "lucide-react";

const sections = [
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
    description: "Buttons, cards, alerts, and interactive elements",
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
        <div className="grid gap-4 md:grid-cols-2">
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

      {/* Color Palette Preview */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Color Palette Preview</h2>
        <div className="flex flex-wrap gap-2">
          {[
            { name: "Slate Dark", color: "#191919" },
            { name: "Slate Medium", color: "#262625" },
            { name: "Slate Light", color: "#40403E" },
            { name: "Cloud Dark", color: "#666663" },
            { name: "Cloud Medium", color: "#91918D" },
            { name: "Cloud Light", color: "#BFBFBA" },
            { name: "Ivory Dark", color: "#E5E4DF" },
            { name: "Ivory Medium", color: "#F0F0EB" },
            { name: "Ivory Light", color: "#FAFAF7" },
            { name: "Book Cloth", color: "#CC785C" },
            { name: "Kraft", color: "#D4A27F" },
            { name: "Manilla", color: "#EBDBBC" },
            { name: "Sage", color: "#7D8B6F" },
            { name: "Periwinkle", color: "#8B8FC7" },
            { name: "Focus Blue", color: "#61AAF2" },
            { name: "Error Red", color: "#BF4D43" },
          ].map((color) => (
            <div
              key={color.name}
              className="size-12 rounded-md border shadow-sm"
              style={{ backgroundColor: color.color }}
              title={`${color.name}: ${color.color}`}
            />
          ))}
        </div>
        <Link
          href="/design/colors"
          className="text-sm text-primary hover:underline"
        >
          View full color documentation →
        </Link>
      </div>
    </div>
  );
}
