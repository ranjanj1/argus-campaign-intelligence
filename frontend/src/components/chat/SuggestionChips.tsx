import { SURFACE2, BORDER, TEXT_MID, TEXT_DIM, AMBER } from "../../design/tokens";

const SUGGESTIONS = [
  "What ad copy had the highest CTR for SaaS clients?",
  "Compare Q2 vs Q3 ROAS across all channels",
  "Which campaigns had ROI > 4x under $50K budget?",
  "Best performing audience for Google Ads last quarter",
];

interface SuggestionChipsProps {
  onSelect: (s: string) => void;
}

export default function SuggestionChips({ onSelect }: SuggestionChipsProps) {
  return (
    <div style={{ textAlign: "center", paddingTop: 60 }}>
      <div
        style={{
          fontFamily: "'Instrument Serif', serif",
          fontSize: 32,
          color: TEXT_DIM,
          marginBottom: 8,
        }}
      >
        What do you want to know?
      </div>
      <div style={{ fontSize: 12, color: TEXT_DIM, marginBottom: 32 }}>
        Ask anything about your campaigns, audiences, or ad performance.
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          justifyContent: "center",
          maxWidth: 600,
          margin: "0 auto",
        }}
      >
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s)}
            style={{
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              borderRadius: 8,
              padding: "8px 14px",
              fontSize: 11,
              color: TEXT_MID,
              cursor: "pointer",
              fontFamily: "'Syne', sans-serif",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = `${AMBER}44`;
              e.currentTarget.style.color = "#E8E4D9";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = BORDER;
              e.currentTarget.style.color = TEXT_MID;
            }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
