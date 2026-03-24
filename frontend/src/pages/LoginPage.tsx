import { useState } from "react";
import { fetchToken } from "../api/auth";
import { useAuth } from "../auth/useAuth";
import { AMBER, BG, BORDER, SURFACE, SURFACE2, TEXT_DIM, TEXT_MID, CLIENTS, SKILLS } from "../design/tokens";
import type { ClientId, SkillId } from "../design/tokens";
import Logo from "../components/ui/Logo";

export default function LoginPage() {
  const { setToken } = useAuth();
  const [clientId, setClientId] = useState<ClientId>("acme_corp");
  const [skill, setSkill] = useState<SkillId>("all_campaigns");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await fetchToken(clientId, skill);
      setToken(token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: BG,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: 360,
          background: SURFACE,
          border: `1px solid ${BORDER}`,
          borderRadius: 12,
          padding: "32px 28px",
        }}
      >
        <div style={{ marginBottom: 28 }}>
          <Logo />
          <div style={{ fontSize: 11, color: TEXT_DIM, marginTop: 6 }}>
            Campaign Intelligence System
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", display: "block", marginBottom: 6 }}>
            CLIENT
          </label>
          <select
            value={clientId}
            onChange={(e) => setClientId(e.target.value as ClientId)}
            style={{
              width: "100%",
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              color: TEXT_MID,
              borderRadius: 6,
              padding: "8px 10px",
              fontSize: 12,
              fontFamily: "'Syne', sans-serif",
              outline: "none",
            }}
          >
            {CLIENTS.map((c) => (
              <option key={c.id} value={c.id}>{c.label}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ fontSize: 9, color: TEXT_DIM, letterSpacing: "0.12em", display: "block", marginBottom: 6 }}>
            SKILL / ACCESS LEVEL
          </label>
          <select
            value={skill}
            onChange={(e) => setSkill(e.target.value as SkillId)}
            style={{
              width: "100%",
              background: SURFACE2,
              border: `1px solid ${BORDER}`,
              color: TEXT_MID,
              borderRadius: 6,
              padding: "8px 10px",
              fontSize: 12,
              fontFamily: "'Syne', sans-serif",
              outline: "none",
            }}
          >
            {SKILLS.map((s) => (
              <option key={s.id} value={s.id}>{s.label}</option>
            ))}
          </select>
        </div>

        {error && (
          <div style={{ fontSize: 11, color: "#F87171", marginBottom: 14 }}>{error}</div>
        )}

        <button
          onClick={handleLogin}
          disabled={loading}
          style={{
            width: "100%",
            padding: "10px",
            background: `${AMBER}18`,
            border: `1px solid ${AMBER}55`,
            borderRadius: 7,
            color: AMBER,
            fontSize: 11,
            fontFamily: "'Syne', sans-serif",
            fontWeight: 700,
            letterSpacing: "0.1em",
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "SIGNING IN…" : "SIGN IN"}
        </button>
      </div>
    </div>
  );
}
