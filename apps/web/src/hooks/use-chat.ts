import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

// ── Query hooks ──────────────────────────────────────────────────────

/**
 * List all sessions for the current user.
 * Maps to GET /api/sessions.
 */
export function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () =>
      apiClient.GET('/api/sessions').then((res) => {
        if (!res.response.ok) throw new Error(`Sessions fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Create a new chat session.
 * Maps to POST /api/session.
 */
export function useCreateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: { name?: string; model?: string }) => {
      const params = new URLSearchParams();
      params.append('name', body.name ?? 'New Session');
      if (body.model) params.append('model', body.model);
      return apiClient
        .POST('/api/session', {
          body: params,
          bodySerializer: (b: unknown) => (b as URLSearchParams).toString(),
        } as never)
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

/**
 * Delete a session by ID.
 * Maps to DELETE /api/session/{sid}.
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (sid: string) =>
      apiClient.DELETE('/api/session/{sid}', {
        params: { path: { sid } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Session delete failed: ${res.response.status}`);
        return res.data;
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

/**
 * Fetch chat history (messages) for a specific session.
 * Maps to GET /api/history/{sid}.
 */
export function useMessages(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () =>
      apiClient.GET('/api/history/{sid}', {
        params: { path: { sid: sessionId! } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`History fetch failed: ${res.response.status}`);
        return res.data;
      }),
    enabled: !!sessionId,
  });
}

/**
 * Send a chat message (non-streaming).
 * Maps to POST /api/chat.
 */
export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      message: string;
      session: string;
      attachments?: string[];
      use_web?: boolean;
      use_research?: boolean;
      time_filter?: string;
      preset_id?: string;
    }) =>
      apiClient
        .POST('/api/chat', {
          body: {
            message: body.message,
            session: body.session,
            attachments: body.attachments ?? null,
            use_web: body.use_web ?? null,
            use_research: body.use_research ?? null,
            time_filter: body.time_filter ?? null,
            preset_id: body.preset_id ?? null,
          },
        })
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['messages', variables.session],
      });
    },
  });
}

// ── SSE streaming hook ───────────────────────────────────────────────

export interface StreamingChatState {
  /** Accumulated text chunks received so far. */
  text: string;
  /** Whether a stream is currently active. */
  isStreaming: boolean;
  /** Error object if the stream failed. */
  error: Error | null;
}

export interface UseStreamingChatOptions {
  /** Called when a new delta chunk arrives. */
  onChunk?: (chunk: string) => void;
  /** Called when the stream completes successfully. */
  onDone?: (fullText: string) => void;
  /** Called when the stream encounters an error. */
  onError?: (error: Error) => void;
  /** Called on every state change, for fine-grained control. */
  onStateChange?: (state: StreamingChatState) => void;
}

/**
 * SSE streaming chat hook.
 *
 * Uses `fetch` with a `ReadableStream` to consume the text/event-stream
 * response from POST /api/chat_stream. Handles:
 * - AbortController cleanup on unmount
 * - Exponential-backoff reconnect on connection loss
 * - Typed event parsing from SSE chunks
 */
export function useStreamingChat(options: UseStreamingChatOptions = {}) {
  const { onChunk, onDone, onError, onStateChange } = options;

  const [state, setState] = useState<StreamingChatState>({
    text: '',
    isStreaming: false,
    error: null,
  });

  const abortRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);
  const maxRetries = 5;
  const onChunkRef = useRef(onChunk);
  const onDoneRef = useRef(onDone);
  const onErrorRef = useRef(onError);
  const onStateChangeRef = useRef(onStateChange);

  // Keep refs fresh without triggering effect re-runs
  onChunkRef.current = onChunk;
  onDoneRef.current = onDone;
  onErrorRef.current = onError;
  onStateChangeRef.current = onStateChange;

  const updateState = useCallback(
    (patch: Partial<StreamingChatState>) => {
      setState((prev) => {
        const next = { ...prev, ...patch };
        onStateChangeRef.current?.(next);
        return next;
      });
    },
    [],
  );

  const start = useCallback(
    async (requestBody: Record<string, unknown>) => {
      // Abort any existing stream
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      updateState({ text: '', isStreaming: true, error: null });
      retryCountRef.current = 0;

      const doFetch = async (): Promise<void> => {
        try {
          const response = await fetch('/api/chat_stream', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Accept: 'text/event-stream',
            },
            body: JSON.stringify(requestBody),
            signal: abortRef.current!.signal,
          });

          if (!response.ok) {
            throw new Error(
              `Chat stream failed with status ${response.status}`,
            );
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error('Response body is not readable');
          }

          const decoder = new TextDecoder();
          let fullText = '';
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE lines: "data: <payload>\n\n"
            const lines = buffer.split('\n');
            // The last line may be incomplete; keep it in the buffer
            buffer = lines.pop() ?? '';

            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed || trimmed.startsWith(':')) continue; // comment or empty

              if (trimmed.startsWith('data: ')) {
                const payload = trimmed.slice(6);
                if (payload === '[DONE]') {
                  // Stream finished signal
                  updateState({ isStreaming: false });
                  onDoneRef.current?.(fullText);
                  return;
                }
                try {
                  const parsed = JSON.parse(payload);
                  const chunk =
                    typeof parsed === 'string'
                      ? parsed
                      : parsed?.content ?? parsed?.delta ?? '';
                  fullText += chunk;
                  updateState({ text: fullText });
                  onChunkRef.current?.(chunk);
                } catch {
                  // Non-JSON payload — treat as raw text
                  fullText += payload;
                  updateState({ text: fullText });
                  onChunkRef.current?.(payload);
                }
              }
            }
          }

          // Stream ended normally
          updateState({ isStreaming: false });
          onDoneRef.current?.(fullText);
        } catch (err) {
          if ((err as Error).name === 'AbortError') return;

          if (retryCountRef.current < maxRetries) {
            retryCountRef.current += 1;
            const delay = Math.min(1000 * 2 ** retryCountRef.current, 30000);
            await new Promise((resolve) => setTimeout(resolve, delay));
            return doFetch();
          }

          const error =
            err instanceof Error ? err : new Error(String(err));
          updateState({ isStreaming: false, error });
          onErrorRef.current?.(error);
        }
      };

      await doFetch();
    },
    [updateState],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    updateState({ isStreaming: false });
  }, [updateState]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { ...state, start, stop };
}
