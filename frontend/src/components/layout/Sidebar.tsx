import { NavLink } from "react-router-dom";
import { useState } from "react";
import Logo from "../ui/Logo";
import { AMBER, SURFACE, SURFACE2, BORDER, TEXT_DIM, TEXT_MID, SKILLS, CLIENTS } from "../../design/tokens";
import type { SkillId, ClientId } from "../../design/tokens";
import type { HistoryEntry } from "../../hooks/useQueryHistory";

interface SidebarProps {
  activeSkill: SkillId;
  setSkill: (s: SkillId) => void;
  activeClient: ClientId;
  setClient: (c: ClientId) => void;
  history: HistoryEntry[];
  onHistoryClick: (q: string) => void;
  onHistoryDelete: (ts: number) => void;
  onNewChat: () => void;
  onLogout?: () => void;
  devMode: boolean;
}

function HistoryItem({
  entry,
  onClick,
  onDelete,
}: {
  entry: HistoryEntry;
  onClick: () => void;
  onDelete: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        padding: "6px 8px",
        borderRadius: 5,
        cursor: "pointer",
        marginBottom: 2,
        background: hovered ? SURFACE2 : "transparent",
        display: "flex",
        alignItems: "flex-start",
        gap: 4,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 10, color: TEXT_MID, lineHeight: 1.3, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {entry.q}
        </div>
        <div style={{ fontSize: 9, color: TEXT_DIM }}>{entry.t}</div>
      </div>
      {hovered && (
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: TEXT_DIM,
            fontSize: 12,
            lineHeight: 1,
            padding: "1px 2px",
            flexShrink: 0,
          }}
          title="Remove"
        >
          ×
        </button>
      )}
    </div>
  );
}

const NAV_ITEMS = [
  { to: "/chat", icon: "◈", label: "Chat" },
  { to: "/ingest", icon: "↑", label: "Ingest Data" },
  { to: "/collections", icon: "⊞", label: "Collections" },
  { to: "/feedback", icon: "◇", label: "Feedback" },
];

export default function Sidebar({
  activeSkill,
  setSkill,
  activeClient,
  setClient,
  history,
  onHistoryClick,
  onHistoryDelete,
  onNewChat,
  onLogout,
  devMode,
}: SidebarProps) {
  return (
    <div
      style={{
        width: 220,
        minWidth: 220,
        background: SURFACE,
        borderRight: `1px solid ${BORDER}`,
        display: "flex",
        flexDirection: "column",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* Logo */}
      <div style={{ padding: "18px 16px 14px", borderBottom: `1px solid ${BORDER}` }}>
        <Logo />
      </div>

      {/* New Chat */}
      <div style={{ padding: "10px 14px 6px" }}>
        <button
          onClick={onNewChat}
          style={{
            width: "100%",
            padding: "7px 10px",
            borderRadius: 6,
            border: `1px solid ${AMBER}55`,
            background: `${AMBER}10`,
            color: AMBER,
            fontSize: 10,
            fontFamily: "'Syne', sans-serif",
            fontWeight: 600,
            letterSpacing: "0.08em",
            cursor: "pointer",
            textAlign: "left" as const,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span style={{ fontSize: 14 }}>+</span> NEW CHAT
        </button>
      </div>

      {/* Client selector */}
      <div style={{ padding: "12px 14px 8px" }}>
        <div style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", marginBottom: 6 }}>
          CLIENT
        </div>
        <select
          value={activeClient}
          onChange={(e) => setClient(e.target.value as ClientId)}
          disabled={!devMode}
          style={{
            width: "100%",
            background: SURFACE2,
            border: `1px solid ${BORDER}`,
            color: TEXT_MID,
            borderRadius: 6,
            padding: "6px 8px",
            fontSize: 11,
            fontFamily: "'Syne', sans-serif",
            cursor: devMode ? "pointer" : "default",
            outline: "none",
            opacity: devMode ? 1 : 0.6,
          }}
        >
          {CLIENTS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      {/* Navigation */}
      <div style={{ padding: "4px 8px" }}>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            style={({ isActive }) => ({
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 10px",
              borderRadius: 6,
              border: "none",
              cursor: "pointer",
              textAlign: "left" as const,
              background: isActive ? `${AMBER}12` : "transparent",
              color: isActive ? AMBER : TEXT_MID,
              fontSize: 11,
              fontFamily: "'Syne', sans-serif",
              fontWeight: 500,
              marginBottom: 2,
              textDecoration: "none",
            })}
          >
            <span style={{ fontSize: 13, width: 16 }}>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>

      {/* Skill selector */}
      <div
        style={{
          padding: "10px 14px 6px",
          borderTop: `1px solid ${BORDER}`,
          marginTop: 4,
        }}
      >
        <div style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", marginBottom: 8 }}>
          SKILL / ACCESS LEVEL
        </div>
        {SKILLS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSkill(s.id)}
            disabled={!devMode}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "5px 8px",
              borderRadius: 5,
              border: "none",
              cursor: devMode ? "pointer" : "default",
              background: activeSkill === s.id ? `${s.color}15` : "transparent",
              color: activeSkill === s.id ? s.color : TEXT_DIM,
              fontSize: 10,
              fontFamily: "'Syne', sans-serif",
              marginBottom: 1,
            }}
          >
            <span style={{ fontSize: 12, color: s.color }}>{s.icon}</span>
            {s.label}
            {activeSkill === s.id && (
              <span style={{ marginLeft: "auto", fontSize: 8, color: s.color }}>●</span>
            )}
          </button>
        ))}
      </div>

      {/* Recent queries */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "10px 14px 6px",
          borderTop: `1px solid ${BORDER}`,
          marginTop: 4,
        }}
      >
        <div style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", marginBottom: 8 }}>
          RECENT
        </div>
        {history.length === 0 && (
          <div style={{ fontSize: 10, color: TEXT_DIM, padding: "4px 8px" }}>No recent queries</div>
        )}
        {history.map((h, i) => (
          <HistoryItem
            key={h.ts}
            entry={h}
            onClick={() => onHistoryClick(h.q)}
            onDelete={() => onHistoryDelete(h.ts)}
          />
        ))}
      </div>

      {/* User */}
      <div
        style={{
          padding: "10px 14px",
          borderTop: `1px solid ${BORDER}`,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}
      >
        <div
          style={{
            width: 26,
            height: 26,
            borderRadius: "50%",
            background: `${AMBER}22`,
            border: `1px solid ${AMBER}44`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 10,
            color: AMBER,
            fontWeight: 700,
          }}
        >
          R
        </div>
        <div>
          <div style={{ fontSize: 10, color: TEXT_MID, fontWeight: 600 }}>Ranjan Jaiswal</div>
          <div style={{ fontSize: 9, color: TEXT_DIM }}>Machine Learning Engineer</div>
        </div>
        {onLogout && (
          <button
            onClick={onLogout}
            title="Sign out"
            style={{
              marginLeft: "auto",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              color: TEXT_DIM,
              fontSize: 14,
              lineHeight: 1,
              padding: 2,
            }}
          >
            ⏻
          </button>
        )}
      </div>
    </div>
  );
}
