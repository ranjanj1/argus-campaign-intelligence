import { SURFACE2, BORDER } from "../../design/tokens";

const RED = "#EF4444";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  return (
    <div
      className="fade-up"
      style={{
        background: `${RED}10`,
        border: `1px solid ${RED}33`,
        borderRadius: 8,
        padding: "10px 14px",
        display: "flex",
        alignItems: "flex-start",
        gap: 10,
        margin: "8px 0",
      }}
    >
      <span style={{ color: RED, fontSize: 13, flexShrink: 0 }}>✕</span>
      <span style={{ fontSize: 12, color: RED, flex: 1, lineHeight: 1.5 }}>{message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: "transparent",
            border: `1px solid ${BORDER}`,
            borderRadius: 4,
            padding: "2px 8px",
            cursor: "pointer",
            fontSize: 9,
            color: RED,
            fontFamily: "'Syne', sans-serif",
            flexShrink: 0,
          }}
        >
          DISMISS
        </button>
      )}
    </div>
  );
}
