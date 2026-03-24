import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Badge from "../ui/Badge";
import SourceCard from "./SourceCard";
import GraphNode from "./GraphNode";
import { AMBER, AMBER_DIM, SURFACE2, BORDER, TEXT_DIM, TEXT } from "../../design/tokens";
import type { Message } from "../../api/types";

interface MessageBubbleProps {
  msg: Message;
}

export default function MessageBubble({ msg }: MessageBubbleProps) {
  const isUser = msg.role === "user";
  const [showSources, setShowSources] = useState(false);
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.content).catch(() => {});
  };

  const handleFeedback = (val: "up" | "down") => {
    setFeedback(val);
    // Store locally for future Langfuse integration
    try {
      const stored = JSON.parse(localStorage.getItem("argus_feedback") ?? "[]");
      stored.push({ content: msg.content.slice(0, 100), rating: val, ts: Date.now() });
      localStorage.setItem("argus_feedback", JSON.stringify(stored.slice(-100)));
    } catch { /* ignore */ }
  };

  if (isUser) {
    return (
      <div
        className="fade-up"
        style={{ display: "flex", justifyContent: "flex-end", marginBottom: 20, padding: "0 4px" }}
      >
        <div
          style={{
            maxWidth: "70%",
            background: `${AMBER}15`,
            border: `1px solid ${AMBER}2A`,
            borderRadius: "12px 12px 2px 12px",
            padding: "10px 14px",
          }}
        >
          <div style={{ fontSize: 12, color: TEXT, lineHeight: 1.6 }}>{msg.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-up" style={{ marginBottom: 24, padding: "0 4px" }}>
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: 8 }}>
        {/* Avatar */}
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

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span style={{ fontSize: 10, fontWeight: 700, color: AMBER, letterSpacing: "0.06em" }}>
              ARGUS
            </span>
            <Badge color="#10B981">grounded</Badge>
            {msg.sources && <Badge color={TEXT_DIM}>{msg.sources.length} sources</Badge>}
          </div>

          {/* Message content via react-markdown — no dangerouslySetInnerHTML */}
          <div
            className="md-content"
            style={{
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              borderRadius: "2px 12px 12px 12px",
              padding: "14px 16px",
            }}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
          </div>

          {/* Sources toggle */}
          {msg.sources && msg.sources.length > 0 && (
            <button
              onClick={() => setShowSources(!showSources)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginTop: 8,
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: TEXT_DIM,
                fontSize: 10,
                fontFamily: "'Syne', sans-serif",
                padding: "4px 0",
              }}
            >
              <span>{showSources ? "▾" : "▸"}</span>
              {showSources ? "Hide" : "Show"} {msg.sources.length} source citations
            </button>
          )}

          {showSources && msg.sources && (
            <div style={{ marginTop: 6 }}>
              {msg.graphNodes?.map((n, i) => <GraphNode key={i} text={n} />)}
              {msg.sources.map((s, i) => <SourceCard key={i} src={s} cardIndex={i} />)}
            </div>
          )}

          {/* Feedback */}
          <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
            {(["👍", "👎"] as const).map((e, i) => {
              const val = i === 0 ? "up" : "down";
              return (
                <button
                  key={e}
                  onClick={() => handleFeedback(val as "up" | "down")}
                  style={{
                    background: feedback === val ? `${AMBER}20` : SURFACE2,
                    border: `1px solid ${feedback === val ? AMBER + "44" : BORDER}`,
                    borderRadius: 6,
                    padding: "3px 8px",
                    cursor: "pointer",
                    fontSize: 11,
                    color: TEXT_DIM,
                  }}
                >
                  {e}
                </button>
              );
            })}
            <button
              onClick={handleCopy}
              style={{
                background: SURFACE2,
                border: `1px solid ${BORDER}`,
                borderRadius: 6,
                padding: "3px 10px",
                cursor: "pointer",
                fontSize: 9,
                color: TEXT_DIM,
                fontFamily: "'Syne', sans-serif",
                letterSpacing: "0.06em",
              }}
            >
              COPY
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
