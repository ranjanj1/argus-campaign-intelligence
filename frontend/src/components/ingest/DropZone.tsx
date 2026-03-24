import { useRef, useState } from "react";
import CollectionPicker from "./CollectionPicker";
import { AMBER, SURFACE2, BORDER, TEXT_MID, TEXT_DIM } from "../../design/tokens";
import type { CollectionId } from "../../design/tokens";

interface DropZoneProps {
  onUpload: (file: File, collection: CollectionId) => void;
  isUploading: boolean;
}

const ACCEPTED = ".pdf,.docx,.pptx,.csv,.xlsx,.md,.txt,.png,.jpg,.jpeg";

export default function DropZone({ onUpload, isUploading }: DropZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [collection, setCollection] = useState<CollectionId>("campaign_performance");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    Array.from(files).forEach((f) => onUpload(f, collection));
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ marginBottom: 12 }}>
        <CollectionPicker value={collection} onChange={setCollection} />
      </div>

      {/* Hidden file input — triggered by click on drop zone */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED}
        multiple
        style={{ display: "none" }}
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !isUploading && fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? AMBER : BORDER}`,
          borderRadius: 12,
          padding: "40px 24px",
          textAlign: "center",
          background: dragging ? `${AMBER}08` : SURFACE2,
          transition: "all .2s",
          cursor: isUploading ? "default" : "pointer",
          opacity: isUploading ? 0.6 : 1,
        }}
      >
        <div style={{ fontSize: 28, marginBottom: 12, color: dragging ? AMBER : TEXT_DIM }}>↑</div>
        <div style={{ fontSize: 14, color: TEXT_MID, marginBottom: 6, fontWeight: 600 }}>
          {isUploading ? "Uploading..." : "Drop files here or click to browse"}
        </div>
        <div style={{ fontSize: 11, color: TEXT_DIM }}>
          PDF · DOCX · PPTX · CSV · XLSX · MD · TXT · PNG · JPG
        </div>
      </div>
    </div>
  );
}
