import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Info, AlertCircle } from "lucide-react";
import Link from "next/link";

export default function AlertPage() {
  return (
    <div className="space-y-12">
      <div className="space-y-4">
        <h1 className="text-4xl font-medium tracking-tight">Alert</h1>
        <p className="text-lg text-muted-foreground max-w-2xl">
          Base alert component from shadcn/ui. For clinical contexts, use{" "}
          <Link href="/design/components/insight-card" className="text-primary hover:underline">
            InsightCard
          </Link>{" "}
          which provides severity-based styling.
        </p>
      </div>

      {/* Variants */}
      <div className="space-y-6">
        <h2 className="text-2xl font-medium">Variants</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <Alert>
            <Info className="size-4" />
            <AlertTitle>Default</AlertTitle>
            <AlertDescription>
              Standard informational message.
            </AlertDescription>
          </Alert>

          <Alert variant="destructive">
            <AlertCircle className="size-4" />
            <AlertTitle>Destructive</AlertTitle>
            <AlertDescription>
              Error or critical failure message.
            </AlertDescription>
          </Alert>
        </div>
      </div>

      {/* Usage */}
      <div className="space-y-4">
        <h2 className="text-2xl font-medium">Usage</h2>
        <div className="rounded-lg border bg-muted p-4">
          <pre className="text-sm font-mono overflow-x-auto">
            <code>{`import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"

<Alert>
  <AlertTitle>Default</AlertTitle>
  <AlertDescription>Message here.</AlertDescription>
</Alert>

<Alert variant="destructive">
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>Something went wrong.</AlertDescription>
</Alert>`}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
