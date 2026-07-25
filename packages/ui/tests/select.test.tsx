import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Select, type SelectItem } from "../src/components/select";

const fruitItems: SelectItem[] = [
  { id: "apple", label: "Apple" },
  { id: "banana", label: "Banana" },
  { id: "cherry", label: "Cherry" },
];

describe("Select", () => {
  it("renders with a label", () => {
    render(<Select label="Choose fruit" items={fruitItems} />);
    expect(screen.getByText("Choose fruit")).toBeInTheDocument();
  });

  it("shows placeholder by default", () => {
    render(
      <Select
        label="Fruit"
        items={fruitItems}
        placeholder="Pick one..."
      />,
    );
    expect(screen.getByText("Pick one...")).toBeInTheDocument();
  });

  it("opens popover on click and shows options", async () => {
    const user = userEvent.setup();
    render(<Select label="Fruit" items={fruitItems} />);
    await user.click(screen.getByRole("button"));
    // React Aria renders options in a listbox
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("shows error message", () => {
    render(
      <Select label="Fruit" items={fruitItems} error="Selection required" />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Selection required");
  });

  it("passes accessibility audit (axe = 0 violations)", async () => {
    const { container } = render(
      <Select label="Accessible select" items={fruitItems} />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
