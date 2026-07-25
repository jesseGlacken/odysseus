import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

/**
 * List emails for the configured email account.
 * Maps to GET /api/email/list.
 */
export function useEmails(params?: {
  account?: string;
  folder?: string;
  offset?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['email', 'list', params],
    queryFn: () =>
      apiClient.GET('/api/email/list', {
        params: {
          query: {
            account: params?.account,
            folder: params?.folder,
            offset: params?.offset,
            limit: params?.limit,
          },
        },
      } as never).then((res) => {
        if (!res.response.ok) throw new Error(`Email list fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Get email contacts.
 * Maps to GET /api/email/contacts.
 */
export function useEmailContacts() {
  return useQuery({
    queryKey: ['email', 'contacts'],
    queryFn: () =>
      apiClient.GET('/api/email/contacts').then((res) => {
        if (!res.response.ok) throw new Error(`Email contacts fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Search emails server-side.
 * Maps to GET /api/email/search.
 */
export function useSearchEmails(params?: {
  q?: string;
  account?: string;
  folder?: string;
  offset?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: ['email', 'search', params],
    queryFn: () =>
      apiClient.GET('/api/email/search', {
        params: {
          query: {
            q: params?.q,
            account: params?.account,
            folder: params?.folder,
            offset: params?.offset,
            limit: params?.limit,
          },
        },
      } as never).then((res) => {
        if (!res.response.ok) throw new Error(`Email search failed: ${res.response.status}`);
        return res.data;
      }),
    enabled: !!params?.q,
  });
}

/**
 * Read a single email by UID.
 * Maps to GET /api/email/read/{uid}.
 */
export function useReadEmail(uid: string | undefined) {
  return useQuery({
    queryKey: ['email', 'read', uid],
    queryFn: () =>
      apiClient.GET('/api/email/read/{uid}', {
        params: { path: { uid: uid! } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Email read failed: ${res.response.status}`);
        return res.data;
      }),
    enabled: !!uid,
  });
}

/**
 * Get unread state for email accounts.
 * Maps to GET /api/email/unread-state.
 */
export function useUnreadState() {
  return useQuery({
    queryKey: ['email', 'unread-state'],
    queryFn: () =>
      apiClient.GET('/api/email/unread-state').then((res) => {
        if (!res.response.ok) throw new Error(`Unread state fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Mark an email as read.
 * Maps to POST /api/email/mark-read/{uid}.
 */
export function useMarkRead() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uid: string) =>
      apiClient.POST('/api/email/mark-read/{uid}', {
        params: { path: { uid } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Mark read failed: ${res.response.status}`);
        return res.data;
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email'] });
    },
  });
}

/**
 * Delete an email (move to Trash).
 * Maps to DELETE /api/email/delete/{uid}.
 */
export function useDeleteEmail() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (uid: string) =>
      apiClient.DELETE('/api/email/delete/{uid}', {
        params: { path: { uid } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Email delete failed: ${res.response.status}`);
        return res.data;
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['email'] });
    },
  });
}
