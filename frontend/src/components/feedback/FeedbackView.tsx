import { TEXT_DIM } from "../../design/tokens";

export default function FeedbackView() {
  return (
    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ textAlign: "center", color: TEXT_DIM }}>
        <div
          style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 24,
            marginBottom: 8,
          }}
        >
          Feedback & Evals
        </div>
        <div style={{ fontSize: 12 }}>Thumbs up/down history · Langfuse eval dataset</div>
        <div style={{ fontSize: 11, marginTop: 16, opacity: 0.6 }}>
          Langfuse integration pending
        </div>
      </div>
    </div>
  );
}
