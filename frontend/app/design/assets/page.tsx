"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";
import { CodeBlock } from "@/components/design-system/CodeBlock";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

interface AssetCardProps {
  name: string;
  src: string;
  description?: string;
  bgClass?: string;
  width?: number;
  height?: number;
}

function AssetCard({ name, src, description, bgClass = "bg-white", width = 200, height = 60 }: AssetCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(src);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="group rounded-lg border overflow-hidden transition-all hover:shadow-md">
      <div className={cn("flex items-center justify-center p-8 min-h-[120px]", bgClass)}>
        <Image
          src={src}
          alt={name}
          width={width}
          height={height}
          className="object-contain"
        />
      </div>
      <div className="bg-card p-4 border-t">
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-medium text-sm">{name}</p>
            {description && (
              <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
            )}
            <p className="text-xs font-mono text-muted-foreground mt-1">{src}</p>
          </div>
          <button
            onClick={handleCopy}
            className="p-1.5 rounded hover:bg-muted transition-colors"
            title="Copy path"
          >
            {copied ? (
              <Check className="size-4 text-primary" />
            ) : (
              <Copy className="size-4 text-muted-foreground" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function AssetSection({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-medium">{title}</h2>
        {description && <p className="text-muted-foreground mt-1">{description}</p>}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {children}
      </div>
    </div>
  );
}

export default function AssetsPage() {
  const [lottieData, setLottieData] = useState<object | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then((data) => setLottieData(data));
  }, []);

  const handleCopyPath = async (path: string) => {
    await navigator.clipboard.writeText(path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Brand Assets</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Official CruxMD logos, wordmarks, and brand assets. Click the copy button
          to copy the file path for use in your code.
        </p>
      </div>

      {/* Wordmarks */}
      <AssetSection
        title="Wordmarks"
        description="Full logo with CruxMD text. Use these for headers and prominent placements."
      >
        <AssetCard
          name="Primary Wordmark"
          src="/brand/wordmark-primary.svg"
          description="Use on light backgrounds"
          bgClass="bg-white"
        />
        <AssetCard
          name="Reversed Wordmark"
          src="/brand/wordmark-reversed.svg"
          description="Use on dark backgrounds"
          bgClass="bg-slate-900"
        />
        <AssetCard
          name="Mono Dark Wordmark"
          src="/brand/wordmark-mono-dark.svg"
          description="Single color, dark variant"
          bgClass="bg-white"
        />
        <AssetCard
          name="Mono Light Wordmark"
          src="/brand/wordmark-mono-light.svg"
          description="Single color, light variant"
          bgClass="bg-slate-900"
        />
      </AssetSection>

      {/* Marks */}
      <AssetSection
        title="Marks"
        description="Icon-only versions for compact spaces like favicons and app icons."
      >
        <AssetCard
          name="Primary Mark"
          src="/brand/mark-primary.svg"
          description="Use on light backgrounds"
          bgClass="bg-white"
          width={48}
          height={48}
        />
        <AssetCard
          name="Reversed Mark"
          src="/brand/mark-reversed.svg"
          description="Use on dark backgrounds"
          bgClass="bg-slate-900"
          width={48}
          height={48}
        />
        <AssetCard
          name="Mono Dark Mark"
          src="/brand/mark-mono-dark.svg"
          description="Single color, dark variant"
          bgClass="bg-white"
          width={48}
          height={48}
        />
        <AssetCard
          name="Mono Light Mark"
          src="/brand/mark-mono-light.svg"
          description="Single color, light variant"
          bgClass="bg-slate-900"
          width={48}
          height={48}
        />
      </AssetSection>

      {/* Animated Spinner */}
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-medium">Animated Spinner</h2>
          <p className="text-muted-foreground mt-1">
            Lottie animation for loading states and thinking indicators. Works on both light and dark backgrounds.
          </p>
        </div>

        {/* Preview on both backgrounds */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="group rounded-lg border overflow-hidden transition-all hover:shadow-md">
            <div className="flex items-center justify-center p-8 min-h-[120px] bg-white">
              {lottieData ? (
                <div className="w-16 h-16">
                  <Lottie
                    animationData={lottieData}
                    loop={true}
                    style={{ width: "100%", height: "100%" }}
                  />
                </div>
              ) : (
                <div className="w-16 h-16 rounded-full bg-muted animate-pulse" />
              )}
            </div>
            <div className="bg-card p-4 border-t">
              <p className="font-medium text-sm">Light Background</p>
            </div>
          </div>
          <div className="group rounded-lg border overflow-hidden transition-all hover:shadow-md">
            <div className="flex items-center justify-center p-8 min-h-[120px] bg-slate-900">
              {lottieData ? (
                <div className="w-16 h-16">
                  <Lottie
                    animationData={lottieData}
                    loop={true}
                    style={{ width: "100%", height: "100%" }}
                  />
                </div>
              ) : (
                <div className="w-16 h-16 rounded-full bg-slate-700 animate-pulse" />
              )}
            </div>
            <div className="bg-card p-4 border-t">
              <p className="font-medium text-sm">Dark Background</p>
            </div>
          </div>
        </div>

        {/* File Format Options */}
        <div className="rounded-lg border bg-card p-5 space-y-4">
          <h3 className="font-medium">File Formats</h3>
          <p className="text-sm text-muted-foreground">
            The spinner is available in two Lottie formats. Both contain the same animation and work on any background.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">/brand/crux-spin.json</code>
                <button
                  onClick={() => handleCopyPath("/brand/crux-spin.json")}
                  className="p-1.5 rounded hover:bg-muted transition-colors"
                  title="Copy path"
                >
                  {copied ? (
                    <Check className="size-4 text-primary" />
                  ) : (
                    <Copy className="size-4 text-muted-foreground" />
                  )}
                </button>
              </div>
              <p className="text-sm text-muted-foreground">
                <strong>JSON format.</strong> Human-readable, easy to inspect and modify. Works directly with lottie-react via fetch + JSON parse. Recommended for web.
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <code className="text-sm font-mono bg-muted px-2 py-1 rounded">/brand/crux-spin.lottie</code>
                <button
                  onClick={() => handleCopyPath("/brand/crux-spin.lottie")}
                  className="p-1.5 rounded hover:bg-muted transition-colors"
                  title="Copy path"
                >
                  {copied ? (
                    <Check className="size-4 text-primary" />
                  ) : (
                    <Copy className="size-4 text-muted-foreground" />
                  )}
                </button>
              </div>
              <p className="text-sm text-muted-foreground">
                <strong>dotLottie format.</strong> Compressed binary (zip) containing JSON + embedded assets. Smaller file size. Requires @dotlottie/react-player or similar library.
              </p>
            </div>
          </div>
        </div>

        <CodeBlock
          collapsible
          label="Usage with lottie-react (.json)"
          code={`import dynamic from "next/dynamic";
import { useState, useEffect } from "react";

const Lottie = dynamic(() => import("lottie-react"), { ssr: false });

function SpinningLogo() {
  const [lottieData, setLottieData] = useState<object | null>(null);

  useEffect(() => {
    fetch("/brand/crux-spin.json")
      .then((res) => res.json())
      .then((data) => setLottieData(data));
  }, []);

  if (!lottieData) return null;

  return (
    <div className="w-10 h-10">
      <Lottie
        animationData={lottieData}
        loop={true}
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}`}
        />
      </div>

      {/* Favicons */}
      <AssetSection
        title="Favicons & App Icons"
        description="Icons for browser tabs, bookmarks, and mobile home screens."
      >
        <AssetCard
          name="SVG Favicon"
          src="/favicon.svg"
          description="Scalable vector favicon"
          bgClass="bg-slate-100"
          width={48}
          height={48}
        />
        <AssetCard
          name="Apple Touch Icon"
          src="/apple-touch-icon.png"
          description="180x180 for iOS home screen"
          bgClass="bg-slate-100"
          width={60}
          height={60}
        />
        <AssetCard
          name="PWA Icon 192"
          src="/pwa-192x192.png"
          description="192x192 for PWA manifest"
          bgClass="bg-slate-100"
          width={48}
          height={48}
        />
        <AssetCard
          name="PWA Icon 512"
          src="/pwa-512x512.png"
          description="512x512 for PWA splash"
          bgClass="bg-slate-100"
          width={64}
          height={64}
        />
      </AssetSection>

      {/* Social / OG Images */}
      <AssetSection
        title="Social Media"
        description="Open Graph images for link previews on social platforms."
      >
        <AssetCard
          name="OG Image"
          src="/og-image.png"
          description="1200x630 for Facebook, LinkedIn"
          bgClass="bg-slate-100"
          width={240}
          height={126}
        />
        <AssetCard
          name="Twitter Card"
          src="/og-image-twitter.png"
          description="1200x600 for Twitter/X"
          bgClass="bg-slate-100"
          width={240}
          height={120}
        />
      </AssetSection>

      {/* Usage Guidelines */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Usage Guidelines</h2>
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div>
            <h3 className="font-medium">Clear Space</h3>
            <p className="text-sm text-muted-foreground">
              Maintain a minimum clear space around the logo equal to the height of the &quot;C&quot; in CruxMD.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Minimum Size</h3>
            <p className="text-sm text-muted-foreground">
              Wordmarks should be no smaller than 80px wide. Marks should be no smaller than 24px.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Background Selection</h3>
            <p className="text-sm text-muted-foreground">
              Use primary/mono-dark variants on light backgrounds. Use reversed/mono-light variants on dark backgrounds.
              Ensure sufficient contrast for accessibility.
            </p>
          </div>
          <div>
            <h3 className="font-medium">Don&apos;t</h3>
            <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
              <li>Stretch or distort the logo</li>
              <li>Change the logo colors outside approved variants</li>
              <li>Add effects like shadows or gradients</li>
              <li>Place on busy or low-contrast backgrounds</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Code Example */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Usage in Code</h2>
        <CodeBlock
          collapsible
          label="Theme-Aware Logo Component"
          code={`import Image from "next/image"
import { useTheme } from "next-themes"

function Logo() {
  const { resolvedTheme } = useTheme()

  const src = resolvedTheme === "dark"
    ? "/brand/wordmark-reversed.svg"
    : "/brand/wordmark-primary.svg"

  return (
    <Image
      src={src}
      alt="CruxMD"
      width={100}
      height={24}
      priority
    />
  )
}`}
        />
      </div>

      {/* HTML Implementation */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">HTML Implementation</h2>
        <p className="text-muted-foreground">
          Add these tags to your document head for complete favicon and social sharing support.
        </p>

        <div className="space-y-4">
          <CodeBlock
            collapsible
            label="Minimal Head Tags"
            language="html"
            code={`<!-- Favicon (SVG + ICO fallback) -->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon.ico" sizes="32x32">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" href="/apple-touch-icon.png">

<!-- Web App Manifest -->
<link rel="manifest" href="/manifest.webmanifest">

<!-- Theme Color -->
<meta name="theme-color" content="#CC785C">`}
          />

          <CodeBlock
            collapsible
            label="Open Graph (Social Sharing)"
            language="html"
            code={`<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:image" content="https://cruxmd.ai/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="CruxMD - Clinical Intelligence">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://cruxmd.ai/og-image-twitter.png">`}
          />

          <CodeBlock
            collapsible
            label="manifest.webmanifest"
            language="json"
            code={`{
  "name": "CruxMD",
  "short_name": "CruxMD",
  "description": "Clinical intelligence for physicians",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#FAFAF7",
  "theme_color": "#CC785C",
  "icons": [
    {
      "src": "/pwa-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/pwa-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    },
    {
      "src": "/pwa-maskable-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "maskable"
    }
  ]
}`}
          />
        </div>
      </div>
    </div>
  );
}
