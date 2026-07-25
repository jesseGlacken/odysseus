import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "../lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /**
   * Visible label text rendered in a <label> element bound to the input.
   * Must be provided so the input is accessible.
   */
  label: string;
  /** Error message rendered below the input. Also sets aria-invalid + aria-errormessage. */
  error?: string;
}

/**
 * Accessible text input with label.
 *
 * Always renders a bound `<label>` so screen readers can identify the field.
 * Error state sets `aria-invalid="true"` and associates the error message
 * via `aria-describedby`.
 */
export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, id: externalId, className, ...props }, ref) => {
    const generatedId = useId();
    const id = externalId ?? generatedId;
    const errorId = `${id}-error`;

    return (
      <div className="grid gap-1.5">
        <label
          htmlFor={id}
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          {label}
        </label>
        <input
          ref={ref}
          id={id}
          aria-invalid={error ? "true" : undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn(
            "flex h-10 w-full rounded-[var(--radius)] border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm",
            "file:border-0 file:bg-transparent file:text-sm file:font-medium",
            "placeholder:text-[var(--muted-foreground)]",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--ring)] focus-visible:ring-1 focus-visible:ring-[var(--ring)]",
            "disabled:cursor-not-allowed disabled:opacity-50",
            error && "border-[var(--destructive)] focus-visible:outline-[var(--destructive)] focus-visible:ring-[var(--destructive)]",
            className,
          )}
          {...props}
        />
        {error && (
          <p id={errorId} className="text-sm text-[var(--destructive)]" role="alert">
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
