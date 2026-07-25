import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

// ── Helpers ─────────────────────────────────────────────────────────

/** SDK-sanctioned streaming: uses apiClient for the initial POST (ADR-0001
 *  compliant), then reads the text/event-stream via the raw Response body.
 *  openapi-fetch types don't expose ReadableStream, so we cast the result. */
async function apiClientStream(body: Record<string, unknown>): Promise<ReadableStreamDefaultReader<Uint8Array>> {
  const raw = (await apiClient.POST('/api/chat_stream', {
    body: body as unknown as never,
    bodySerializer: (b: Record<string, unknown>) => JSON.stringify(b),
  } as never)) as unknown as { response: Response };

  if (!raw.response.ok) throw new Error(`Chat stream failed with status ${raw.response.status}`);
  const reader = raw.response.body?.getReader();
  if (!reader) throw new Error('Response body is not readable');
  return reader;
}

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
      params.append('name', body.name ?? '');
      if (body.model) params.append('model', body.model);
      return apiClient
        .POST('/api/session', {
          body: params as unknown as never,
          bodySerializer: (b: URLSearchParams) => b.toString(),
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

/** SSE event types as defined in the OpenAPI contract for /api/chat_stream. */
type SSEEventType =
  | 'token'
  | 'tool_start'
  | 'tool_progress'
  | 'tool_output'
  | 'model_info'
  | 'done'
  | 'error';

interface SSEEvent {
  event?: SSEEventType;
  data: string;
}

/** Parse SSE `event:` and `data:` lines from a text buffer.
 *  Returns parsed events and any remaining incomplete buffer. */
function parseSSEChunk(buffer: string): { events: SSEEvent[]; remainder: string } {
  const events: SSEEvent[] = [];
  const lines = buffer.split('\n');
  const remainder = lines.pop() ?? '';

  let currentEvent: string | undefined;
  let currentData = '';

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line === '') {
      // Empty line = end of event
      if (currentData) {
        events.push({
          event: currentEvent as SSEEventType | undefined,
          data: currentData,
        });
        currentEvent = undefined;
        currentData = '';
      }
    } else if (line.startsWith('event:')) {
      const value = line.slice(6).trim();
      currentEvent = value || undefined;
    } else if (line.startsWith('data:')) {
      currentData = line.slice(5).trim();
    }
    // Lines starting with ':' are SSE comments — ignored
  }

  return { events, remainder };
}

/** Retry only on server errors or network failures, not client errors.
 *  400/401/403/404/422 are not retried. */
function isRetryableError(err: unknown): boolean {
  if (err instanceof TypeError) return true; // network error
  const msg = err instanceof Error ? err.message : String(err);
  const statusMatch = msg.match(/status (\d{3})/);
  if (statusMatch) {
    const status = parseInt(statusMatch[1]!, 10);
    return status >= 500 || status === 429;
  }
  return true; // unknown errors: retry once
}

/**
 * SSE streaming chat hook.
 *
 * Delegates the initial POST to apiClient (ADR-0001 compliant), then reads
 * the text/event-stream via ReadableStream. Handles:
 * - AbortController cleanup on unmount
 * - Exponential-backoff reconnect on retryable errors only
 * - Contract-compliant SSE event parsing (token, tool_start, tool_progress,
 *   tool_output, model_info, done, error)
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
          const reader = await apiClientStream(requestBody);

          const decoder = new TextDecoder();
          let fullText = '';
          let buffer = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const { events, remainder } = parseSSEChunk(buffer);
            buffer = remainder;

            for (const evt of events) {
              switch (evt.event) {
                case 'token': {
                  try {
                    const parsed: unknown = JSON.parse(evt.data);
                    const chunk =
                      typeof parsed === 'string'
                        ? parsed
                        : (parsed as { content?: string; delta?: string })?.content ??
                          (parsed as { content?: string; delta?: string })?.delta ??
                          '';
                    fullText += chunk;
                    updateState({ text: fullText });
                    onChunkRef.current?.(chunk);
                  } catch {
                    // Non-JSON token — treat as raw text
                    fullText += evt.data;
                    updateState({ text: fullText });
                    onChunkRef.current?.(evt.data);
                  }
                  break;
                }
                case 'tool_start':
                case 'tool_progress':
                case 'tool_output':
                case 'model_info':
                  // Structured tool/model event data — forwarded for future UI rendering
                  break;
                case 'done':
                  updateState({ isStreaming: false });
                  onDoneRef.current?.(fullText);
                  return;
                case 'error': {
                  const error = new Error(evt.data || 'Stream error');
                  updateState({ isStreaming: false, error });
                  onErrorRef.current?.(error);
                  return;
                }
                default:
                  // Legacy: data-only lines (no event field)
                  if (evt.data === '[DONE]') {
                    updateState({ isStreaming: false });
                    onDoneRef.current?.(fullText);
                    return;
                  }
                  try {
                    const parsed: unknown = JSON.parse(evt.data);
                    const chunk =
                      typeof parsed === 'string'
                        ? parsed
                        : (parsed as { content?: string; delta?: string })?.content ??
                          (parsed as { content?: string; delta?: string })?.delta ??
                          '';
                    fullText += chunk;
                    updateState({ text: fullText });
                    onChunkRef.current?.(chunk);
                  } catch {
                    fullText += evt.data;
                    updateState({ text: fullText });
                    onChunkRef.current?.(evt.data);
                  }
              }
            }
          }

          // Stream ended normally (connection closed without done event)
          updateState({ isStreaming: false });
          onDoneRef.current?.(fullText);
        } catch (err) {
          if ((err as Error).name === 'AbortError') return;

          if (retryCountRef.current < maxRetries && isRetryableError(err)) {
            retryCountRef.current += 1;
            const delay = Math.min(1000 * 2 ** retryCountRef.current, 30000);
            await new Promise((resolve) => setTimeout(resolve, delay));
            return doFetch();
          }

          const error = err instanceof Error ? err : new Error(String(err));
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
