import { Component, type ErrorInfo, type ReactNode } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/providers/AuthProvider';
import { ThemeProvider } from '@/providers/ThemeProvider';
import { TimerProvider } from '@/providers/TimerProvider';
import { ModalProvider } from '@/providers/ModalProvider';
import { ToastProvider } from '@/providers/ToastProvider';
import { DataRefreshProvider } from '@/providers/DataRefreshProvider';
import { routes } from '@/routes';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
  },
});

const router = createBrowserRouter(routes);

/** Root-level error boundary — catches crashes in the provider tree or router. */
class RootErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[RootErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'Inter, sans-serif', color: '#ccc', background: '#111', minHeight: '100vh' }}>
          <h1 style={{ color: '#e5a300' }}>Something went wrong</h1>
          <p>{this.state.error.message}</p>
          <button
            onClick={() => { this.setState({ error: null }); window.location.href = '/'; }}
            style={{ marginTop: 16, padding: '8px 20px', background: '#e5a300', color: '#111', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Go to Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <RootErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <DataRefreshProvider>
          <ThemeProvider>
            <AuthProvider>
              <ToastProvider>
                <TimerProvider>
                  <ModalProvider>
                    <RouterProvider router={router} />
                  </ModalProvider>
                </TimerProvider>
              </ToastProvider>
            </AuthProvider>
          </ThemeProvider>
        </DataRefreshProvider>
      </QueryClientProvider>
    </RootErrorBoundary>
  );
}
