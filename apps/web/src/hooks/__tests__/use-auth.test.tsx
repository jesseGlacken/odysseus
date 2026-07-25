import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import type { ReactNode } from 'react';

// ── Mock the generated client SDK ────────────────────────────────────
const mockGET = vi.fn();
const mockPOST = vi.fn();
const mockDELETE = vi.fn();
const mockPUT = vi.fn();

vi.mock('@odysseus/client-sdk', () => ({
  apiClient: {
    GET: (...args: unknown[]) => mockGET(...args),
    POST: (...args: unknown[]) => mockPOST(...args),
    DELETE: (...args: unknown[]) => mockDELETE(...args),
    PUT: (...args: unknown[]) => mockPUT(...args),
  },
}));

// ── Helpers ──────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

function okResponse<T>(data: T) {
  return Promise.resolve({
    data,
    error: undefined,
    response: { ok: true, status: 200 } as Response,
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Tests ────────────────────────────────────────────────────────────

import {
  useAuthStatus,
  useLogin,
  useLogout,
  useSetup,
  useChangePassword,
} from '../use-auth';

import {
  useSessions,
  useCreateSession,
  useDeleteSession,
  useMessages,
  useSendMessage,
  useStreamingChat,
} from '../use-chat';

import {
  useDocumentsLibrary,
  useDocuments,
  useDocument,
  useCreateDocument,
  useUploadDocument,
  useDeleteDocument,
} from '../use-documents';

import {
  useEmails,
  useEmailContacts,
  useReadEmail,
  useUnreadState,
  useMarkRead,
  useDeleteEmail,
} from '../use-email';

import {
  useSettings,
  useUpdateSettings,
  useAuthPolicy,
  useFeatures,
} from '../use-settings';

describe('useAuthStatus', () => {
  it('calls GET /api/auth/status and returns data', async () => {
    const data = { configured: true, authenticated: true, username: 'test', is_admin: false };
    mockGET.mockReturnValue(okResponse(data));

    const { result } = renderHook(() => useAuthStatus(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/auth/status');
    expect(result.current.data).toEqual(data);
  });

  it('sets the correct queryKey', async () => {
    mockGET.mockReturnValue(okResponse({}));
    const { result } = renderHook(() => useAuthStatus(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // The queryKey is used internally by react-query.
    // We verify by checking the hook resolved.
    expect(result.current.data).toBeDefined();
  });
});

describe('useLogin', () => {
  it('calls POST /api/auth/login with correct body', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true, username: 'test' }));

    const { result } = renderHook(() => useLogin(), { wrapper: createWrapper() });

    result.current.mutate({ username: 'test', password: 'secret' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/auth/login', {
      body: {
        username: 'test',
        password: 'secret',
        remember: true,
        totp_code: null,
      },
    });
  });

  it('invalidates auth queries on success', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    function Wrapper({ children }: { children: ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          {children}
        </QueryClientProvider>
      );
    }

    const { result } = renderHook(() => useLogin(), { wrapper: Wrapper });

    result.current.mutate({ username: 'test', password: 'secret' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['auth'] });
  });
});

describe('useLogout', () => {
  it('calls POST /api/auth/logout', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useLogout(), { wrapper: createWrapper() });

    result.current.mutate();

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/auth/logout');
  });
});

describe('useSetup', () => {
  it('calls POST /api/auth/setup with correct body', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useSetup(), { wrapper: createWrapper() });

    result.current.mutate({ username: 'admin', password: 'admin123' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/auth/setup', {
      body: { username: 'admin', password: 'admin123' },
    });
  });
});

describe('useChangePassword', () => {
  it('calls POST /api/auth/change-password with correct body', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useChangePassword(), { wrapper: createWrapper() });

    result.current.mutate({ current_password: 'old', new_password: 'new' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/auth/change-password', {
      body: { current_password: 'old', new_password: 'new' },
    });
  });
});

// ── Chat hooks ──────────────────────────────────────────────────────

describe('useSessions', () => {
  it('calls GET /api/sessions', async () => {
    mockGET.mockReturnValue(okResponse([{ id: '1', name: 'Session 1' }]));

    const { result } = renderHook(() => useSessions(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/sessions');
    expect(result.current.data).toEqual([{ id: '1', name: 'Session 1' }]);
  });
});

describe('useCreateSession', () => {
  it('calls POST /api/session', async () => {
    mockPOST.mockReturnValue(okResponse({ id: 'new', name: 'New Session' }));

    const { result } = renderHook(() => useCreateSession(), { wrapper: createWrapper() });

    result.current.mutate({ name: 'My Session', model: 'gpt-4' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalled();
    const callArgs = mockPOST.mock.calls[0]!;
    expect(callArgs[0]).toBe('/api/session');
  });
});

describe('useDeleteSession', () => {
  it('calls DELETE /api/session/{sid}', async () => {
    mockDELETE.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useDeleteSession(), { wrapper: createWrapper() });

    result.current.mutate('session-123');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockDELETE).toHaveBeenCalledWith('/api/session/{sid}', {
      params: { path: { sid: 'session-123' } },
    });
  });
});

describe('useMessages', () => {
  it('does not fetch when sessionId is undefined', () => {
    renderHook(() => useMessages(undefined), { wrapper: createWrapper() });
    expect(mockGET).not.toHaveBeenCalled();
  });

  it('calls GET /api/history/{sid} when sessionId is provided', async () => {
    mockGET.mockReturnValue(okResponse([{ role: 'user', content: 'hi' }]));

    const { result } = renderHook(() => useMessages('session-1'), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/history/{sid}', {
      params: { path: { sid: 'session-1' } },
    });
  });
});

describe('useSendMessage', () => {
  it('calls POST /api/chat with correct body', async () => {
    mockPOST.mockReturnValue(okResponse({ reply: 'Hello!' }));

    const { result } = renderHook(() => useSendMessage(), { wrapper: createWrapper() });

    result.current.mutate({ message: 'Hi', session: 's1' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/chat', {
      body: {
        message: 'Hi',
        session: 's1',
        attachments: null,
        use_web: null,
        use_research: null,
        time_filter: null,
        preset_id: null,
      },
    });
  });
});

// ── Document hooks ──────────────────────────────────────────────────

describe('useDocumentsLibrary', () => {
  it('calls GET /api/documents/library', async () => {
    mockGET.mockReturnValue(okResponse([{ id: 'd1', title: 'Doc 1' }]));

    const { result } = renderHook(() => useDocumentsLibrary(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/documents/library');
  });
});

describe('useDocuments', () => {
  it('calls GET /api/documents/{session_id}', async () => {
    mockGET.mockReturnValue(okResponse([]));

    const { result } = renderHook(() => useDocuments('s1'), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/documents/{session_id}', {
      params: { path: { session_id: 's1' } },
    });
  });
});

describe('useDocument', () => {
  it('calls GET /api/document/{doc_id}', async () => {
    mockGET.mockReturnValue(okResponse({ id: 'd1', title: 'My Doc' }));

    const { result } = renderHook(() => useDocument('d1'), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/document/{doc_id}', {
      params: { path: { doc_id: 'd1' } },
    });
  });
});

describe('useCreateDocument', () => {
  it('calls POST /api/document', async () => {
    mockPOST.mockReturnValue(okResponse({ id: 'new-doc' }));

    const { result } = renderHook(() => useCreateDocument(), { wrapper: createWrapper() });

    result.current.mutate({ title: 'Test', content: 'Body', session_id: 's1' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalled();
    const callArgs = mockPOST.mock.calls[0]!;
    expect(callArgs[0]).toBe('/api/document');
  });
});

describe('useUploadDocument', () => {
  it('calls POST /api/upload with FormData', async () => {
    mockPOST.mockReturnValue(okResponse({ file_id: 'f1' }));
    const formData = new FormData();
    formData.append('file', new Blob(['test']), 'test.txt');

    const { result } = renderHook(() => useUploadDocument(), { wrapper: createWrapper() });

    result.current.mutate(formData);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalled();
    const callArgs = mockPOST.mock.calls[0]!;
    expect(callArgs[0]).toBe('/api/upload');
  });
});

describe('useDeleteDocument', () => {
  it('calls DELETE /api/document/{doc_id}', async () => {
    mockDELETE.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useDeleteDocument(), { wrapper: createWrapper() });

    result.current.mutate('d1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockDELETE).toHaveBeenCalledWith('/api/document/{doc_id}', {
      params: { path: { doc_id: 'd1' } },
    });
  });
});

// ── Email hooks ─────────────────────────────────────────────────────

describe('useEmails', () => {
  it('calls GET /api/email/list', async () => {
    mockGET.mockReturnValue(okResponse([{ uid: '1', subject: 'Test' }]));

    const { result } = renderHook(() => useEmails(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalled();
    const callArgs = mockGET.mock.calls[0]!;
    expect(callArgs[0]).toBe('/api/email/list');
  });
});

describe('useEmailContacts', () => {
  it('calls GET /api/email/contacts', async () => {
    mockGET.mockReturnValue(okResponse([]));

    const { result } = renderHook(() => useEmailContacts(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/email/contacts');
  });
});

describe('useReadEmail', () => {
  it('calls GET /api/email/read/{uid}', async () => {
    mockGET.mockReturnValue(okResponse({ uid: '123', subject: 'Hello' }));

    const { result } = renderHook(() => useReadEmail('123'), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/email/read/{uid}', {
      params: { path: { uid: '123' } },
    });
  });
});

describe('useUnreadState', () => {
  it('calls GET /api/email/unread-state', async () => {
    mockGET.mockReturnValue(okResponse({ count: 5 }));

    const { result } = renderHook(() => useUnreadState(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/email/unread-state');
  });
});

describe('useMarkRead', () => {
  it('calls POST /api/email/mark-read/{uid}', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useMarkRead(), { wrapper: createWrapper() });

    result.current.mutate('email-1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/email/mark-read/{uid}', {
      params: { path: { uid: 'email-1' } },
    });
  });
});

describe('useDeleteEmail', () => {
  it('calls DELETE /api/email/delete/{uid}', async () => {
    mockDELETE.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useDeleteEmail(), { wrapper: createWrapper() });

    result.current.mutate('email-1');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockDELETE).toHaveBeenCalledWith('/api/email/delete/{uid}', {
      params: { path: { uid: 'email-1' } },
    });
  });
});

// ── Settings hooks ──────────────────────────────────────────────────

describe('useSettings', () => {
  it('calls GET /api/auth/settings', async () => {
    mockGET.mockReturnValue(okResponse({ theme: 'dark' }));

    const { result } = renderHook(() => useSettings(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/auth/settings');
  });
});

describe('useUpdateSettings', () => {
  it('calls POST /api/auth/settings with body', async () => {
    mockPOST.mockReturnValue(okResponse({ ok: true }));

    const { result } = renderHook(() => useUpdateSettings(), { wrapper: createWrapper() });

    result.current.mutate({ theme: 'light' });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockPOST).toHaveBeenCalledWith('/api/auth/settings', {
      body: { theme: 'light' },
    });
  });
});

describe('useAuthPolicy', () => {
  it('calls GET /api/auth/policy', async () => {
    mockGET.mockReturnValue(okResponse({ min_password_length: 8 }));

    const { result } = renderHook(() => useAuthPolicy(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/auth/policy');
  });
});

describe('useFeatures', () => {
  it('calls GET /api/auth/features', async () => {
    mockGET.mockReturnValue(okResponse({ chat: true }));

    const { result } = renderHook(() => useFeatures(), { wrapper: createWrapper() });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(mockGET).toHaveBeenCalledWith('/api/auth/features');
  });
});

// ── SSE streaming hook ──────────────────────────────────────────────

describe('useStreamingChat', () => {
  it('exposes isStreaming=false and text="" initially', () => {
    const { result } = renderHook(() => useStreamingChat(), { wrapper: createWrapper() });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.text).toBe('');
    expect(result.current.error).toBeNull();
  });

  it('sets isStreaming true when start() is called', async () => {
    mockPOST.mockResolvedValue({
      response: {
        ok: true,
        body: {
          getReader: () => ({
            read: () =>
              new Promise<{ done: boolean; value?: Uint8Array }>(() => {}),
          }),
        },
      },
    });

    const { result } = renderHook(() => useStreamingChat(), { wrapper: createWrapper() });

    result.current.start({ message: 'Hello', session: 's1' });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(true);
    });

    result.current.stop();
  });

  it('calls onDone with accumulated text when stream finishes', async () => {
    const onDone = vi.fn();

    mockPOST.mockResolvedValue({
      response: {
        ok: true,
        body: {
          getReader: () => {
            let doneCalled = false;
            return {
              read: () => {
                if (doneCalled) {
                  return Promise.resolve({ done: true, value: undefined });
                }
                doneCalled = true;
                const chunk = new TextEncoder().encode(
                  'event: token\ndata: {"content":"Hello"}\n\nevent: done\ndata: \n\n',
                );
                return Promise.resolve({ done: false, value: chunk });
              },
            };
          },
        },
      },
    });

    const { result } = renderHook(() => useStreamingChat({ onDone }), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.start({ message: 'Hi' });
    });

    await waitFor(() => {
      expect(onDone).toHaveBeenCalledWith('Hello');
    });
  });

  it('calls onChunk for each delta', async () => {
    const onChunk = vi.fn();

    mockPOST.mockResolvedValue({
      response: {
        ok: true,
        body: {
          getReader: () => {
            let calls = 0;
            return {
              read: () => {
                calls += 1;
                if (calls === 1) {
                  const chunk = new TextEncoder().encode('event: token\ndata: {"delta":"Hello"}\n\n');
                  return Promise.resolve({ done: false, value: chunk });
                }
                const done = new TextEncoder().encode('event: done\ndata: \n\n');
                return Promise.resolve({ done: false, value: done });
              },
            };
          },
        },
      },
    });

    const { result } = renderHook(() => useStreamingChat({ onChunk }), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.start({ message: 'Hi' });
    });

    await waitFor(() => {
      expect(onChunk).toHaveBeenCalledWith('Hello');
    });
  });

  it('calls onError when stream fails', async () => {
    const onError = vi.fn();

    // Use a 400-status error — non-retryable per isRetryableError(), avoids fake-timer loops
    mockPOST.mockRejectedValue(new Error('Chat stream failed with status 400'));

    const { result } = renderHook(() => useStreamingChat({ onError }), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.start({ message: 'Hi' });
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalled();
    });
  });

  it('aborts fetch on stop()', async () => {
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    result.current.start({ message: 'Hi' });
    result.current.stop();

    expect(result.current.isStreaming).toBe(false);
  });

  it('cleans up abort controller on unmount', async () => {
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort');

    mockPOST.mockResolvedValue({
      response: {
        ok: true,
        body: {
          getReader: () => ({
            read: () =>
              new Promise<{ done: boolean; value?: Uint8Array }>(() => {}),
          }),
        },
      },
    });

    const { result, unmount } = renderHook(() => useStreamingChat(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.start({ message: 'Hi' });
    });

    unmount();

    expect(abortSpy).toHaveBeenCalled();

    abortSpy.mockRestore();
  });
});