"use client";

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { Brain, Zap, Sparkles } from "lucide-react";

const selectTriggerProps = [
  {
    name: "size",
    type: '"sm" | "default"',
    default: '"default"',
    description: "The size of the trigger button",
  },
  {
    name: "placeholder",
    type: "string",
    default: "—",
    description: "Placeholder text when no value is selected",
  },
];

const subComponents = [
  {
    name: "Select",
    type: "SelectPrimitive.Root",
    default: "—",
    description: "Root component managing state",
  },
  {
    name: "SelectTrigger",
    type: "SelectPrimitive.Trigger & { size }",
    default: "—",
    description: "The button that toggles the dropdown",
  },
  {
    name: "SelectValue",
    type: "SelectPrimitive.Value",
    default: "—",
    description: "Displays the selected value",
  },
  {
    name: "SelectContent",
    type: "SelectPrimitive.Content",
    default: "—",
    description: "The dropdown container",
  },
  {
    name: "SelectItem",
    type: "SelectPrimitive.Item",
    default: "—",
    description: "Individual selectable option",
  },
  {
    name: "SelectGroup",
    type: "SelectPrimitive.Group",
    default: "—",
    description: "Group of related items",
  },
  {
    name: "SelectLabel",
    type: "SelectPrimitive.Label",
    default: "—",
    description: "Label for a group",
  },
  {
    name: "SelectSeparator",
    type: "SelectPrimitive.Separator",
    default: "—",
    description: "Visual divider between items",
  },
];

export default function SelectPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Select</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Select components allow users to choose from a list of options. Built
          on Radix UI primitives for full accessibility support.
        </p>
      </div>

      {/* Basic Usage */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Usage</h2>
        <ComponentPreview
          title="Simple select"
          description="Basic dropdown selection"
          code={`<Select>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Select a fruit" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="apple">Apple</SelectItem>
    <SelectItem value="banana">Banana</SelectItem>
    <SelectItem value="orange">Orange</SelectItem>
  </SelectContent>
</Select>`}
        >
          <Select>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select a fruit" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="apple">Apple</SelectItem>
              <SelectItem value="banana">Banana</SelectItem>
              <SelectItem value="orange">Orange</SelectItem>
            </SelectContent>
          </Select>
        </ComponentPreview>
      </div>

      {/* Sizes */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sizes</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Default size"
            description="Standard trigger height (36px)"
            code={`<Select>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Default size" />
  </SelectTrigger>
  ...
</Select>`}
          >
            <Select>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Default size" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="option1">Option 1</SelectItem>
                <SelectItem value="option2">Option 2</SelectItem>
              </SelectContent>
            </Select>
          </ComponentPreview>

          <ComponentPreview
            title="Small size"
            description="Compact trigger height (32px)"
            code={`<Select>
  <SelectTrigger size="sm" className="w-[180px]">
    <SelectValue placeholder="Small size" />
  </SelectTrigger>
  ...
</Select>`}
          >
            <Select>
              <SelectTrigger size="sm" className="w-[180px]">
                <SelectValue placeholder="Small size" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="option1">Option 1</SelectItem>
                <SelectItem value="option2">Option 2</SelectItem>
              </SelectContent>
            </Select>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* With Groups */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Groups</h2>
        <ComponentPreview
          title="Grouped options"
          description="Organize options into labeled groups"
          code={`<Select>
  <SelectTrigger className="w-[200px]">
    <SelectValue placeholder="Select model" />
  </SelectTrigger>
  <SelectContent>
    <SelectGroup>
      <SelectLabel>Claude Models</SelectLabel>
      <SelectItem value="opus">Claude Opus</SelectItem>
      <SelectItem value="sonnet">Claude Sonnet</SelectItem>
      <SelectItem value="haiku">Claude Haiku</SelectItem>
    </SelectGroup>
    <SelectSeparator />
    <SelectGroup>
      <SelectLabel>OpenAI Models</SelectLabel>
      <SelectItem value="gpt4">GPT-4</SelectItem>
      <SelectItem value="gpt35">GPT-3.5</SelectItem>
    </SelectGroup>
  </SelectContent>
</Select>`}
        >
          <Select>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select model" />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Claude Models</SelectLabel>
                <SelectItem value="opus">Claude Opus</SelectItem>
                <SelectItem value="sonnet">Claude Sonnet</SelectItem>
                <SelectItem value="haiku">Claude Haiku</SelectItem>
              </SelectGroup>
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel>OpenAI Models</SelectLabel>
                <SelectItem value="gpt4">GPT-4</SelectItem>
                <SelectItem value="gpt35">GPT-3.5</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </ComponentPreview>
      </div>

      {/* With Icons */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Icons</h2>
        <ComponentPreview
          title="Items with icons"
          description="Visual indicators for each option"
          code={`<Select defaultValue="sonnet">
  <SelectTrigger className="w-[200px]">
    <SelectValue />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="opus">
      <Brain className="size-4" />
      <span>Claude Opus</span>
    </SelectItem>
    <SelectItem value="sonnet">
      <Sparkles className="size-4" />
      <span>Claude Sonnet</span>
    </SelectItem>
    <SelectItem value="haiku">
      <Zap className="size-4" />
      <span>Claude Haiku</span>
    </SelectItem>
  </SelectContent>
</Select>`}
        >
          <Select defaultValue="sonnet">
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="opus">
                <Brain className="size-4" />
                <span>Claude Opus</span>
              </SelectItem>
              <SelectItem value="sonnet">
                <Sparkles className="size-4" />
                <span>Claude Sonnet</span>
              </SelectItem>
              <SelectItem value="haiku">
                <Zap className="size-4" />
                <span>Claude Haiku</span>
              </SelectItem>
            </SelectContent>
          </Select>
        </ComponentPreview>
      </div>

      {/* Disabled State */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">States</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Disabled"
            description="Non-interactive select"
            code={`<Select disabled>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Disabled" />
  </SelectTrigger>
  ...
</Select>`}
          >
            <Select disabled>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Disabled" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="option">Option</SelectItem>
              </SelectContent>
            </Select>
          </ComponentPreview>

          <ComponentPreview
            title="With disabled item"
            description="Individual option disabled"
            code={`<Select>
  <SelectTrigger className="w-[180px]">
    <SelectValue placeholder="Select..." />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="active">Active</SelectItem>
    <SelectItem value="disabled" disabled>
      Disabled
    </SelectItem>
  </SelectContent>
</Select>`}
          >
            <Select>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Select..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">Active Option</SelectItem>
                <SelectItem value="disabled" disabled>
                  Disabled Option
                </SelectItem>
              </SelectContent>
            </Select>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Props Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">SelectTrigger Props</h2>
        <PropsTable props={selectTriggerProps} />
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={subComponents} />
      </div>
    </div>
  );
}
