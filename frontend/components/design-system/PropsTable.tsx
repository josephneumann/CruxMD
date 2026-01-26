import { cn } from "@/lib/utils";

interface PropDefinition {
  name: string;
  type: string;
  default?: string;
  description: string;
  required?: boolean;
}

interface PropsTableProps {
  props: PropDefinition[];
  className?: string;
}

export function PropsTable({ props, className }: PropsTableProps) {
  return (
    <div className={cn("rounded-lg border overflow-hidden", className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            <th className="text-left font-medium px-4 py-3">Prop</th>
            <th className="text-left font-medium px-4 py-3">Type</th>
            <th className="text-left font-medium px-4 py-3">Default</th>
            <th className="text-left font-medium px-4 py-3">Description</th>
          </tr>
        </thead>
        <tbody>
          {props.map((prop, index) => (
            <tr
              key={prop.name}
              className={cn(index !== props.length - 1 && "border-b")}
            >
              <td className="px-4 py-3">
                <code className="text-sm font-mono text-primary">
                  {prop.name}
                  {prop.required && <span className="text-destructive">*</span>}
                </code>
              </td>
              <td className="px-4 py-3">
                <code className="text-xs font-mono text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                  {prop.type}
                </code>
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {prop.default ? (
                  <code className="text-xs font-mono">{prop.default}</code>
                ) : (
                  "—"
                )}
              </td>
              <td className="px-4 py-3 text-muted-foreground">
                {prop.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
