import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../src/components/tabs";

describe("Tabs", () => {
  function TestTabs({ defaultValue = "tab1" }: { defaultValue?: string }) {
    return (
      <Tabs defaultValue={defaultValue}>
        <TabsList>
          <TabsTrigger value="tab1">First</TabsTrigger>
          <TabsTrigger value="tab2">Second</TabsTrigger>
          <TabsTrigger value="tab3">Third</TabsTrigger>
        </TabsList>
        <TabsContent value="tab1">Content one</TabsContent>
        <TabsContent value="tab2">Content two</TabsContent>
        <TabsContent value="tab3">Content three</TabsContent>
      </Tabs>
    );
  }

  it("renders tab triggers", () => {
    render(<TestTabs />);
    expect(screen.getByRole("tab", { name: "First" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Second" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Third" })).toBeInTheDocument();
  });

  it("shows content for the active tab only", () => {
    render(<TestTabs />);
    expect(screen.getByText("Content one")).toBeInTheDocument();
    // The other tabs' content should not be visible
    expect(screen.queryByText("Content two")).toBeNull();
    expect(screen.queryByText("Content three")).toBeNull();
  });

  it("switches tab content on click", async () => {
    const user = userEvent.setup();
    render(<TestTabs />);
    await user.click(screen.getByRole("tab", { name: "Second" }));
    expect(screen.getByText("Content two")).toBeInTheDocument();
    expect(screen.queryByText("Content one")).toBeNull();
  });

  it("marks active tab with aria-selected", () => {
    render(<TestTabs />);
    const firstTab = screen.getByRole("tab", { name: "First" });
    expect(firstTab).toHaveAttribute("aria-selected", "true");
    const secondTab = screen.getByRole("tab", { name: "Second" });
    expect(secondTab).toHaveAttribute("aria-selected", "false");
  });

  it("passes accessibility audit (axe = 0 violations)", async () => {
    const { container } = render(<TestTabs />);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
