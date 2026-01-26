"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button variant="outline" size="sm" disabled>
        <Sun className="size-4" />
      </Button>
    );
  }

  return (
    <Select value={theme} onValueChange={setTheme}>
      <SelectTrigger size="sm" className="w-[130px]">
        <SelectValue>
          {theme === "system" && <Monitor className="size-4" />}
          {theme === "light" && <Sun className="size-4" />}
          {theme === "dark" && <Moon className="size-4" />}
          <span className="capitalize ml-2">{theme}</span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="system">
          <Monitor className="size-4" />
          <span>System</span>
        </SelectItem>
        <SelectItem value="light">
          <Sun className="size-4" />
          <span>Light</span>
        </SelectItem>
        <SelectItem value="dark">
          <Moon className="size-4" />
          <span>Dark</span>
        </SelectItem>
      </SelectContent>
    </Select>
  );
}
