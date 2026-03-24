import { SURFACE2, BORDER, TEXT_MID, TEXT_DIM, COLLECTIONS } from "../../design/tokens";
import type { CollectionId } from "../../design/tokens";

interface CollectionPickerProps {
  value: CollectionId;
  onChange: (c: CollectionId) => void;
}

export default function CollectionPicker({ value, onChange }: CollectionPickerProps) {
  return (
    <div>
      <div style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", marginBottom: 6 }}>
        TARGET COLLECTION
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as CollectionId)}
        style={{
          width: "100%",
          background: SURFACE2,
          border: `1px solid ${BORDER}`,
          color: TEXT_MID,
          borderRadius: 6,
          padding: "8px 10px",
          fontSize: 11,
          fontFamily: "'Syne', sans-serif",
          cursor: "pointer",
          outline: "none",
        }}
      >
        {COLLECTIONS.map((c) => (
          <option key={c.id} value={c.id}>
            {c.label}
          </option>
        ))}
      </select>
    </div>
  );
}
