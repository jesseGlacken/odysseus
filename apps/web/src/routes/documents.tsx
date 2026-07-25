import { createFileRoute } from '@tanstack/react-router';

import { t } from '@/lib/i18n';

export const Route = createFileRoute('/documents')({
  component: DocumentsPage,
});

function DocumentsPage() {
  return (
    <section aria-labelledby="documents-heading">
      <h1 id="documents-heading">{t('documents.heading')}</h1>
    </section>
  );
}
