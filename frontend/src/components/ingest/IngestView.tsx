import DropZone from "./DropZone";
import JobQueue from "./JobQueue";
import ErrorBanner from "../ui/ErrorBanner";
import { TEXT_DIM, TEXT } from "../../design/tokens";
import { useIngest } from "../../hooks/useIngest";
import type { CollectionId } from "../../design/tokens";

interface IngestViewProps {
  token: string | null;
  clientId: string;
}

export default function IngestView({ token, clientId }: IngestViewProps) {
  const { documents, uploadQueue, isLoading, error, upload, remove, clearError } = useIngest(
    token,
    clientId
  );

  const handleUpload = (file: File, collection: CollectionId) => {
    upload(file, collection);
  };

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 28px" }}>
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 28,
            color: TEXT,
            marginBottom: 4,
          }}
        >
          Ingest Data
        </div>
        <div style={{ fontSize: 12, color: TEXT_DIM }}>
          Upload documents to build Argus's knowledge base. Files are chunked, embedded, and stored
          in pgvector + Neo4j.
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={clearError} />}

      <DropZone onUpload={handleUpload} isUploading={isLoading} />

      <JobQueue
        uploadQueue={uploadQueue}
        documents={documents}
        onDelete={remove}
      />
    </div>
  );
}
