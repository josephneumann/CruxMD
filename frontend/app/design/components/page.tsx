import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Info } from "lucide-react";

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
    name: "Card",
    description: "Container for grouping related content",
    href: "/design/components/card",
    preview: (
      <Card className="w-40">
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">Card</CardTitle>
          <CardDescription className="text-xs">Description</CardDescription>
        </CardHeader>
      </Card>
    ),
  },
  {
    name: "Alert",
    description: "Display important messages and feedback",
    href: "/design/components/alert",
    preview: (
      <Alert className="w-48">
        <Info className="size-4" />
        <AlertTitle className="text-sm">Alert Title</AlertTitle>
      </Alert>
    ),
  },
  {
    name: "InsightCard",
    description: "Clinical insights with severity colors",
    href: "/design/components/insight-card",
    preview: (
      <div className="flex gap-2">
        <div className="size-6 rounded bg-insight-info" />
        <div className="size-6 rounded bg-insight-warning" />
        <div className="size-6 rounded bg-insight-critical" />
        <div className="size-6 rounded bg-insight-positive" />
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
