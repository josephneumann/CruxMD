"use client";

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
