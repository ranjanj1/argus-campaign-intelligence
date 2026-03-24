import { AMBER, TEXT_DIM, TEXT } from "../../design/tokens";

export default function Logo() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: 8,
          background: `linear-gradient(135deg, ${AMBER}22, ${AMBER}44)`,
          border: `1px solid ${AMBER}44`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 16,
          color: AMBER,
          fontWeight: 800,
          fontFamily: "'Instrument Serif', serif",
        }}
      >
        A
      </div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.08em", color: TEXT }}>
          ARGUS
        </div>
        <div style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", marginTop: -2 }}>
          CAMPAIGN INTELLIGENCE
        </div>
      </div>
    </div>
  );
}
