/**
 * Medical disclaimer banner for the application.
 *
 * Displays a prominent warning that this is a demo system using
 * synthetic data and should not be used for actual medical decisions.
 */

import { AlertTriangle } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function MedicalDisclaimer() {
  return (
    <Alert
      variant="default"
      className="border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-950/20"
    >
      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
      <AlertTitle className="text-amber-800 dark:text-amber-200">
        For demonstration purposes only
      </AlertTitle>
      <AlertDescription className="text-amber-700 dark:text-amber-300">
        This system uses synthetic patient data and AI-generated insights. Do
        not use for actual medical decisions.
      </AlertDescription>
    </Alert>
  );
}
