import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Compose Tailwind classes, merging conflicts with tailwind-merge.
 * Uses clsx for conditional/falsy handling and twMerge for
 * conflict resolution (e.g. duplicate padding, colours).
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
