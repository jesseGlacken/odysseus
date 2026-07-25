import type { Meta, StoryObj } from "@storybook/react";
import { Select } from "../src/components/select";

const items = [
  { id: "apple", label: "Apple" },
  { id: "banana", label: "Banana" },
  { id: "cherry", label: "Cherry" },
  { id: "dragonfruit", label: "Dragonfruit" },
  { id: "elderberry", label: "Elderberry" },
];

const meta: Meta<typeof Select> = {
  title: "Components/Select",
  component: Select,
};

export default meta;
type Story = StoryObj<typeof Select>;

export const Default: Story = {
  args: {
    label: "Favourite fruit",
    items,
    placeholder: "Choose a fruit...",
  },
};

export const WithError: Story = {
  args: {
    label: "Fruit",
    items,
    error: "Please select a fruit",
  },
};
