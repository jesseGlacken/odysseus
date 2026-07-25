import { createFileRoute } from '@tanstack/react-router';

import { t } from '@/lib/i18n';

export const Route = createFileRoute('/')({
  component: HomePage,
});

function HomePage() {
  return (
    <section aria-labelledby="home-heading">
      <h1 id="home-heading">{t('home.heading')}</h1>
      <p>{t('home.body')}</p>
    </section>
  );
}
