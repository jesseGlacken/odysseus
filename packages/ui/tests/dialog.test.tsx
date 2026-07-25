import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../src/components/dialog";
import { Button } from "../src/components/button";

describe("Dialog", () => {
  function TestDialog({ defaultOpen = false }: { defaultOpen?: boolean }) {
    return (
      <Dialog defaultOpen={defaultOpen}>
        <DialogTrigger asChild>
          <Button>Open dialog</Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Test Title</DialogTitle>
            <DialogDescription>A test description</DialogDescription>
          </DialogHeader>
          <p>Dialog body content</p>
        </DialogContent>
      </Dialog>
    );
  }

  it("renders the trigger button", () => {
    render(<TestDialog />);
    expect(
      screen.getByRole("button", { name: "Open dialog" }),
    ).toBeInTheDocument();
  });

  it("opens the dialog on trigger click", async () => {
    const user = userEvent.setup();
    render(<TestDialog />);
    await user.click(screen.getByRole("button", { name: "Open dialog" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Test Title")).toBeInTheDocument();
    expect(screen.getByText("A test description")).toBeInTheDocument();
  });

  it("shows content when defaultOpen is true", () => {
    render(<TestDialog defaultOpen />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("has a close button with accessible name", async () => {
    const user = userEvent.setup();
    render(<TestDialog defaultOpen />);
    const closeBtn = screen.getByRole("button", { name: /close dialog/i });
    expect(closeBtn).toBeInTheDocument();
    await user.click(closeBtn);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("passes accessibility audit when open (axe = 0 violations)", async () => {
    const { container } = render(<TestDialog defaultOpen />);
    // axe needs the portal-rendered dialog in the DOM
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
