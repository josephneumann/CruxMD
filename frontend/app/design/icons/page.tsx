"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

// Only icons actually used in the CruxMD codebase
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Brain,
  CheckCircle,
  CheckSquare,
  ChevronDown,
  ChevronUp,
  Clock,
  Code,
  Component,
  Database,
  Eye,
  Github,
  Heart,
  Info,
  Layers,
  Loader2,
  Lock,
  Mail,
  MessageSquare,
  Monitor,
  Moon,
  MoreHorizontal,
  Palette,
  PanelLeft,
  PanelLeftClose,
  Plus,
  Search,
  Settings,
  Smile,
  Sparkles,
  Sun,
  Terminal,
  Type,
  Users,
  Zap,
} from "lucide-react";

interface IconInfo {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  category: string;
}

// Icons organized by actual usage in the codebase
const icons: IconInfo[] = [
  // Navigation & UI
  { name: "ArrowLeft", icon: ArrowLeft, category: "Navigation" },
  { name: "ArrowRight", icon: ArrowRight, category: "Navigation" },
  { name: "ChevronDown", icon: ChevronDown, category: "Navigation" },
  { name: "ChevronUp", icon: ChevronUp, category: "Navigation" },
  { name: "PanelLeft", icon: PanelLeft, category: "Navigation" },
  { name: "PanelLeftClose", icon: PanelLeftClose, category: "Navigation" },

  // Actions
  { name: "Plus", icon: Plus, category: "Actions" },
  { name: "Search", icon: Search, category: "Actions" },
  { name: "Settings", icon: Settings, category: "Actions" },
  { name: "Copy", icon: Copy, category: "Actions" },
  { name: "Eye", icon: Eye, category: "Actions" },
  { name: "MoreHorizontal", icon: MoreHorizontal, category: "Actions" },

  // Status & Feedback
  { name: "Info", icon: Info, category: "Status" },
  { name: "AlertCircle", icon: AlertCircle, category: "Status" },
  { name: "AlertTriangle", icon: AlertTriangle, category: "Status" },
  { name: "CheckCircle", icon: CheckCircle, category: "Status" },
  { name: "Check", icon: Check, category: "Status" },
  { name: "Loader2", icon: Loader2, category: "Status" },

  // Communication
  { name: "Mail", icon: Mail, category: "Communication" },
  { name: "MessageSquare", icon: MessageSquare, category: "Communication" },

  // Users
  { name: "Users", icon: Users, category: "Users" },

  // Data & Content
  { name: "Database", icon: Database, category: "Data" },
  { name: "Code", icon: Code, category: "Data" },
  { name: "Layers", icon: Layers, category: "Data" },
  { name: "Terminal", icon: Terminal, category: "Data" },

  // Theme
  { name: "Sun", icon: Sun, category: "Theme" },
  { name: "Moon", icon: Moon, category: "Theme" },
  { name: "Monitor", icon: Monitor, category: "Theme" },

  // AI/Models
  { name: "Brain", icon: Brain, category: "AI" },
  { name: "Sparkles", icon: Sparkles, category: "AI" },
  { name: "Zap", icon: Zap, category: "AI" },

  // Design System (used in docs sidebar)
  { name: "Palette", icon: Palette, category: "Design" },
  { name: "Type", icon: Type, category: "Design" },
  { name: "Component", icon: Component, category: "Design" },
  { name: "Smile", icon: Smile, category: "Design" },

  // Misc
  { name: "Github", icon: Github, category: "Brand" },
  { name: "Heart", icon: Heart, category: "Misc" },
  { name: "Lock", icon: Lock, category: "Misc" },
  { name: "Clock", icon: Clock, category: "Misc" },
  { name: "CheckSquare", icon: CheckSquare, category: "Misc" },
];

function IconCard({ icon: Icon, name }: { icon: React.ComponentType<{ className?: string }>; name: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(`<${name} />`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className={cn(
        "group flex flex-col items-center gap-2 rounded-lg border bg-card p-4 transition-all",
        "hover:bg-muted/50 hover:shadow-sm",
        copied && "border-primary bg-primary/5"
      )}
    >
      <Icon className="size-6 text-foreground" />
      <span className="text-xs text-muted-foreground group-hover:text-foreground truncate w-full text-center">
        {copied ? (
          <span className="flex items-center justify-center gap-1 text-primary">
            <Check className="size-3" /> Copied
          </span>
        ) : (
          name
        )}
      </span>
    </button>
  );
}

export default function IconsPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = Array.from(new Set(icons.map((i) => i.category))).sort();

  const filteredIcons = icons.filter((icon) => {
    const matchesSearch = icon.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = !selectedCategory || icon.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const iconsByCategory = filteredIcons.reduce((acc, icon) => {
    if (!acc[icon.category]) {
      acc[icon.category] = [];
    }
    acc[icon.category].push(icon);
    return acc;
  }, {} as Record<string, IconInfo[]>);

  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Icons</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          CruxMD uses{" "}
          <a
            href="https://lucide.dev"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline"
          >
            Lucide React
          </a>{" "}
          for icons. These are the icons currently used in the application.
          Click any icon to copy its JSX.
        </p>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search icons..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full rounded-md border bg-background pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setSelectedCategory(null)}
            className={cn(
              "px-3 py-1.5 text-sm rounded-md border transition-colors",
              !selectedCategory
                ? "bg-primary text-primary-foreground"
                : "bg-card hover:bg-muted"
            )}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
              className={cn(
                "px-3 py-1.5 text-sm rounded-md border transition-colors",
                selectedCategory === cat
                  ? "bg-primary text-primary-foreground"
                  : "bg-card hover:bg-muted"
              )}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Icons Grid by Category */}
      <div className="space-y-10">
        {Object.entries(iconsByCategory)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([category, categoryIcons]) => (
            <div key={category} className="space-y-4">
              <h2 className="text-xl font-medium">{category}</h2>
              <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-10 gap-2">
                {categoryIcons.map((icon) => (
                  <IconCard key={icon.name} icon={icon.icon} name={icon.name} />
                ))}
              </div>
            </div>
          ))}
      </div>

      {filteredIcons.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          No icons found matching &quot;{searchTerm}&quot;
        </div>
      )}

      {/* Usage */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Usage</h2>
        <div className="rounded-lg border bg-muted p-4">
          <pre className="text-sm font-mono overflow-x-auto">
            <code>{`import { ArrowRight, Check, AlertCircle } from "lucide-react"

// In your component
<Button>
  Continue
  <ArrowRight className="size-4" />
</Button>`}</code>
          </pre>
        </div>
      </div>

      {/* Size Reference */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Size Reference</h2>
        <div className="flex items-end gap-6">
          {[
            { size: "size-3", label: "12px (size-3)" },
            { size: "size-4", label: "16px (size-4)" },
            { size: "size-5", label: "20px (size-5)" },
            { size: "size-6", label: "24px (size-6)" },
            { size: "size-8", label: "32px (size-8)" },
          ].map((item) => (
            <div key={item.size} className="flex flex-col items-center gap-2">
              <Heart className={item.size} />
              <span className="text-xs text-muted-foreground">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
