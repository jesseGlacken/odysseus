import type { Meta, StoryObj } from "@storybook/react";
import { Input } from "../src/components/input";

const meta: Meta<typeof Input> = {
  title: "Components/Input",
  component: Input,
  argTypes: {
    label: { control: "text" },
    placeholder: { control: "text" },
    error: { control: "text" },
    disabled: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof Input>;

export const Default: Story = {
  args: {
    label: "Email",
    placeholder: "you@example.com",
  },
};

export const WithError: Story = {
  args: {
    label: "Email",
    error: "Please enter a valid email address",
    defaultValue: "not-an-email",
  },
};

export const Disabled: Story = {
  args: {
    label: "Disabled field",
    disabled: true,
    defaultValue: "Cannot edit",
  },
};
