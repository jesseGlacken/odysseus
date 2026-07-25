import { type ReactNode } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../lib/utils";

/**
 * Root tabs container.
 *
 * Built on @radix-ui/react-tabs for keyboard navigation (arrow keys,
 * Home/End) and ARIA tabpanel pattern. WCAG 2.2 AA compliant.
 */
export function Tabs({
  className,
  ...props
}: TabsPrimitive.TabsProps): ReactNode {
  return (
    <TabsPrimitive.Root
      className={cn("flex flex-col", className)}
      {...props}
    />
  );
}

export function TabsList({
  className,
  ...props
}: TabsPrimitive.TabsListProps): ReactNode {
  return (
    <TabsPrimitive.List
      className={cn(
        "inline-flex h-10 items-center justify-center gap-1 rounded-[var(--radius)] bg-[var(--muted)] p-1 text-[var(--muted-foreground)]",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: TabsPrimitive.TabsTriggerProps): ReactNode {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium",
        "ring-offset-[var(--background)] transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        "data-[state=active]:bg-[var(--background)] data-[state=active]:text-[var(--foreground)] data-[state=active]:shadow-sm",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: TabsPrimitive.TabsContentProps): ReactNode {
  return (
    <TabsPrimitive.Content
      className={cn(
        "mt-2",
        "ring-offset-[var(--background)]",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2",
        className,
      )}
      {...props}
    />
  );
}
