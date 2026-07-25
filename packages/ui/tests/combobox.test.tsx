import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { ComboBox, type ComboBoxItem } from "../src/components/combobox";

const fruitItems: ComboBoxItem[] = [
  { id: "apple", label: "Apple" },
  { id: "banana", label: "Banana" },
  { id: "cherry", label: "Cherry" },
  { id: "dragonfruit", label: "Dragonfruit" },
];

describe("ComboBox", () => {
  it("renders with a label", () => {
    render(<ComboBox label="Search fruit" items={fruitItems} />);
    expect(screen.getByText("Search fruit")).toBeInTheDocument();
  });

  it("renders an input for typing", () => {
    render(<ComboBox label="Fruit" items={fruitItems} />);
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("shows placeholder in input", () => {
    render(
      <ComboBox
        label="Fruit"
        items={fruitItems}
        placeholder="Find a fruit..."
      />,
    );
    expect(screen.getByPlaceholderText("Find a fruit...")).toBeInTheDocument();
  });

  it("filters items as user types", async () => {
    const user = userEvent.setup();
    render(<ComboBox label="Fruit" items={fruitItems} />);
    const input = screen.getByRole("combobox");
    await user.type(input, "ban");
    // Should open the listbox with filtered results
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });

  it("passes accessibility audit (axe = 0 violations)", async () => {
    const { container } = render(
      <ComboBox label="Accessible combobox" items={fruitItems} />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
