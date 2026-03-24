import { apiFetch } from "./client";
import type { EnqueueResponse, DocumentListResponse } from "./types";

/**
 * Upload a file for ingestion.
 * Uses FormData — do NOT set Content-Type manually (browser sets boundary automatically).
 */
export async function uploadFile(
  file: File,
  collection: string,
  clientId: string,
  token: string | null
): Promise<EnqueueResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("collection", collection);
  form.append("client_id", clientId);

  const res = await apiFetch(
    "/v1/ingest/file",
    { method: "POST", body: form },
    token
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
    throw new Error(err.detail ?? `Upload failed (${res.status})`);
  }
  return res.json();
}

/**
 * List ingested documents for the current client.
 * Optionally filter by collection.
 */
export async function listDocuments(
  token: string | null,
  collection?: string
): Promise<DocumentListResponse> {
  const qs = collection ? `?collection=${encodeURIComponent(collection)}` : "";
  const res = await apiFetch(`/v1/ingest/list${qs}`, {}, token);
  if (!res.ok) {
    throw new Error(`Failed to fetch document list (${res.status})`);
  }
  return res.json();
}

/**
 * Delete a document and all its chunks.
 */
export async function deleteDocument(
  docId: string,
  token: string | null
): Promise<void> {
  const res = await apiFetch(`/v1/ingest/${encodeURIComponent(docId)}`, { method: "DELETE" }, token);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
    throw new Error(err.detail ?? `Delete failed (${res.status})`);
  }
}
