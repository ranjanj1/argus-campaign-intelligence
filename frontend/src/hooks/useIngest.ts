import { useCallback, useEffect, useRef, useState } from "react";
import { uploadFile, listDocuments, deleteDocument } from "../api/ingest";
import type { DocumentListItem, UploadJob } from "../api/types";

const POLL_MS = 5000;

export function useIngest(token: string | null, clientId: string) {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [uploadQueue, setUploadQueue] = useState<UploadJob[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await listDocuments(token);
      setDocuments(data.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents");
    }
  }, [token]);

  // Initial load + periodic polling
  useEffect(() => {
    fetchDocuments();
    pollRef.current = setInterval(fetchDocuments, POLL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchDocuments]);

  const upload = useCallback(
    async (file: File, collection: string) => {
      const localId = `${Date.now()}-${file.name}`;
      const newJob: UploadJob = {
        localId,
        filename: file.name,
        collection,
        status: "uploading",
        startedAt: Date.now(),
      };
      setUploadQueue((prev) => [newJob, ...prev]);
      setError(null);

      try {
        setIsLoading(true);
        const result = await uploadFile(file, collection, clientId, token);
        setUploadQueue((prev) =>
          prev.map((j) =>
            j.localId === localId
              ? { ...j, status: "queued", doc_id: result.job_id }
              : j
          )
        );
        // Refresh document list immediately after upload
        await fetchDocuments();
      } catch (err) {
        setUploadQueue((prev) =>
          prev.map((j) =>
            j.localId === localId
              ? { ...j, status: "error", error: err instanceof Error ? err.message : "Upload failed" }
              : j
          )
        );
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setIsLoading(false);
      }
    },
    [clientId, token, fetchDocuments]
  );

  const remove = useCallback(
    async (docId: string) => {
      try {
        await deleteDocument(docId, token);
        setDocuments((prev) => prev.filter((d) => d.doc_id !== docId));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      }
    },
    [token]
  );

  const clearError = useCallback(() => setError(null), []);

  return { documents, uploadQueue, isLoading, error, upload, remove, clearError };
}
