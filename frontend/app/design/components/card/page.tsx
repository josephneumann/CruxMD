import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import { MoreHorizontal } from "lucide-react";

const cardComponents = [
  {
    name: "Card",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Container wrapper with shadow and border",
  },
  {
    name: "CardHeader",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Header section with grid layout for title/action",
  },
  {
    name: "CardTitle",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Title element with semibold text",
  },
  {
    name: "CardDescription",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Muted description text",
  },
  {
    name: "CardContent",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Main content area",
  },
  {
    name: "CardFooter",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Footer section for actions",
  },
  {
    name: "CardAction",
    type: "React.ComponentProps<'div'>",
    default: "—",
    description: "Action button slot in header",
  },
];

export default function CardPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Card</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Cards are containers that group related content and actions. They use
          a composable pattern with multiple sub-components for flexible layouts.
        </p>
      </div>

      {/* Basic Card */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Basic Card</h2>
        <ComponentPreview
          title="Simple card"
          description="Card with header and content"
          code={`<Card>
  <CardHeader>
    <CardTitle>Patient Summary</CardTitle>
    <CardDescription>Last updated 2 hours ago</CardDescription>
  </CardHeader>
  <CardContent>
    <p>Patient is a 45-year-old male with history of hypertension.</p>
  </CardContent>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Patient Summary</CardTitle>
              <CardDescription>Last updated 2 hours ago</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Patient is a 45-year-old male with history of hypertension.
              </p>
            </CardContent>
          </Card>
        </ComponentPreview>
      </div>

      {/* With Footer */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Footer</h2>
        <ComponentPreview
          title="Card with footer"
          description="Card with action buttons in the footer"
          code={`<Card>
  <CardHeader>
    <CardTitle>Lab Results</CardTitle>
    <CardDescription>Complete blood count</CardDescription>
  </CardHeader>
  <CardContent>
    <p>All values within normal range.</p>
  </CardContent>
  <CardFooter className="gap-2">
    <Button size="sm">View Details</Button>
    <Button size="sm" variant="outline">Download PDF</Button>
  </CardFooter>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Lab Results</CardTitle>
              <CardDescription>Complete blood count</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                All values within normal range.
              </p>
            </CardContent>
            <CardFooter className="gap-2">
              <Button size="sm">View Details</Button>
              <Button size="sm" variant="outline">Download PDF</Button>
            </CardFooter>
          </Card>
        </ComponentPreview>
      </div>

      {/* With Header Action */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">With Header Action</h2>
        <ComponentPreview
          title="Card with action button"
          description="Using CardAction for a menu button"
          code={`<Card>
  <CardHeader>
    <CardTitle>Recent Visits</CardTitle>
    <CardDescription>3 visits in the last month</CardDescription>
    <CardAction>
      <Button variant="ghost" size="icon-sm">
        <MoreHorizontal className="size-4" />
      </Button>
    </CardAction>
  </CardHeader>
  <CardContent>
    <p>View the patient's recent visit history.</p>
  </CardContent>
</Card>`}
        >
          <Card className="w-80">
            <CardHeader>
              <CardTitle>Recent Visits</CardTitle>
              <CardDescription>3 visits in the last month</CardDescription>
              <CardAction>
                <Button variant="ghost" size="icon-sm">
                  <MoreHorizontal className="size-4" />
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                View the patient&apos;s recent visit history.
              </p>
            </CardContent>
          </Card>
        </ComponentPreview>
      </div>

      {/* Card Grid */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Card Grid</h2>
        <PreviewGrid cols={3}>
          <Card>
            <CardHeader>
              <CardTitle>Medications</CardTitle>
              <CardDescription>Active prescriptions</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">12</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Allergies</CardTitle>
              <CardDescription>Known allergies</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">3</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Conditions</CardTitle>
              <CardDescription>Active diagnoses</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">5</p>
            </CardContent>
          </Card>
        </PreviewGrid>
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={cardComponents} />
      </div>
    </div>
  );
}
