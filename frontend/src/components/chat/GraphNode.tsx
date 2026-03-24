import { AMBER, SURFACE2, BORDER, TEXT_DIM } from "../../design/tokens";

interface GraphNodeProps {
  text: string;
}

export default function GraphNode({ text }: GraphNodeProps) {
  const parts = text.split("→").map((p) => p.trim());

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        flexWrap: "wrap",
        padding: "8px 12px",
        background: SURFACE2,
        borderRadius: 8,
        border: `1px solid ${BORDER}`,
        marginBottom: 6,
      }}
    >
      {parts.map((p, i) => (
        <span key={i} style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <span
            style={{
              background: `${AMBER}15`,
              border: `1px solid ${AMBER}33`,
              borderRadius: 4,
              padding: "2px 8px",
              fontSize: 9,
              color: AMBER,
              fontWeight: 600,
            }}
          >
            {p}
          </span>
          {i < parts.length - 1 && (
            <span style={{ color: TEXT_DIM, fontSize: 10 }}>→</span>
          )}
        </span>
      ))}
    </div>
  );
}
