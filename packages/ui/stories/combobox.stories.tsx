import type { Meta, StoryObj } from "@storybook/react";
import { ComboBox } from "../src/components/combobox";

const items = [
  { id: "apple", label: "Apple" },
  { id: "banana", label: "Banana" },
  { id: "cherry", label: "Cherry" },
  { id: "dragonfruit", label: "Dragonfruit" },
  { id: "elderberry", label: "Elderberry" },
];

const meta: Meta<typeof ComboBox> = {
  title: "Components/ComboBox",
  component: ComboBox,
};

export default meta;
type Story = StoryObj<typeof ComboBox>;

export const Default: Story = {
  args: {
    label: "Search fruit",
    items,
    placeholder: "Type to filter...",
  },
};
