"use client";

import Image from "next/image";
import {
  Avatar,
  AvatarImage,
  AvatarFallback,
  AvatarBadge,
  AvatarGroup,
  AvatarGroupCount,
} from "@/components/ui/avatar";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { CodeBlock } from "@/components/design-system/CodeBlock";
import { Check, Plus } from "lucide-react";

const avatarProps = [
  {
    name: "size",
    type: '"sm" | "default" | "lg"',
    default: '"default"',
    description: "The size of the avatar",
  },
];

const subComponents = [
  {
    name: "Avatar",
    type: "AvatarPrimitive.Root & { size }",
    default: "—",
    description: "Container for avatar with size variants",
  },
  {
    name: "AvatarImage",
    type: "AvatarPrimitive.Image",
    default: "—",
    description: "The user's profile image",
  },
  {
    name: "AvatarFallback",
    type: "AvatarPrimitive.Fallback",
    default: "—",
    description: "Fallback content when image fails to load",
  },
  {
    name: "AvatarBadge",
    type: 'React.ComponentProps<"span">',
    default: "—",
    description: "Status badge positioned at bottom-right",
  },
  {
    name: "AvatarGroup",
    type: 'React.ComponentProps<"div">',
    default: "—",
    description: "Container for stacked avatars",
  },
  {
    name: "AvatarGroupCount",
    type: 'React.ComponentProps<"div">',
    default: "—",
    description: "Overflow count indicator",
  },
];

export default function AvatarPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Avatar</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Avatars represent users with images or initials. They support multiple
          sizes, fallback states, badges, and can be grouped for team displays.
        </p>
      </div>

      {/* Watercolor Portraits */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Watercolor Portraits</h2>
        <p className="text-muted-foreground">
          CruxMD uses AI-generated watercolor portraits for doctor and patient avatars.
          These are created with <strong>Nano Banana Pro</strong> using a consistent prompt
          that produces soft, bleeding ink washes in our brand palette. The style avoids
          photorealism in favor of an artistic, approachable aesthetic.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="flex flex-col items-center">
            <div className="h-40 w-40 rounded-full overflow-hidden mb-4">
              <Image
                src="/brand/portraits/doctor-wilcox.png"
                alt="Dr. Brian Wilcox"
                width={300}
                height={300}
                className="h-full w-full object-cover"
              />
            </div>
            <p className="text-sm font-medium">Dr. Brian Wilcox, MD</p>
            <p className="text-xs text-muted-foreground">Internal Medicine</p>
          </div>
          <div className="flex flex-col items-center">
            <div className="h-40 w-40 rounded-full overflow-hidden mb-4">
              <Image
                src="/brand/portraits/doctor-patel.png"
                alt="Dr. Priya Patel"
                width={300}
                height={300}
                className="h-full w-full object-cover"
              />
            </div>
            <p className="text-sm font-medium">Dr. Priya Patel, MD</p>
            <p className="text-xs text-muted-foreground">Family Medicine</p>
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-lg font-medium">Generation Prompt</h3>
          <p className="text-sm text-muted-foreground">
            Use the following prompt with Nano Banana Pro, substituting the description
            for each person:
          </p>
          <CodeBlock className="[&_pre]:whitespace-pre-wrap [&_pre]:overflow-x-hidden" code={`Generate minimalist, wet-ink watercolor portrait of <description of person or reference image>. The person is in a smiling, front-facing "observer" pose, facing straight ahead, centered in the image. The form is defined by soft, bleeding washes of color rather than hard lines. The primary colors are "Vibrant Forest" (#2F5E52) and "Glacier Teal" (#5A7D7C), forming the silhouette of the head, brown hair, and shoulders. The edges of the watercolor are organic and feathery, bleeding into a textured, off-white "Alabaster" (#F0EAD6) paper background. No sharp details, just flowing color and texture.`} />
        </div>

        <div className="space-y-3">
          <h3 className="text-lg font-medium">Guidelines</h3>
          <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
            <li>Always use the brand colors Vibrant Forest and Glacier Teal as the primary palette</li>
            <li>Portraits should be front-facing and centered for consistent circular cropping</li>
            <li>File naming convention: lowercase, hyphenated name (e.g. <code className="text-xs bg-muted px-1.5 py-0.5 rounded">miguel-bashirian.png</code>)</li>
            <li>Strip diacritics from filenames (e.g. Andrés → andres) for URL compatibility</li>
            <li>Place files in <code className="text-xs bg-muted px-1.5 py-0.5 rounded">public/brand/avatars/</code></li>
            <li>The Avatar component falls back to initials if the image file is missing</li>
          </ul>
        </div>
      </div>

      {/* Basic Usage */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Usage</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="With image"
            description="Avatar displaying a user photo"
            code={`<Avatar>
  <AvatarImage src="/user.jpg" alt="Dr. Smith" />
  <AvatarFallback>DS</AvatarFallback>
</Avatar>`}
          >
            <Avatar>
              <AvatarImage src="https://github.com/shadcn.png" alt="User" />
              <AvatarFallback>DS</AvatarFallback>
            </Avatar>
          </ComponentPreview>

          <ComponentPreview
            title="With fallback"
            description="Avatar showing initials when no image"
            code={`<Avatar>
  <AvatarFallback>JN</AvatarFallback>
</Avatar>`}
          >
            <Avatar>
              <AvatarFallback>JN</AvatarFallback>
            </Avatar>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Sizes */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sizes</h2>
        <ComponentPreview
          title="Size comparison"
          description="Available avatar sizes"
          code={`<Avatar size="sm">
  <AvatarFallback>SM</AvatarFallback>
</Avatar>
<Avatar size="default">
  <AvatarFallback>MD</AvatarFallback>
</Avatar>
<Avatar size="lg">
  <AvatarFallback>LG</AvatarFallback>
</Avatar>`}
        >
          <div className="flex items-center gap-4">
            <div className="flex flex-col items-center gap-2">
              <Avatar size="sm">
                <AvatarFallback>SM</AvatarFallback>
              </Avatar>
              <span className="text-xs text-muted-foreground">sm (24px)</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Avatar size="default">
                <AvatarFallback>MD</AvatarFallback>
              </Avatar>
              <span className="text-xs text-muted-foreground">default (32px)</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Avatar size="lg">
                <AvatarFallback>LG</AvatarFallback>
              </Avatar>
              <span className="text-xs text-muted-foreground">lg (40px)</span>
            </div>
          </div>
        </ComponentPreview>
      </div>

      {/* With Badge */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Badge</h2>
        <PreviewGrid cols={3}>
          <ComponentPreview
            title="Online status"
            description="Badge indicating user status"
            code={`<Avatar>
  <AvatarFallback>JN</AvatarFallback>
  <AvatarBadge className="bg-green-500" />
</Avatar>`}
          >
            <Avatar>
              <AvatarFallback>JN</AvatarFallback>
              <AvatarBadge className="bg-green-500" />
            </Avatar>
          </ComponentPreview>

          <ComponentPreview
            title="With icon"
            description="Badge with checkmark icon"
            code={`<Avatar size="lg">
  <AvatarFallback>AB</AvatarFallback>
  <AvatarBadge>
    <Check />
  </AvatarBadge>
</Avatar>`}
          >
            <Avatar size="lg">
              <AvatarFallback>AB</AvatarFallback>
              <AvatarBadge>
                <Check />
              </AvatarBadge>
            </Avatar>
          </ComponentPreview>

          <ComponentPreview
            title="Notification"
            description="Badge for notifications"
            code={`<Avatar>
  <AvatarFallback>CD</AvatarFallback>
  <AvatarBadge className="bg-destructive" />
</Avatar>`}
          >
            <Avatar>
              <AvatarFallback>CD</AvatarFallback>
              <AvatarBadge className="bg-destructive" />
            </Avatar>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Avatar Group */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Avatar Group</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Basic group"
            description="Stacked avatars for teams"
            code={`<AvatarGroup>
  <Avatar>
    <AvatarFallback>JN</AvatarFallback>
  </Avatar>
  <Avatar>
    <AvatarFallback>AB</AvatarFallback>
  </Avatar>
  <Avatar>
    <AvatarFallback>CD</AvatarFallback>
  </Avatar>
</AvatarGroup>`}
          >
            <AvatarGroup>
              <Avatar>
                <AvatarFallback>JN</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>AB</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>CD</AvatarFallback>
              </Avatar>
            </AvatarGroup>
          </ComponentPreview>

          <ComponentPreview
            title="With overflow count"
            description="Showing additional members"
            code={`<AvatarGroup>
  <Avatar>
    <AvatarFallback>JN</AvatarFallback>
  </Avatar>
  <Avatar>
    <AvatarFallback>AB</AvatarFallback>
  </Avatar>
  <AvatarGroupCount>+5</AvatarGroupCount>
</AvatarGroup>`}
          >
            <AvatarGroup>
              <Avatar>
                <AvatarFallback>JN</AvatarFallback>
              </Avatar>
              <Avatar>
                <AvatarFallback>AB</AvatarFallback>
              </Avatar>
              <AvatarGroupCount>+5</AvatarGroupCount>
            </AvatarGroup>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Different sizes in group */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sized Groups</h2>
        <ComponentPreview
          title="Large avatar group"
          description="Avatar group with large size"
          code={`<AvatarGroup>
  <Avatar size="lg">
    <AvatarFallback>JN</AvatarFallback>
  </Avatar>
  <Avatar size="lg">
    <AvatarFallback>AB</AvatarFallback>
  </Avatar>
  <Avatar size="lg">
    <AvatarFallback>CD</AvatarFallback>
  </Avatar>
  <AvatarGroupCount>
    <Plus />
  </AvatarGroupCount>
</AvatarGroup>`}
        >
          <AvatarGroup>
            <Avatar size="lg">
              <AvatarFallback>JN</AvatarFallback>
            </Avatar>
            <Avatar size="lg">
              <AvatarFallback>AB</AvatarFallback>
            </Avatar>
            <Avatar size="lg">
              <AvatarFallback>CD</AvatarFallback>
            </Avatar>
            <AvatarGroupCount>
              <Plus className="size-5" />
            </AvatarGroupCount>
          </AvatarGroup>
        </ComponentPreview>
      </div>

      {/* Props Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Props</h2>
        <PropsTable props={avatarProps} />
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={subComponents} />
      </div>
    </div>
  );
}
