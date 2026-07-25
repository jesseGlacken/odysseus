import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Button } from "../src/components/button";

describe("Button", () => {
  it("renders with default variant and size", () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole("button", { name: "Click me" });
    expect(btn).toBeInTheDocument();
  });

  it("fires onClick handler", async () => {
    const user = userEvent.setup();
    let clicked = false;
    render(<Button onClick={() => { clicked = true; }}>Fire</Button>);
    await user.click(screen.getByRole("button", { name: "Fire" }));
    expect(clicked).toBe(true);
  });

  it("applies destructive variant class", () => {
    render(<Button variant="destructive">Delete</Button>);
    const btn = screen.getByRole("button", { name: "Delete" });
    expect(btn.className).toContain("bg-[var(--destructive)]");
  });

  it("applies outline variant class", () => {
    render(<Button variant="outline">Outline</Button>);
    const btn = screen.getByRole("button", { name: "Outline" });
    expect(btn.className).toContain("border");
  });

  it("applies ghost variant class", () => {
    render(<Button variant="ghost">Ghost</Button>);
    const btn = screen.getByRole("button", { name: "Ghost" });
    expect(btn.className).toContain("hover:bg");
  });

  it("applies link variant class", () => {
    render(<Button variant="link">Link</Button>);
    const btn = screen.getByRole("button", { name: "Link" });
    expect(btn.className).toContain("underline-offset-4");
  });

  it("applies size sm classes", () => {
    render(<Button size="sm">Small</Button>);
    const btn = screen.getByRole("button", { name: "Small" });
    expect(btn.className).toContain("h-8");
  });

  it("applies size lg classes", () => {
    render(<Button size="lg">Large</Button>);
    const btn = screen.getByRole("button", { name: "Large" });
    expect(btn.className).toContain("h-12");
  });

  it("is disabled when disabled prop is set", () => {
    render(<Button disabled>Can't click</Button>);
    expect(screen.getByRole("button", { name: "Can't click" })).toBeDisabled();
  });

  it("accepts a custom className", () => {
    render(<Button className="custom-test">Custom</Button>);
    const btn = screen.getByRole("button", { name: "Custom" });
    expect(btn.className).toContain("custom-test");
  });

  it("passes accessibility audit (axe = 0 violations)", async () => {
    const { container } = render(<Button aria-label="Accessible button">A11y</Button>);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("forwards ref to the underlying button element", () => {
    let refEl: HTMLButtonElement | null = null;
    render(
      <Button ref={(el) => { refEl = el; }}>Ref test</Button>,
    );
    expect(refEl).toBeInstanceOf(HTMLButtonElement);
    expect(refEl?.textContent).toBe("Ref test");
  });
});
