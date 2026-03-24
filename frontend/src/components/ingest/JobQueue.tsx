import Badge from "../ui/Badge";
import { AMBER, SURFACE2, BORDER, TEXT_MID, TEXT_DIM, COLLECTIONS } from "../../design/tokens";
import type { DocumentListItem, UploadJob } from "../../api/types";

const STATUS_COLOR: Record<string, string> = {
  done: "#10B981",
  complete: "#10B981",
  running: AMBER,
  queued: "#3B82F6",
  uploading: AMBER,
  pending: TEXT_DIM,
  error: "#EF4444",
};

const STATUS_ICON: Record<string, string> = {
  done: "✓",
  complete: "✓",
  running: "◈",
  queued: "◈",
  uploading: "◈",
  pending: "○",
  error: "✕",
};

function elapsedLabel(ts: number): string {
  const s = Math.floor((Date.now() - ts) / 1000);
  if (s < 60) return `${s}s ago`;
  return `${Math.floor(s / 60)}m ago`;
}

interface JobQueueProps {
  uploadQueue: UploadJob[];
  documents: DocumentListItem[];
  onDelete: (docId: string) => void;
}

export default function JobQueue({ uploadQueue, documents, onDelete }: JobQueueProps) {
  const isEmpty = uploadQueue.length === 0 && documents.length === 0;

  return (
    <div>
      <div style={{ fontSize: 11, color: TEXT_DIM, letterSpacing: "0.1em", marginBottom: 12 }}>
        INGEST QUEUE
      </div>

      {isEmpty && (
        <div style={{ fontSize: 12, color: TEXT_DIM, padding: "20px 0", textAlign: "center" }}>
          No documents ingested yet. Upload a file above to get started.
        </div>
      )}

      {/* Active upload jobs (optimistic) */}
      {uploadQueue.map((job) => {
        const color = STATUS_COLOR[job.status] ?? TEXT_DIM;
        const icon = STATUS_ICON[job.status] ?? "○";
        const collColor = COLLECTIONS.find((c) => c.id === job.collection)?.color ?? AMBER;
        return (
          <div
            key={job.localId}
            style={{
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              borderRadius: 10,
              padding: "12px 16px",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                background: `${color}15`,
                border: `1px solid ${color}33`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color,
                fontSize: 12,
                flexShrink: 0,
                animation: ["uploading", "running", "queued"].includes(job.status)
                  ? "pulse 1s ease-in-out infinite"
                  : "none",
              }}
            >
              {icon}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: TEXT_MID, fontWeight: 600, marginBottom: 2 }}>
                {job.filename}
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Badge color={collColor}>{job.collection}</Badge>
                {job.error && (
                  <span style={{ fontSize: 9, color: "#EF4444" }}>{job.error}</span>
                )}
              </div>
              {["uploading", "running"].includes(job.status) && (
                <div style={{ marginTop: 6, height: 2, background: BORDER, borderRadius: 1, overflow: "hidden" }}>
                  <div
                    style={{
                      height: "100%",
                      width: "60%",
                      borderRadius: 1,
                      background: AMBER,
                      backgroundImage: `linear-gradient(90deg, transparent, ${AMBER}, transparent)`,
                      backgroundSize: "200% 100%",
                      animation: "shimmer 1.5s infinite",
                    }}
                  />
                </div>
              )}
            </div>
            <div style={{ fontSize: 9, color: TEXT_DIM }}>{elapsedLabel(job.startedAt)}</div>
          </div>
        );
      })}

      {/* Completed documents from backend */}
      {documents.map((doc) => {
        const collColor = COLLECTIONS.find((c) => c.id === doc.collection)?.color ?? AMBER;
        return (
          <div
            key={doc.doc_id}
            style={{
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              borderRadius: 10,
              padding: "12px 16px",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                background: "#10B98115",
                border: "1px solid #10B98133",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#10B981",
                fontSize: 12,
                flexShrink: 0,
              }}
            >
              ✓
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 11, color: TEXT_MID, fontWeight: 600, marginBottom: 2 }}>
                {doc.source_file}
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Badge color={collColor}>{doc.collection}</Badge>
                {doc.chunk_count && (
                  <span style={{ fontSize: 9, color: TEXT_DIM }}>
                    {doc.chunk_count.toLocaleString()} chunks
                  </span>
                )}
              </div>
            </div>
            <div style={{ fontSize: 9, color: TEXT_DIM }}>
              {new Date(doc.ingested_at).toLocaleDateString()}
            </div>
            <button
              onClick={() => onDelete(doc.doc_id)}
              style={{
                background: "transparent",
                border: `1px solid ${BORDER}`,
                borderRadius: 6,
                padding: "4px 10px",
                cursor: "pointer",
                color: "#EF4444",
                fontSize: 9,
                fontFamily: "'Syne', sans-serif",
              }}
            >
              DELETE
            </button>
          </div>
        );
      })}
    </div>
  );
}
