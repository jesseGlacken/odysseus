import { Link, Outlet, createRootRoute } from '@tanstack/react-router';

import { t } from '@/lib/i18n';

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <>
      <a
        href="#main-content"
        style={{
          position: 'absolute',
          top: '-100%',
          left: 0,
          zIndex: 100,
          padding: '0.5rem 1rem',
          background: '#3b82f6',
          color: '#fff',
        }}
        onFocus={(e) => {
          e.currentTarget.style.top = '0';
        }}
        onBlur={(e) => {
          e.currentTarget.style.top = '-100%';
        }}
      >
        Skip to main content
      </a>
      <header role="banner">
        <nav aria-label={t('nav.label')}>
          <Link to="/">{t('nav.home')}</Link>
          {' | '}
          <Link to="/chat">{t('nav.chat')}</Link>
          {' | '}
          <Link to="/documents">{t('nav.documents')}</Link>
          {' | '}
          <Link to="/settings">{t('nav.settings')}</Link>
        </nav>
      </header>
      <main id="main-content" role="main">
        <Outlet />
      </main>
      <footer role="contentinfo">
        <p>{t('footer.credit')}</p>
      </footer>
    </>
  );
}
