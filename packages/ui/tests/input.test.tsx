import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Input } from "../src/components/input";

describe("Input", () => {
  it("renders with a label bound to the input", () => {
    render(<Input label="Email" />);
    const input = screen.getByLabelText("Email");
    expect(input).toBeInTheDocument();
  });

  it("accepts typed text", async () => {
    const user = userEvent.setup();
    render(<Input label="Name" />);
    const input = screen.getByLabelText("Name");
    await user.type(input, "Alice");
    expect(input).toHaveValue("Alice");
  });

  it("shows error message and sets aria-invalid", () => {
    render(<Input label="Email" error="Email is required" />);
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Email is required");
  });

  it("associates error via aria-describedby", () => {
    render(<Input label="Email" error="Bad format" id="test-email" />);
    const input = screen.getByLabelText("Email");
    expect(input.getAttribute("aria-describedby")).toContain("error");
  });

  it("renders as disabled", () => {
    render(<Input label="Locked" disabled />);
    expect(screen.getByLabelText("Locked")).toBeDisabled();
  });

  it("accepts placeholder text", () => {
    render(<Input label="Search" placeholder="Type here..." />);
    expect(screen.getByPlaceholderText("Type here...")).toBeInTheDocument();
  });

  it("passes accessibility audit (axe = 0 violations)", async () => {
    const { container } = render(
      <Input label="Accessible input" placeholder="Enter text" />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("passes accessibility audit in error state", async () => {
    const { container } = render(
      <Input label="Bad field" error="Something went wrong" />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
