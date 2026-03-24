// API types matching backend Pydantic models

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream: boolean;
}

export interface Source {
  index: number;
  source_file: string;
  collection: string;
  page: number | null;
  client_id: string;
  score: number;
  excerpt?: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  session_id: string;
}

// SSE event payloads
export type SSEEvent =
  | { type: "token"; token: string }
  | { type: "done"; response: ChatResponse }
  | { type: "error"; detail: string };

export interface EnqueueResponse {
  job_id: string;
  status: "queued" | "running" | "complete" | "error";
  filename: string;
  collection: string;
  client_id: string;
}

export interface DocumentListItem {
  doc_id: string;
  source_file: string;
  collection: string;
  ingested_at: string;
  chunk_count?: number;
}

export interface DocumentListResponse {
  client_id: string;
  count: number;
  documents: DocumentListItem[];
}

// Local upload queue entry (optimistic UI)
export interface UploadJob {
  localId: string;
  filename: string;
  collection: string;
  status: "uploading" | "queued" | "running" | "complete" | "error";
  doc_id?: string;
  error?: string;
  startedAt: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  graphNodes?: string[];
}
