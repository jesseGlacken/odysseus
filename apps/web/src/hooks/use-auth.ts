import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

/**
 * Fetch the current auth status (logged-in user, admin flag, etc.).
 * Maps to GET /api/auth/status.
 */
export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: () =>
      apiClient.GET('/api/auth/status').then((res) => {
        if (!res.response.ok) throw new Error(`Auth status failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Login with username + password (+ optional TOTP).
 * Maps to POST /api/auth/login.
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      username: string;
      password: string;
      remember?: boolean;
      totp_code?: string;
    }) =>
      apiClient
        .POST('/api/auth/login', {
          body: {
            username: body.username,
            password: body.password,
            remember: body.remember ?? true,
            totp_code: body.totp_code ?? null,
          },
        })
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
}

/**
 * Logout the current session.
 * Maps to POST /api/auth/logout.
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () =>
      apiClient.POST('/api/auth/logout').then((res) => {
        if (!res.response.ok) throw new Error(`Logout failed: ${res.response.status}`);
        return res.data;
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
}

/**
 * First-run setup — create the initial admin account.
 * Maps to POST /api/auth/setup.
 */
export function useSetup() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: { username: string; password: string }) =>
      apiClient
        .POST('/api/auth/setup', {
          body: {
            username: body.username,
            password: body.password,
          },
        })
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
  });
}

/**
 * Request a password change for the authenticated user.
 * Maps to POST /api/auth/change-password.
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (body: {
      current_password: string;
      new_password: string;
    }) =>
      apiClient
        .POST('/api/auth/change-password', {
          body: {
            current_password: body.current_password,
            new_password: body.new_password,
          },
        })
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
  });
}
