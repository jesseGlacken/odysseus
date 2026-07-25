import { type ReactNode, useState } from "react";
import {
  ComboBox as AriaComboBox,
  Input as AriaInput,
  Button,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  type ComboBoxProps as AriaComboBoxProps,
} from "react-aria-components";
import { cn } from "../lib/utils";

export interface ComboBoxItem {
  id: string;
  label: string;
}

export interface ComboBoxProps<T extends ComboBoxItem>
  extends Omit<AriaComboBoxProps<T>, "children"> {
  /** Visible label text for the combobox. */
  label: string;
  /** Items to filter and display. */
  items: T[];
  /** Placeholder text for the input. */
  placeholder?: string;
}

/**
 * Accessible combobox (autocomplete) built on React Aria's ComboBox.
 *
 * Supports filtering via input, keyboard navigation, and full ARIA
 * attributes managed by React Aria hooks. WCAG 2.2 AA compliant out
 * of the box.
 */
export function ComboBox<T extends ComboBoxItem>({
  label,
  items,
  placeholder = "Type to search...",
  className,
  ...props
}: ComboBoxProps<T>): ReactNode {
  const [filterText, setFilterText] = useState("");

  const filteredItems = filterText
    ? items.filter((item) =>
        item.label.toLowerCase().includes(filterText.toLowerCase()),
      )
    : items;

  return (
    <AriaComboBox
      {...props}
      inputValue={filterText}
      onInputChange={setFilterText}
      className={cn("grid gap-1.5", className)}
      aria-label={undefined}
    >
      <Label className="text-sm font-medium leading-none">{label}</Label>
      <div className="relative">
        <AriaInput
          placeholder={placeholder}
          className={cn(
            "flex h-10 w-full rounded-[var(--radius)] border border-[var(--border)]",
            "bg-[var(--background)] px-3 py-2 text-sm",
            "placeholder:text-[var(--muted-foreground)]",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]",
            "disabled:cursor-not-allowed disabled:opacity-50",
          )}
        />
        <Button
          className={cn(
            "absolute right-2 top-1/2 -translate-y-1/2 rounded-sm p-1",
            "opacity-50 hover:opacity-100",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)]",
          )}
        >
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
          >
            <path d="m6 9 6 6 6-6" />
          </svg>
        </Button>
      </div>
      <Popover
        className={cn(
          "z-50 w-[--trigger-width] overflow-auto rounded-[var(--radius)] border border-[var(--border)]",
          "bg-[var(--popover)] p-1 shadow-md",
          "data-[entering]:animate-in data-[entering]:fade-in-0 data-[entering]:zoom-in-95",
          "data-[exiting]:animate-out data-[exiting]:fade-out-0 data-[exiting]:zoom-out-95",
        )}
      >
        <ListBox
          items={filteredItems}
          className="max-h-60 overflow-auto outline-none"
          renderEmptyState={() => (
            <div className="px-2 py-3 text-sm text-[var(--muted-foreground)]">
              No results found.
            </div>
          )}
        >
          {(item: T) => (
            <ListBoxItem
              id={item.id}
              textValue={item.label}
              className={cn(
                "relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none",
                "text-[var(--popover-foreground)]",
                "data-[focused]:bg-[var(--accent)] data-[focused]:text-[var(--accent-foreground)]",
                "data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
              )}
            >
              {item.label}
            </ListBoxItem>
          )}
        </ListBox>
      </Popover>
    </AriaComboBox>
  );
}
