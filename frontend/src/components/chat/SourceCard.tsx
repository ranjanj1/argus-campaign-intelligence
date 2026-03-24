import Badge from "../ui/Badge";
import { SURFACE2, BORDER, TEXT_MID, TEXT_DIM, AMBER, COLLECTIONS } from "../../design/tokens";
import type { Source } from "../../api/types";

function fileIcon(filename: string): string {
  if (filename.endsWith(".pdf")) return "📄";
  if (filename.endsWith(".xlsx") || filename.endsWith(".csv")) return "📊";
  return "📋";
}

interface SourceCardProps {
  src: Source;
  cardIndex: number;
}

export default function SourceCard({ src, cardIndex }: SourceCardProps) {
  const collColor = COLLECTIONS.find((c) => c.id === src.collection)?.color ?? AMBER;
  // score is typically 0.01–0.10 range from RRF; normalise to 0–1 for display
  const displayScore = Math.min(src.score * 10, 1);

  return (
    <div
      className="slide-in"
      style={{
        animationDelay: `${cardIndex * 0.08}s`,
        opacity: 0,
        background: SURFACE2,
        border: `1px solid ${BORDER}`,
        borderRadius: 8,
        padding: "10px 12px",
        marginBottom: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 6 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            background: `${collColor}15`,
            border: `1px solid ${collColor}33`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 12,
            flexShrink: 0,
          }}
        >
          {fileIcon(src.source_file)}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 10,
              color: TEXT_MID,
              fontWeight: 600,
              marginBottom: 2,
              wordBreak: "break-all",
            }}
          >
            {src.source_file}
          </div>
          {src.page != null && (
            <div style={{ fontSize: 9, color: TEXT_DIM }}>Page {src.page}</div>
          )}
        </div>
      </div>

      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        <Badge color={collColor}>{src.collection.replace(/_/g, " ")}</Badge>
        <Badge color={TEXT_DIM}>{src.client_id}</Badge>
        <Badge color="#10B981">score {src.score.toFixed(4)}</Badge>
      </div>

      {src.excerpt && (
        <div
          style={{
            fontSize: 10,
            color: TEXT_DIM,
            marginTop: 8,
            lineHeight: 1.5,
            borderLeft: `2px solid ${collColor}44`,
            paddingLeft: 8,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          {src.excerpt}
        </div>
      )}

      <div style={{ marginTop: 8 }}>
        <div style={{ fontSize: 9, color: TEXT_DIM, marginBottom: 3 }}>RELEVANCE</div>
        <div style={{ height: 3, background: BORDER, borderRadius: 2, overflow: "hidden" }}>
          <div
            style={{
              height: "100%",
              width: `${displayScore * 100}%`,
              borderRadius: 2,
              background: `linear-gradient(90deg, ${collColor}88, ${collColor})`,
              animation: "grow .6s ease forwards",
            }}
          />
        </div>
      </div>
    </div>
  );
}
