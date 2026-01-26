"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { CodeBlock } from "@/components/design-system/CodeBlock";

// Clinical & Medical Icons
import {
  Activity,
  Ambulance,
  Apple,
  Baby,
  Bandage,
  Beaker,
  Bed,
  BedDouble,
  Biohazard,
  Bone,
  BrainCircuit,
  Briefcase,
  Calendar,
  CalendarCheck,
  CalendarClock,
  CalendarDays,
  Cigarette,
  CircleDot,
  CircleOff,
  Clipboard,
  ClipboardCheck,
  ClipboardList,
  ClipboardPlus,
  Cross,
  Dna,
  Droplet,
  Droplets,
  Ear,
  EarOff,
  Eye,
  EyeOff,
  FileHeart,
  FileText,
  FileClock,
  FileSearch,
  FileWarning,
  FlaskConical,
  FlaskRound,
  Footprints,
  Gauge,
  GlassWater,
  Grab,
  Hand,
  HeartCrack,
  HeartHandshake,
  HeartOff,
  HeartPulse,
  Hospital,
  Hourglass,
  Infinity,
  Leaf,
  LineChart,
  ListChecks,
  Microscope,
  Moon,
  MoveVertical,
  Newspaper,
  Orbit,
  PersonStanding,
  Pill,
  PillBottle,
  Radiation,
  Refrigerator,
  Ruler,
  Scale,
  Scan,
  ScanLine,
  Scissors,
  ShieldAlert,
  ShieldCheck,
  ShieldPlus,
  Shrub,
  Skull,
  Snowflake,
  Sparkle,
  Stethoscope,
  Syringe,
  Target,
  TestTube,
  TestTubes,
  Thermometer,
  ThermometerSnowflake,
  ThermometerSun,
  Timer,
  TrendingDown,
  TrendingUp,
  Utensils,
  Vegan,
  Vibrate,
  Waypoints,
  Weight,
  Wind,
  Wine,
  X,
  Zap,
} from "lucide-react";

// Navigation & UI
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
  Github,
  Heart,
  Info,
  Layers,
  Loader2,
  Lock,
  Mail,
  MessageSquare,
  Monitor,
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
} from "lucide-react";

interface IconInfo {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  category: string;
}

const icons: IconInfo[] = [
  // ===== CLINICAL ICONS =====

  // Vitals & Monitoring
  { name: "Activity", icon: Activity, category: "Vitals" },
  { name: "HeartPulse", icon: HeartPulse, category: "Vitals" },
  { name: "Heart", icon: Heart, category: "Vitals" },
  { name: "HeartCrack", icon: HeartCrack, category: "Vitals" },
  { name: "HeartOff", icon: HeartOff, category: "Vitals" },
  { name: "Thermometer", icon: Thermometer, category: "Vitals" },
  { name: "ThermometerSun", icon: ThermometerSun, category: "Vitals" },
  { name: "ThermometerSnowflake", icon: ThermometerSnowflake, category: "Vitals" },
  { name: "Gauge", icon: Gauge, category: "Vitals" },
  { name: "Scale", icon: Scale, category: "Vitals" },
  { name: "Weight", icon: Weight, category: "Vitals" },
  { name: "Ruler", icon: Ruler, category: "Vitals" },
  { name: "TrendingUp", icon: TrendingUp, category: "Vitals" },
  { name: "TrendingDown", icon: TrendingDown, category: "Vitals" },
  { name: "LineChart", icon: LineChart, category: "Vitals" },

  // Labs & Diagnostics
  { name: "TestTube", icon: TestTube, category: "Labs" },
  { name: "TestTubes", icon: TestTubes, category: "Labs" },
  { name: "FlaskConical", icon: FlaskConical, category: "Labs" },
  { name: "FlaskRound", icon: FlaskRound, category: "Labs" },
  { name: "Beaker", icon: Beaker, category: "Labs" },
  { name: "Microscope", icon: Microscope, category: "Labs" },
  { name: "Droplet", icon: Droplet, category: "Labs" },
  { name: "Droplets", icon: Droplets, category: "Labs" },
  { name: "Dna", icon: Dna, category: "Labs" },
  { name: "Scan", icon: Scan, category: "Labs" },
  { name: "ScanLine", icon: ScanLine, category: "Labs" },
  { name: "CircleDot", icon: CircleDot, category: "Labs" },
  { name: "Radiation", icon: Radiation, category: "Labs" },

  // Medications & Treatment
  { name: "Pill", icon: Pill, category: "Medications" },
  { name: "PillBottle", icon: PillBottle, category: "Medications" },
  { name: "Syringe", icon: Syringe, category: "Medications" },
  { name: "Bandage", icon: Bandage, category: "Medications" },
  { name: "Scissors", icon: Scissors, category: "Medications" },
  { name: "Stethoscope", icon: Stethoscope, category: "Medications" },
  { name: "Cross", icon: Cross, category: "Medications" },
  { name: "ShieldPlus", icon: ShieldPlus, category: "Medications" },
  { name: "Zap", icon: Zap, category: "Medications" },

  // Anatomy & Body
  { name: "Brain", icon: Brain, category: "Anatomy" },
  { name: "BrainCircuit", icon: BrainCircuit, category: "Anatomy" },
  { name: "Eye", icon: Eye, category: "Anatomy" },
  { name: "EyeOff", icon: EyeOff, category: "Anatomy" },
  { name: "Ear", icon: Ear, category: "Anatomy" },
  { name: "EarOff", icon: EarOff, category: "Anatomy" },
  { name: "Bone", icon: Bone, category: "Anatomy" },
  { name: "Skull", icon: Skull, category: "Anatomy" },
  { name: "Hand", icon: Hand, category: "Anatomy" },
  { name: "Grab", icon: Grab, category: "Anatomy" },
  { name: "Footprints", icon: Footprints, category: "Anatomy" },
  { name: "PersonStanding", icon: PersonStanding, category: "Anatomy" },
  { name: "Wind", icon: Wind, category: "Anatomy" },

  // Patient & Care
  { name: "Baby", icon: Baby, category: "Patient" },
  { name: "Bed", icon: Bed, category: "Patient" },
  { name: "BedDouble", icon: BedDouble, category: "Patient" },
  { name: "HeartHandshake", icon: HeartHandshake, category: "Patient" },
  { name: "Users", icon: Users, category: "Patient" },

  // Facilities & Equipment
  { name: "Hospital", icon: Hospital, category: "Facilities" },
  { name: "Ambulance", icon: Ambulance, category: "Facilities" },
  { name: "Refrigerator", icon: Refrigerator, category: "Facilities" },

  // Clinical Documentation
  { name: "FileText", icon: FileText, category: "Documentation" },
  { name: "FileHeart", icon: FileHeart, category: "Documentation" },
  { name: "FileClock", icon: FileClock, category: "Documentation" },
  { name: "FileSearch", icon: FileSearch, category: "Documentation" },
  { name: "FileWarning", icon: FileWarning, category: "Documentation" },
  { name: "Clipboard", icon: Clipboard, category: "Documentation" },
  { name: "ClipboardList", icon: ClipboardList, category: "Documentation" },
  { name: "ClipboardCheck", icon: ClipboardCheck, category: "Documentation" },
  { name: "ClipboardPlus", icon: ClipboardPlus, category: "Documentation" },
  { name: "ListChecks", icon: ListChecks, category: "Documentation" },
  { name: "Newspaper", icon: Newspaper, category: "Documentation" },

  // Scheduling & Time
  { name: "Calendar", icon: Calendar, category: "Scheduling" },
  { name: "CalendarDays", icon: CalendarDays, category: "Scheduling" },
  { name: "CalendarCheck", icon: CalendarCheck, category: "Scheduling" },
  { name: "CalendarClock", icon: CalendarClock, category: "Scheduling" },
  { name: "Clock", icon: Clock, category: "Scheduling" },
  { name: "Timer", icon: Timer, category: "Scheduling" },
  { name: "Hourglass", icon: Hourglass, category: "Scheduling" },

  // Allergies & Warnings
  { name: "ShieldAlert", icon: ShieldAlert, category: "Alerts" },
  { name: "ShieldCheck", icon: ShieldCheck, category: "Alerts" },
  { name: "AlertCircle", icon: AlertCircle, category: "Alerts" },
  { name: "AlertTriangle", icon: AlertTriangle, category: "Alerts" },
  { name: "Biohazard", icon: Biohazard, category: "Alerts" },
  { name: "CircleOff", icon: CircleOff, category: "Alerts" },
  { name: "X", icon: X, category: "Alerts" },

  // Lifestyle & Social History
  { name: "Cigarette", icon: Cigarette, category: "Lifestyle" },
  { name: "Wine", icon: Wine, category: "Lifestyle" },
  { name: "Apple", icon: Apple, category: "Lifestyle" },
  { name: "Utensils", icon: Utensils, category: "Lifestyle" },
  { name: "Vegan", icon: Vegan, category: "Lifestyle" },
  { name: "Leaf", icon: Leaf, category: "Lifestyle" },
  { name: "Shrub", icon: Shrub, category: "Lifestyle" },
  { name: "GlassWater", icon: GlassWater, category: "Lifestyle" },
  { name: "Moon", icon: Moon, category: "Lifestyle" },
  { name: "Sun", icon: Sun, category: "Lifestyle" },
  { name: "Snowflake", icon: Snowflake, category: "Lifestyle" },

  // AI & Intelligence
  { name: "Sparkles", icon: Sparkles, category: "AI" },
  { name: "Sparkle", icon: Sparkle, category: "AI" },
  { name: "Target", icon: Target, category: "AI" },
  { name: "Waypoints", icon: Waypoints, category: "AI" },
  { name: "Orbit", icon: Orbit, category: "AI" },
  { name: "Infinity", icon: Infinity, category: "AI" },

  // ===== UI ICONS =====

  // Navigation
  { name: "ArrowLeft", icon: ArrowLeft, category: "Navigation" },
  { name: "ArrowRight", icon: ArrowRight, category: "Navigation" },
  { name: "ChevronDown", icon: ChevronDown, category: "Navigation" },
  { name: "ChevronUp", icon: ChevronUp, category: "Navigation" },
  { name: "PanelLeft", icon: PanelLeft, category: "Navigation" },
  { name: "PanelLeftClose", icon: PanelLeftClose, category: "Navigation" },
  { name: "MoveVertical", icon: MoveVertical, category: "Navigation" },

  // Actions
  { name: "Plus", icon: Plus, category: "Actions" },
  { name: "Search", icon: Search, category: "Actions" },
  { name: "Settings", icon: Settings, category: "Actions" },
  { name: "Copy", icon: Copy, category: "Actions" },
  { name: "MoreHorizontal", icon: MoreHorizontal, category: "Actions" },
  { name: "Vibrate", icon: Vibrate, category: "Actions" },

  // Status
  { name: "Info", icon: Info, category: "Status" },
  { name: "CheckCircle", icon: CheckCircle, category: "Status" },
  { name: "Check", icon: Check, category: "Status" },
  { name: "CheckSquare", icon: CheckSquare, category: "Status" },
  { name: "Loader2", icon: Loader2, category: "Status" },

  // Communication
  { name: "Mail", icon: Mail, category: "Communication" },
  { name: "MessageSquare", icon: MessageSquare, category: "Communication" },

  // Data & System
  { name: "Database", icon: Database, category: "System" },
  { name: "Code", icon: Code, category: "System" },
  { name: "Layers", icon: Layers, category: "System" },
  { name: "Terminal", icon: Terminal, category: "System" },
  { name: "Monitor", icon: Monitor, category: "System" },
  { name: "Lock", icon: Lock, category: "System" },
  { name: "Briefcase", icon: Briefcase, category: "System" },

  // Design System
  { name: "Palette", icon: Palette, category: "Design" },
  { name: "Type", icon: Type, category: "Design" },
  { name: "Component", icon: Component, category: "Design" },
  { name: "Smile", icon: Smile, category: "Design" },

  // Brand
  { name: "Github", icon: Github, category: "Brand" },
];

// Define category order (clinical first)
const categoryOrder = [
  "Vitals",
  "Labs",
  "Medications",
  "Anatomy",
  "Patient",
  "Facilities",
  "Documentation",
  "Scheduling",
  "Alerts",
  "Lifestyle",
  "AI",
  "Navigation",
  "Actions",
  "Status",
  "Communication",
  "System",
  "Design",
  "Brand",
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

  const categories = Array.from(new Set(icons.map((i) => i.category)));
  // Sort categories by defined order
  const sortedCategories = categories.sort((a, b) => {
    const aIndex = categoryOrder.indexOf(a);
    const bIndex = categoryOrder.indexOf(b);
    return aIndex - bIndex;
  });

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

  // Sort the grouped icons by category order
  const sortedIconsByCategory = Object.entries(iconsByCategory).sort(([a], [b]) => {
    const aIndex = categoryOrder.indexOf(a);
    const bIndex = categoryOrder.indexOf(b);
    return aIndex - bIndex;
  });

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
          for icons. Clinical icons are highlighted first for easy reference.
          Click any icon to copy its JSX.
        </p>
      </div>

      {/* Search and Filter */}
      <div className="space-y-4">
        <div className="relative max-w-md">
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
            All ({icons.length})
          </button>
          {sortedCategories.map((cat) => (
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
        {sortedIconsByCategory.map(([category, categoryIcons]) => (
          <div key={category} className="space-y-4">
            <h2 className="text-xl font-medium flex items-center gap-2">
              {category}
              <span className="text-sm font-normal text-muted-foreground">
                ({categoryIcons.length})
              </span>
            </h2>
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
      <CodeBlock
        collapsible
        label="View Code"
        code={`import { Stethoscope, Pill, HeartPulse, TestTube } from "lucide-react"

// Clinical icons in components
<Badge variant="periwinkle" className="gap-1">
  <FlaskConical className="size-3" />
  Lab
</Badge>

// Vitals with trend indicators
<div className="flex items-center gap-2">
  <HeartPulse className="size-4 text-primary" />
  <span>72 bpm</span>
  <TrendingUp className="size-3 text-muted-foreground" />
</div>

// Medication list item
<div className="flex items-center gap-2">
  <Pill className="size-4" />
  <span>Lisinopril 10mg</span>
</div>`}
      />

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
              <Stethoscope className={item.size} />
              <span className="text-xs text-muted-foreground">{item.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Guidelines */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Usage Guidelines</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Icon Sizing</h3>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li><code className="text-xs bg-muted px-1 py-0.5 rounded">size-3</code> — Inline with small text, badges</li>
              <li><code className="text-xs bg-muted px-1 py-0.5 rounded">size-4</code> — Buttons, form fields, lists</li>
              <li><code className="text-xs bg-muted px-1 py-0.5 rounded">size-5</code> — Navigation, card headers</li>
              <li><code className="text-xs bg-muted px-1 py-0.5 rounded">size-6</code> — Feature icons, empty states</li>
            </ul>
          </div>
          <div className="rounded-lg border bg-card p-5">
            <h3 className="font-medium mb-3">Clinical Conventions</h3>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li><strong>Labs</strong> — FlaskConical, TestTube for lab results</li>
              <li><strong>Medications</strong> — Pill for meds, Syringe for injections</li>
              <li><strong>Vitals</strong> — HeartPulse for HR, Activity for BP</li>
              <li><strong>Alerts</strong> — ShieldAlert for allergies, AlertCircle for warnings</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
