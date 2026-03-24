import { useRef } from "react";
import { AMBER, SURFACE, SURFACE2, BORDER, TEXT_DIM } from "../../design/tokens";

interface ChatInputProps {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  disabled: boolean;
}

export default function ChatInput({ value, onChange, onSend, disabled }: ChatInputProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div
      style={{
        padding: "12px 20px 16px",
        borderTop: `1px solid ${BORDER}`,
        background: SURFACE,
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 10,
          background: SURFACE2,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: "4px 4px 4px 16px",
          transition: "border-color .2s",
        }}
        onFocusCapture={(e) => (e.currentTarget.style.borderColor = `${AMBER}44`)}
        onBlurCapture={(e) => (e.currentTarget.style.borderColor = BORDER)}
      >
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder="Ask about any campaign, audience, or performance metric..."
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "#E8E4D9",
            fontSize: 13,
            fontFamily: "'Syne', sans-serif",
            padding: "10px 0",
            opacity: disabled ? 0.5 : 1,
          }}
        />
        <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "4px 4px" }}>
          <button
            onClick={onSend}
            disabled={!value.trim() || disabled}
            style={{
              background: value.trim() && !disabled ? AMBER : BORDER,
              border: "none",
              borderRadius: 8,
              padding: "8px 16px",
              cursor: value.trim() && !disabled ? "pointer" : "default",
              color: value.trim() && !disabled ? "#080C14" : TEXT_DIM,
              fontSize: 11,
              fontWeight: 700,
              fontFamily: "'Syne', sans-serif",
              transition: "all .15s",
              letterSpacing: "0.06em",
            }}
          >
            SEND
          </button>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, marginTop: 8, padding: "0 4px" }}>
        <span style={{ fontSize: 9, color: TEXT_DIM }}>Enter to send · Shift+Enter for newline</span>
        <span style={{ fontSize: 9, color: TEXT_DIM, marginLeft: "auto" }}>
          GPT-4o · nomic-embed · pgvector + Neo4j
        </span>
      </div>
    </div>
  );
}
