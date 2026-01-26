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
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { ComponentPreview, PreviewGrid } from "@/components/design-system/ComponentPreview";
import { PropsTable } from "@/components/design-system/PropsTable";
import {
  MoreHorizontal,
  Heart,
  Activity,
  Thermometer,
  Wind,
  Droplets,
  TrendingUp,
  Minus,
  AlertCircle,
} from "lucide-react";

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

      {/* Vital Signs */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Vital Signs Cards</h2>
        <p className="text-muted-foreground">
          Compact cards for displaying individual vital sign measurements with status indicators.
        </p>
        <div className="flex flex-wrap gap-4">
          {/* Heart Rate */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Heart className="size-5 text-primary" strokeWidth={1.5} />
              <Minus className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">72</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">bpm</p>
            <p className="text-sm font-medium mb-4">Heart Rate</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>

          {/* Blood Pressure */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Activity className="size-5 text-primary" strokeWidth={1.5} />
              <TrendingUp className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">120/80</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">mmHg</p>
            <p className="text-sm font-medium mb-4">Blood Pressure</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>

          {/* Temperature */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Thermometer className="size-5 text-[#8B8FC7]" strokeWidth={1.5} />
              <Minus className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">98.6</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">°F</p>
            <p className="text-sm font-medium mb-4">Temperature</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>

          {/* Respiratory Rate */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Wind className="size-5 text-primary" strokeWidth={1.5} />
              <Minus className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">16</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">bpm</p>
            <p className="text-sm font-medium mb-4">Respiratory Rate</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>

          {/* O2 Saturation */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Droplets className="size-5 text-[#8B8FC7]" strokeWidth={1.5} />
              <Minus className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">98</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">%</p>
            <p className="text-sm font-medium mb-4">O₂ Saturation</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>

          {/* Blood Glucose */}
          <Card className="w-[160px] p-5">
            <div className="flex items-center justify-between mb-4">
              <Activity className="size-5 text-primary" strokeWidth={1.5} />
              <Minus className="size-4 text-muted-foreground/50" />
            </div>
            <div className="mb-1">
              <span className="text-4xl font-semibold tracking-tight">95</span>
            </div>
            <p className="text-sm text-muted-foreground mb-1">mg/dL</p>
            <p className="text-sm font-medium mb-4">Blood Glucose</p>
            <Badge variant="sage" size="sm">Normal</Badge>
            <p className="text-xs text-muted-foreground mt-3">10:30 AM</p>
          </Card>
        </div>
      </div>

      {/* Patient Summary Card */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Patient Summary Card</h2>
        <p className="text-muted-foreground">
          A comprehensive card for displaying patient information at a glance.
        </p>
        <div className="max-w-md">
          <Card className="p-5">
            <div className="flex items-start gap-4">
              <Avatar className="size-12 bg-primary/20">
                <AvatarFallback className="bg-primary/20 text-primary font-medium">
                  J
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold">Johnson, Emily</h3>
                    <p className="text-sm text-muted-foreground">Dr. Williams</p>
                  </div>
                  <Badge variant="sage" size="sm">Low Risk</Badge>
                </div>
                <div className="mt-2 space-y-0.5 text-sm text-muted-foreground">
                  <p>MRN: MRN-789012</p>
                  <p>49y, Female • DOB: 06/22/1975</p>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t space-y-3">
              <div className="flex items-start gap-2">
                <AlertCircle className="size-4 text-destructive mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Allergies</p>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    <Badge variant="outline" size="sm">Penicillin</Badge>
                    <Badge variant="outline" size="sm">Latex</Badge>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-sm">
                  <span className="font-medium">Conditions:</span>{" "}
                  <span className="text-muted-foreground">
                    Hypertension, Type 2 Diabetes
                  </span>
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      {/* Sub-components */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Sub-components</h2>
        <PropsTable props={cardComponents} />
      </div>
    </div>
  );
}
