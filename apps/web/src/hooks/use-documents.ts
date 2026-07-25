import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@odysseus/client-sdk';

/**
 * List all documents in the library.
 * Maps to GET /api/documents/library.
 */
export function useDocumentsLibrary() {
  return useQuery({
    queryKey: ['documents', 'library'],
    queryFn: () =>
      apiClient.GET('/api/documents/library').then((res) => {
        if (!res.response.ok) throw new Error(`Documents library fetch failed: ${res.response.status}`);
        return res.data;
      }),
  });
}

/**
 * List documents for a specific session.
 * Maps to GET /api/documents/{session_id}.
 */
export function useDocuments(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['documents', sessionId],
    queryFn: () =>
      apiClient.GET('/api/documents/{session_id}', {
        params: { path: { session_id: sessionId! } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Documents fetch failed: ${res.response.status}`);
        return res.data;
      }),
    enabled: !!sessionId,
  });
}

/**
 * Get a single document by ID.
 * Maps to GET /api/document/{doc_id}.
 */
export function useDocument(docId: string | undefined) {
  return useQuery({
    queryKey: ['document', docId],
    queryFn: () =>
      apiClient.GET('/api/document/{doc_id}', {
        params: { path: { doc_id: docId! } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Document fetch failed: ${res.response.status}`);
        return res.data;
      }),
    enabled: !!docId,
  });
}

/**
 * Create a new document.
 * Maps to POST /api/document.
 */
export function useCreateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (body: {
      title: string;
      content: string;
      session_id?: string;
    }) =>
      apiClient
        .POST('/api/document', {
          body: {
            title: body.title,
            content: body.content,
            session_id: body.session_id ?? '',
          },
        } as never)
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Upload a file.
 * Maps to POST /api/upload.
 */
export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formData: FormData) =>
      apiClient
        .POST('/api/upload', {
          body: formData,
          bodySerializer: (b: unknown) => b as BodyInit,
        } as never)
        .then((res) => {
          if (res.error) throw res.error;
          return res.data;
        }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Delete a document by ID.
 * Maps to DELETE /api/document/{doc_id}.
 */
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (docId: string) =>
      apiClient.DELETE('/api/document/{doc_id}', {
        params: { path: { doc_id: docId } },
      }).then((res) => {
        if (!res.response.ok) throw new Error(`Document delete failed: ${res.response.status}`);
        return res.data;
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

/**
 * Update a document by ID.
 * Maps to PUT /api/document/{doc_id}.
 */
export function useUpdateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      docId,
      body,
    }: {
      docId: string;
      body: { title?: string; content?: string };
    }) =>
      apiClient.PUT('/api/document/{doc_id}', {
        params: { path: { doc_id: docId } },
        body: {
          content: body.content ?? '',
          force_version: false,
        },
      }).then((res) => {
        if (res.error) throw res.error;
        return res.data;
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['document', variables.docId],
      });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}
