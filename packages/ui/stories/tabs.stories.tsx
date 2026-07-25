import type { Meta, StoryObj } from "@storybook/react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../src/components/tabs";

const meta: Meta<typeof Tabs> = {
  title: "Components/Tabs",
  component: Tabs,
};

export default meta;
type Story = StoryObj<typeof Tabs>;

export const Default: Story = {
  render: () => (
    <Tabs defaultValue="account">
      <TabsList>
        <TabsTrigger value="account">Account</TabsTrigger>
        <TabsTrigger value="password">Password</TabsTrigger>
        <TabsTrigger value="settings">Settings</TabsTrigger>
      </TabsList>
      <TabsContent value="account">
        <div className="rounded-md border border-[var(--border)] p-4">
          <h3 className="text-lg font-medium">Account</h3>
          <p className="text-sm text-[var(--muted-foreground)]">
            Manage your account settings here.
          </p>
        </div>
      </TabsContent>
      <TabsContent value="password">
        <div className="rounded-md border border-[var(--border)] p-4">
          <h3 className="text-lg font-medium">Password</h3>
          <p className="text-sm text-[var(--muted-foreground)]">
            Change your password here.
          </p>
        </div>
      </TabsContent>
      <TabsContent value="settings">
        <div className="rounded-md border border-[var(--border)] p-4">
          <h3 className="text-lg font-medium">Settings</h3>
          <p className="text-sm text-[var(--muted-foreground)]">
            Configure your preferences.
          </p>
        </div>
      </TabsContent>
    </Tabs>
  ),
};
