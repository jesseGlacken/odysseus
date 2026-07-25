import { createFileRoute } from '@tanstack/react-router';

import { t } from '@/lib/i18n';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  return (
    <section aria-labelledby="settings-heading">
      <h1 id="settings-heading">{t('settings.heading')}</h1>
    </section>
  );
}
