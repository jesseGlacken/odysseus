import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';

import { ErrorBoundary } from './components/error-boundary';

describe('web app scaffold', () => {
  describe('ErrorBoundary', () => {
    it('renders children when no error is thrown', () => {
      render(
        <ErrorBoundary>
          <p>Hello from Odysseus</p>
        </ErrorBoundary>,
      );
      expect(screen.getByText('Hello from Odysseus')).toBeInTheDocument();
    });

    it('renders fallback UI when an error is thrown', () => {
      const Thrower = () => {
        throw new Error('Test explosion');
      };
      render(
        <ErrorBoundary>
          <Thrower />
        </ErrorBoundary>,
      );
      expect(screen.getByRole('main')).toBeInTheDocument();
      expect(screen.getByText('Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('Test explosion')).toBeInTheDocument();
    });

    it('renders custom fallback when provided', () => {
      const Thrower = () => {
        throw new Error('Boom');
      };
      render(
        <ErrorBoundary fallback={<p>Custom error UI</p>}>
          <Thrower />
        </ErrorBoundary>,
      );
      expect(screen.getByText('Custom error UI')).toBeInTheDocument();
    });

    it('passes automated accessibility check', async () => {
      const { container } = render(
        <ErrorBoundary>
          <p>Accessible content</p>
        </ErrorBoundary>,
      );
      const results = await axe(container);
      expect(results.violations).toEqual([]);
    });
  });
});
