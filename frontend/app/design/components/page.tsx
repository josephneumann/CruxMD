import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Heart, TrendingUp } from "lucide-react";

const components = [
  {
    name: "Button",
    description: "Clickable elements for actions and navigation",
    href: "/design/components/button",
    preview: (
      <div className="flex gap-2">
        <Button size="sm">Primary</Button>
        <Button size="sm" variant="outline">Outline</Button>
      </div>
    ),
  },
  {
    name: "Badge",
    description: "Status indicators and category labels",
    href: "/design/components/badge",
    preview: (
      <div className="flex gap-2">
        <Badge variant="positive" size="sm">Positive</Badge>
        <Badge variant="warning" size="sm">Warning</Badge>
      </div>
    ),
  },
  {
    name: "Card",
    description: "Container for grouping related content",
    href: "/design/components/card",
    preview: (
      <Card className="px-3 py-2 w-[160px]">
        <div className="flex items-center gap-2">
          <Heart className="size-4 text-primary" strokeWidth={1.5} />
          <span className="text-sm font-semibold">72</span>
          <span className="text-xs text-muted-foreground">bpm</span>
          <div className="flex-1" />
          <TrendingUp className="size-3 text-muted-foreground/40" />
        </div>
      </Card>
    ),
  },
  {
    name: "Alert",
    description: "Clinical insights with severity colors",
    href: "/design/components/alert",
    preview: (
      <div className="flex gap-2">
        <div className="h-6 w-1 rounded-full bg-insight-info" />
        <div className="h-6 w-1 rounded-full bg-insight-warning" />
        <div className="h-6 w-1 rounded-full bg-insight-critical" />
        <div className="h-6 w-1 rounded-full bg-insight-positive" />
      </div>
    ),
  },
  {
    name: "Avatar",
    description: "User profile images with fallback",
    href: "/design/components/avatar",
    preview: (
      <div className="flex -space-x-2">
        <Avatar size="sm">
          <AvatarFallback>JN</AvatarFallback>
        </Avatar>
        <Avatar size="sm">
          <AvatarFallback>AB</AvatarFallback>
        </Avatar>
        <Avatar size="sm">
          <AvatarFallback>CD</AvatarFallback>
        </Avatar>
      </div>
    ),
  },
  {
    name: "Select",
    description: "Dropdown menus for selecting options",
    href: "/design/components/select",
    preview: (
      <Button variant="outline" size="sm" className="w-28 justify-between">
        Select...
        <span className="text-muted-foreground">▼</span>
      </Button>
    ),
  },
];

export default function ComponentsPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Components</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          A collection of reusable UI components built on shadcn/ui and Radix UI
          primitives. Each component is accessible, theme-aware, and designed for
          the clinical context.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {components.map((component) => (
          <Link
            key={component.name}
            href={component.href}
            className="group rounded-lg border bg-card p-6 transition-all hover:shadow-md hover:border-primary/30"
          >
            <div className="mb-4 flex h-20 items-center justify-center rounded-md bg-muted/50">
              {component.preview}
            </div>
            <h3 className="font-semibold group-hover:text-primary transition-colors">
              {component.name}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {component.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
