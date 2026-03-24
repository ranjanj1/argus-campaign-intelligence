import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";
import StreamingBubble from "./StreamingBubble";
import SuggestionChips from "./SuggestionChips";
import ChatInput from "./ChatInput";
import ErrorBanner from "../ui/ErrorBanner";
import Badge from "../ui/Badge";
import { AMBER, SURFACE, BORDER, TEXT_DIM, COLLECTIONS, SKILLS } from "../../design/tokens";
import { useChat } from "../../hooks/useChat";
import { useQueryHistory } from "../../hooks/useQueryHistory";
import type { SkillId, ClientId } from "../../design/tokens";
import { useState } from "react";

interface ChatViewProps {
  token: string | null;
  skill: SkillId;
  clientId: ClientId;
  onSendQuery: (q: string) => void;
  pendingQuery?: string;
  onPendingQueryConsumed: () => void;
}

export default function ChatView({ token, skill, clientId, onSendQuery, pendingQuery, onPendingQueryConsumed }: ChatViewProps) {
  const { messages, streamingText, isStreaming, error, send, clearHistory } = useChat(token, skill, clientId);
  const [input, setInput] = useState("");
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (pendingQuery && !isStreaming) {
      onSendQuery(pendingQuery);
      send(pendingQuery);
      onPendingQueryConsumed();
    }
  }, [pendingQuery]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  const handleSend = () => {
    if (!input.trim()) return;
    const q = input.trim();
    setInput("");
    onSendQuery(q);
    send(q);
  };

  const handleSuggestion = (s: string) => {
    onSendQuery(s);
    send(s);
  };

  const activeSkillLabel = SKILLS.find((s) => s.id === skill)?.label ?? skill;

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      {/* Top bar */}
      <div
        style={{
          padding: "12px 20px",
          borderBottom: `1px solid ${BORDER}`,
          display: "flex",
          alignItems: "center",
          gap: 12,
          background: SURFACE,
          flexShrink: 0,
        }}
      >
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, color: TEXT_DIM }}>
            <span style={{ color: AMBER }}>◈</span> {activeSkillLabel}
            <span style={{ color: BORDER, margin: "0 8px" }}>|</span>
            {clientId.replace(/_/g, " ")}
          </div>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          {COLLECTIONS.slice(0, 4).map((c) => (
            <Badge key={c.id} color={c.color}>
              {c.label.split(" ")[0]}
            </Badge>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#10B981",
              animation: "pulse 2s ease-in-out infinite",
            }}
          />
          <span style={{ fontSize: 9, color: "#10B981", letterSpacing: "0.08em" }}>LIVE</span>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            style={{
              background: "transparent",
              border: `1px solid ${BORDER}`,
              borderRadius: 6,
              padding: "3px 8px",
              cursor: "pointer",
              fontSize: 9,
              color: TEXT_DIM,
              fontFamily: "'Syne', sans-serif",
            }}
          >
            CLEAR
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "24px 20px 12px" }}>
        {error && (
          <ErrorBanner message={error} />
        )}
        {messages.length === 0 && !isStreaming && (
          <SuggestionChips onSelect={handleSuggestion} />
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} msg={msg} />
        ))}
        {isStreaming && <StreamingBubble text={streamingText} />}
        <div ref={messagesEnd} />
      </div>

      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={isStreaming}
      />
    </div>
  );
}
