import { Button } from "@/components/ui/button";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { ArrowRight, Plus, Mail, Loader2, Heart, Settings, Github, X, Menu, Bell, Search } from "lucide-react";

const buttonProps = [
  {
    name: "variant",
    type: '"default" | "destructive" | "outline" | "secondary" | "ghost" | "link"',
    default: '"default"',
    description: "The visual style of the button",
  },
  {
    name: "size",
    type: '"default" | "xs" | "sm" | "lg" | "icon" | "icon-xs" | "icon-sm" | "icon-lg"',
    default: '"default"',
    description: "The size of the button",
  },
  {
    name: "asChild",
    type: "boolean",
    default: "false",
    description: "Render as child element (for links)",
  },
  {
    name: "disabled",
    type: "boolean",
    default: "false",
    description: "Disable the button",
  },
];

export default function ButtonPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Button</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Buttons trigger actions or navigation. They come in multiple variants
          and sizes to fit different contexts and importance levels.
        </p>
      </div>

      {/* Variants */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Variants</h2>
        <PreviewGrid cols={3}>
          <ComponentPreview
            title="Default"
            description="Primary actions"
            code={`<Button>Click me</Button>`}
          >
            <Button>Click me</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Destructive"
            description="Dangerous or irreversible actions"
            code={`<Button variant="destructive">Delete</Button>`}
          >
            <Button variant="destructive">Delete</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Outline"
            description="Secondary actions with border"
            code={`<Button variant="outline">Outline</Button>`}
          >
            <Button variant="outline">Outline</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Secondary"
            description="Less prominent actions"
            code={`<Button variant="secondary">Secondary</Button>`}
          >
            <Button variant="secondary">Secondary</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Ghost"
            description="Subtle, borderless buttons"
            code={`<Button variant="ghost">Ghost</Button>`}
          >
            <Button variant="ghost">Ghost</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Link"
            description="Styled as a link"
            code={`<Button variant="link">Learn more</Button>`}
          >
            <Button variant="link">Learn more</Button>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Sizes */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sizes</h2>
        <ComponentPreview
          title="Size comparison"
          description="Available button sizes from xs to lg"
          code={`<Button size="xs">Extra Small</Button>
<Button size="sm">Small</Button>
<Button size="default">Default</Button>
<Button size="lg">Large</Button>`}
        >
          <div className="flex items-center gap-4 flex-wrap">
            <Button size="xs">Extra Small</Button>
            <Button size="sm">Small</Button>
            <Button size="default">Default</Button>
            <Button size="lg">Large</Button>
          </div>
        </ComponentPreview>
      </div>

      {/* With Icons */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Icons</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Leading icon"
            description="Icon before the text"
            code={`<Button>
  <Mail className="size-4" />
  Send Email
</Button>`}
          >
            <Button>
              <Mail className="size-4" />
              Send Email
            </Button>
          </ComponentPreview>

          <ComponentPreview
            title="Trailing icon"
            description="Icon after the text"
            code={`<Button>
  Continue
  <ArrowRight className="size-4" />
</Button>`}
          >
            <Button>
              Continue
              <ArrowRight className="size-4" />
            </Button>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Icon-only buttons */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Icon Buttons</h2>
        <ComponentPreview
          title="Icon-only sizes"
          description="Square buttons for icons only"
          code={`<Button size="icon-xs" variant="ghost"><Plus /></Button>
<Button size="icon-sm" variant="outline"><Settings /></Button>
<Button size="icon"><Heart /></Button>
<Button size="icon-lg"><Mail /></Button>`}
        >
          <div className="flex items-center gap-4">
            <Button size="icon-xs" variant="ghost">
              <Plus className="size-3" />
            </Button>
            <Button size="icon-sm" variant="outline">
              <Settings className="size-4" />
            </Button>
            <Button size="icon">
              <Heart className="size-4" />
            </Button>
            <Button size="icon-lg">
              <Mail className="size-4" />
            </Button>
          </div>
        </ComponentPreview>
      </div>

      {/* Ghost Icon Buttons */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Ghost Icon Buttons</h2>
        <p className="text-muted-foreground">
          Minimal icon buttons for toolbars, headers, and secondary actions. Used for the GitHub link in the header.
        </p>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Navigation icons"
            description="Header and toolbar actions"
            code={`<Button variant="ghost" size="icon">
  <Github className="size-5" />
</Button>
<Button variant="ghost" size="icon">
  <Menu className="size-5" />
</Button>
<Button variant="ghost" size="icon">
  <X className="size-5" />
</Button>`}
          >
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon">
                <Github className="size-5" />
              </Button>
              <Button variant="ghost" size="icon">
                <Menu className="size-5" />
              </Button>
              <Button variant="ghost" size="icon">
                <X className="size-5" />
              </Button>
            </div>
          </ComponentPreview>

          <ComponentPreview
            title="Action icons"
            description="Search, notifications, settings"
            code={`<Button variant="ghost" size="icon">
  <Search className="size-5" />
</Button>
<Button variant="ghost" size="icon">
  <Bell className="size-5" />
</Button>
<Button variant="ghost" size="icon">
  <Settings className="size-5" />
</Button>`}
          >
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon">
                <Search className="size-5" />
              </Button>
              <Button variant="ghost" size="icon">
                <Bell className="size-5" />
              </Button>
              <Button variant="ghost" size="icon">
                <Settings className="size-5" />
              </Button>
            </div>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* States */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">States</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Disabled"
            description="Button in disabled state"
            code={`<Button disabled>Disabled</Button>`}
          >
            <Button disabled>Disabled</Button>
          </ComponentPreview>

          <ComponentPreview
            title="Loading"
            description="Button with loading spinner"
            code={`<Button disabled>
  <Loader2 className="size-4 animate-spin" />
  Please wait
</Button>`}
          >
            <Button disabled>
              <Loader2 className="size-4 animate-spin" />
              Please wait
            </Button>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Props Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Props</h2>
        <PropsTable props={buttonProps} />
      </div>
    </div>
  );
}
