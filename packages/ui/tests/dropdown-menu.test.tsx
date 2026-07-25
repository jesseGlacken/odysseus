import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "vitest-axe";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "../src/components/dropdown-menu";
import { Button } from "../src/components/button";

describe("DropdownMenu", () => {
  function TestMenu() {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button>Actions</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuLabel>My Account</DropdownMenuLabel>
          <DropdownMenuItem>Profile</DropdownMenuItem>
          <DropdownMenuItem>Settings</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Log out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    );
  }

  it("renders the trigger button", () => {
    render(<TestMenu />);
    expect(
      screen.getByRole("button", { name: "Actions" }),
    ).toBeInTheDocument();
  });

  it("opens menu on trigger click", async () => {
    const user = userEvent.setup();
    render(<TestMenu />);
    await user.click(screen.getByRole("button", { name: "Actions" }));
    // Radix renders into a portal with role="menu"
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Log out")).toBeInTheDocument();
  });

  it("shows label and separator", async () => {
    const user = userEvent.setup();
    render(<TestMenu />);
    await user.click(screen.getByRole("button", { name: "Actions" }));
    expect(screen.getByText("My Account")).toBeInTheDocument();
    // Separators have role="separator"
    expect(screen.getByRole("separator")).toBeInTheDocument();
  });

  it("passes accessibility audit when open (axe = 0 violations)", async () => {
    const user = userEvent.setup();
    const { container } = render(<TestMenu />);
    await user.click(screen.getByRole("button", { name: "Actions" }));
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
