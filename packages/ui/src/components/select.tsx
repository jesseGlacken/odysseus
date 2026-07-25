import { type ReactNode } from "react";
import {
  Select as AriaSelect,
  SelectValue as AriaSelectValue,
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  type SelectProps as AriaSelectProps,
  type ListBoxItemProps,
} from "react-aria-components";
import { cn } from "../lib/utils";

export interface SelectItem {
  id: string;
  label: string;
}

export interface SelectProps<T extends SelectItem>
  extends Omit<AriaSelectProps<T>, "children"> {
  /** Visible label text for the select. */
  label: string;
  /** Items to display in the dropdown. */
  items: T[];
  /** Placeholder shown when no value is selected. */
  placeholder?: string;
  /** Error message displayed below the control. */
  error?: string;
}

/**
 * Accessible select (dropdown) built on React Aria's Select.
 *
 * Supports label, options, placeholder, disabled state, and error state.
 * All ARIA attributes are managed by React Aria hooks.
 */
export function Select<T extends SelectItem>({
  label,
  items,
  placeholder = "Select an option",
  error,
  className,
  ...props
}: SelectProps<T>): ReactNode {
  return (
    <AriaSelect
      {...props}
      className={cn("grid gap-1.5", className)}
      aria-label={undefined}
    >
      <Label className="text-sm font-medium leading-none">{label}</Label>
      <Button
        className={cn(
          "flex h-10 w-full items-center justify-between rounded-[var(--radius)] border border-[var(--border)]",
          "bg-[var(--background)] px-3 py-2 text-sm",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-[var(--destructive)]",
        )}
      >
        <AriaSelectValue className="data-[placeholder]:text-[var(--muted-foreground)]">
          {({ defaultChildren, isPlaceholder }) =>
            isPlaceholder ? <>{placeholder}</> : defaultChildren
          }
        </AriaSelectValue>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="ml-2 shrink-0 opacity-50"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </Button>
      {error && (
        <p className="text-sm text-[var(--destructive)]" role="alert">
          {error}
        </p>
      )}
      <Popover
        className={cn(
          "z-50 w-[--trigger-width] overflow-auto rounded-[var(--radius)] border border-[var(--border)]",
          "bg-[var(--popover)] p-1 shadow-md",
          "data-[entering]:animate-in data-[entering]:fade-in-0 data-[entering]:zoom-in-95",
          "data-[exiting]:animate-out data-[exiting]:fade-out-0 data-[exiting]:zoom-out-95",
        )}
      >
        <ListBox
          items={items}
          className="outline-none"
        >
          {(item: T) => (
            <SelectOption id={item.id}>{item.label}</SelectOption>
          )}
        </ListBox>
      </Popover>
    </AriaSelect>
  );
}

interface SelectOptionProps extends Omit<ListBoxItemProps, "children"> {
  children: ReactNode;
}

function SelectOption({ children, ...props }: SelectOptionProps): ReactNode {
  return (
    <ListBoxItem
      {...props}
      className={cn(
        "relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none",
        "text-[var(--popover-foreground)]",
        "data-[focused]:bg-[var(--accent)] data-[focused]:text-[var(--accent-foreground)]",
        "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
      )}
    >
      {children}
    </ListBoxItem>
  );
}
