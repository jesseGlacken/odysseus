import { Component, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, info);
    // TODO: wire to monitoring service when available
  }

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <main role="main" style={{ padding: '2rem', maxWidth: '36rem', margin: '0 auto' }}>
          <h1>Something went wrong</h1>
          <p>
            An unexpected error occurred. Please try refreshing the page.
          </p>
          <pre
            style={{
              background: '#f1f5f9',
              padding: '1rem',
              borderRadius: '0.5rem',
              overflow: 'auto',
              fontSize: '0.875rem',
            }}
          >
            {this.state.error?.message ?? 'Unknown error'}
          </pre>
        </main>
      );
    }
    return this.props.children;
  }
}
