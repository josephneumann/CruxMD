import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { Info, AlertCircle, Terminal } from "lucide-react";

const alertProps = [
  {
    name: "variant",
    type: '"default" | "destructive"',
    default: '"default"',
    description: "The visual style of the alert",
  },
];

const subComponents = [
  {
    name: "Alert",
    type: 'React.ComponentProps<"div"> & VariantProps',
    default: "—",
    description: "Container with icon support and grid layout",
  },
  {
    name: "AlertTitle",
    type: 'React.ComponentProps<"div">',
    default: "—",
    description: "Title element with medium weight",
  },
  {
    name: "AlertDescription",
    type: 'React.ComponentProps<"div">',
    default: "—",
    description: "Description text with muted color",
  },
];

export default function AlertPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Alert</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Alerts display important messages to users. They support icons and
          come in default and destructive variants. Used as the base component
          for InsightCard.
        </p>
      </div>

      {/* Variants */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Variants</h2>
        <PreviewGrid cols={2}>
          <ComponentPreview
            title="Default"
            description="Standard informational alert"
            code={`<Alert>
  <Info className="size-4" />
  <AlertTitle>Information</AlertTitle>
  <AlertDescription>
    This is a general information message.
  </AlertDescription>
</Alert>`}
          >
            <Alert className="w-full">
              <Info className="size-4" />
              <AlertTitle>Information</AlertTitle>
              <AlertDescription>
                This is a general information message.
              </AlertDescription>
            </Alert>
          </ComponentPreview>

          <ComponentPreview
            title="Destructive"
            description="Error or warning alert"
            code={`<Alert variant="destructive">
  <AlertCircle className="size-4" />
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>
    Something went wrong. Please try again.
  </AlertDescription>
</Alert>`}
          >
            <Alert variant="destructive" className="w-full">
              <AlertCircle className="size-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>
                Something went wrong. Please try again.
              </AlertDescription>
            </Alert>
          </ComponentPreview>
        </PreviewGrid>
      </div>

      {/* Without Icon */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Without Icon</h2>
        <ComponentPreview
          title="Text only"
          description="Alert without an icon"
          code={`<Alert>
  <AlertTitle>Heads up!</AlertTitle>
  <AlertDescription>
    You can use alerts without icons for simpler messages.
  </AlertDescription>
</Alert>`}
        >
          <Alert className="w-full max-w-md">
            <AlertTitle>Heads up!</AlertTitle>
            <AlertDescription>
              You can use alerts without icons for simpler messages.
            </AlertDescription>
          </Alert>
        </ComponentPreview>
      </div>

      {/* With Custom Icon */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Custom Icon</h2>
        <ComponentPreview
          title="Terminal alert"
          description="Using a different icon"
          code={`<Alert>
  <Terminal className="size-4" />
  <AlertTitle>Terminal Output</AlertTitle>
  <AlertDescription>
    npm install completed successfully.
  </AlertDescription>
</Alert>`}
        >
          <Alert className="w-full max-w-md">
            <Terminal className="size-4" />
            <AlertTitle>Terminal Output</AlertTitle>
            <AlertDescription>
              npm install completed successfully.
            </AlertDescription>
          </Alert>
        </ComponentPreview>
      </div>

      {/* Props Table */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Props</h2>
        <PropsTable props={alertProps} />
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={subComponents} />
      </div>
    </div>
  );
}
