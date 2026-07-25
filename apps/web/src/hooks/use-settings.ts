import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

/**
 * Get app settings.
 * Admins get the full set; non-admins get a scrubbed copy.
 * Maps to GET /api/auth/settings.
 */
export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () =>
      apiClient.GET('/api/auth/settings').then((res) => {
        if (!res.response.ok) throw new Error(`Settings fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Update app settings (admin only).
 * Maps to POST /api/auth/settings.
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiClient
        .POST('/api/auth/settings', {
          body,
        } as never)
        .then((res) => {
          if (!res.response.ok) throw new Error(`Settings update failed: ${res.response.status}`);
          return res.data;
        }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });
}

/**
 * Get public auth policy constants.
 * Maps to GET /api/auth/policy.
 */
export function useAuthPolicy() {
  return useQuery({
    queryKey: ['auth', 'policy'],
    queryFn: () =>
      apiClient.GET('/api/auth/policy').then((res) => {
        if (!res.response.ok) throw new Error(`Auth policy fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * Get feature toggles.
 * Maps to GET /api/auth/features.
 */
export function useFeatures() {
  return useQuery({
    queryKey: ['features'],
    queryFn: () =>
      apiClient.GET('/api/auth/features').then((res) => {
        if (!res.response.ok) throw new Error(`Features fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}
