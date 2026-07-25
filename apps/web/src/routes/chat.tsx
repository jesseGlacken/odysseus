import { createFileRoute } from '@tanstack/react-router';

import { t } from '@/lib/i18n';

export const Route = createFileRoute('/chat')({
  component: ChatPage,
});

function ChatPage() {
  return (
    <section aria-labelledby="chat-heading">
      <h1 id="chat-heading">{t('chat.heading')}</h1>
    </section>
  );
}
