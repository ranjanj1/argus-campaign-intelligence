import { useEffect, useState } from "react";
import Badge from "../ui/Badge";
import { AMBER, SURFACE2, BORDER, TEXT_MID, TEXT_DIM, TEXT, COLLECTIONS } from "../../design/tokens";
import { fetchCollectionStats } from "../../api/collections";
import type { CollectionsStatsResponse } from "../../api/collections";

export default function CollectionsView() {
  const [stats, setStats] = useState<CollectionsStatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCollectionStats()
      .then(setStats)
      .catch((err) => setError(err.message));
  }, []);

  // Build a lookup from collection id → vector count
  const countMap: Record<string, number> = {};
  if (stats) {
    for (const c of stats.collections) {
      countMap[c.id] = c.vector_count;
    }
  }

  const neo4j = stats?.neo4j;
  const maxCount = Math.max(...Object.values(countMap), 1);

  const neo4jRows = neo4j
    ? [
        [String(neo4j.entity_types), "Entity Types"],
        [String(neo4j.rel_types), "Rel. Types"],
        [String(neo4j.nodes), "Nodes"],
        [String(neo4j.edges), "Edges"],
      ]
    : [["—", "Entity Types"], ["—", "Rel. Types"], ["—", "Nodes"], ["—", "Edges"]];

  return (
    <div style={{ flex: 1, overflow: "auto", padding: "28px 28px" }}>
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            fontFamily: "'Instrument Serif', serif",
            fontSize: 28,
            color: TEXT,
            marginBottom: 4,
          }}
        >
          Collections
        </div>
        <div style={{ fontSize: 12, color: TEXT_DIM }}>
          6 pgvector collections · Neo4j entity graph
          {!stats && !error && (
            <span style={{ marginLeft: 8, fontSize: 9, color: TEXT_DIM, fontFamily: "'JetBrains Mono', monospace" }}>
              loading…
            </span>
          )}
          {error && (
            <span style={{ marginLeft: 8, fontSize: 9, color: "#f87171", fontFamily: "'JetBrains Mono', monospace" }}>
              {error}
            </span>
          )}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          marginBottom: 24,
        }}
      >
        {COLLECTIONS.map((c) => {
          const count = countMap[c.id] ?? 0;
          return (
            <div
              key={c.id}
              style={{
                background: SURFACE2,
                border: `1px solid ${BORDER}`,
                borderRadius: 12,
                padding: "16px",
                transition: "border-color .2s",
                cursor: "pointer",
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${c.color}44`)}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = BORDER)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    background: c.color,
                    boxShadow: `0 0 8px ${c.color}66`,
                  }}
                />
                <div style={{ fontSize: 11, color: TEXT_MID, fontWeight: 600 }}>{c.label}</div>
              </div>
              <div
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 22,
                  color: stats ? c.color : TEXT_DIM,
                  fontWeight: 500,
                }}
              >
                {stats ? count.toLocaleString() : "—"}
              </div>
              <div style={{ fontSize: 9, color: TEXT_DIM, marginTop: 2 }}>vectors stored</div>
              <div style={{ marginTop: 10, height: 2, background: BORDER, borderRadius: 1 }}>
                <div
                  style={{
                    height: "100%",
                    width: stats ? `${(count / maxCount) * 100}%` : "0%",
                    background: c.color,
                    borderRadius: 1,
                    opacity: 0.7,
                    transition: "width 0.6s ease",
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Neo4j stats */}
      <div
        style={{
          background: SURFACE2,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: "16px",
        }}
      >
        <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: neo4j?.connected ? AMBER : TEXT_DIM,
              boxShadow: neo4j?.connected ? `0 0 8px ${AMBER}66` : "none",
            }}
          />
          <div style={{ fontSize: 11, color: TEXT_MID, fontWeight: 600 }}>Neo4j Graph Database</div>
          {neo4j && (
            <Badge color={neo4j.connected ? "#10B981" : "#f87171"}>
              {neo4j.connected ? "connected" : "offline"}
            </Badge>
          )}
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {neo4jRows.map(([v, l]) => (
            <div key={l}>
              <div
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 20,
                  color: AMBER,
                }}
              >
                {v}
              </div>
              <div style={{ fontSize: 9, color: TEXT_DIM }}>{l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
