import Badge from "../ui/Badge";
import { AMBER, AMBER_DIM, SURFACE2, BORDER, TEXT_DIM, TEXT_BODY, COLLECTIONS } from "../../design/tokens";

interface StreamingBubbleProps {
  text: string;
}

export default function StreamingBubble({ text }: StreamingBubbleProps) {
  return (
    <div className="fade-up" style={{ marginBottom: 24, padding: "0 4px" }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 7,
            background: `${AMBER}20`,
            border: `1px solid ${AMBER}44`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            color: AMBER,
            flexShrink: 0,
            fontFamily: "'Instrument Serif', serif",
          }}
        >
          A
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: AMBER, letterSpacing: "0.06em" }}>
              ARGUS
            </span>
            <Badge color={AMBER_DIM}>streaming</Badge>
          </div>
          <div
            style={{
              background: SURFACE2,
              border: `1px solid ${AMBER}22`,
              borderRadius: "2px 12px 12px 12px",
              padding: "14px 16px",
              position: "relative",
              overflow: "hidden",
            }}
          >
            <div className="scan-overlay" />
            <span style={{ fontSize: 12, color: TEXT_BODY, lineHeight: 1.7 }}>{text}</span>
            <span
              style={{
                animation: "blink 1s step-end infinite",
                color: AMBER,
                fontSize: 14,
                marginLeft: 2,
              }}
            >
              |
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: TEXT_DIM, display: "flex", gap: 8 }}>
            <span>Searching {COLLECTIONS.length} collections</span>
            <span style={{ animation: "pulse 1s ease-in-out infinite" }}>◈</span>
            <span>Graph traversal active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
