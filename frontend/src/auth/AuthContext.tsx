import { createContext, useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import type { SkillId, ClientId } from "../design/tokens";

const DEV_MODE = import.meta.env.VITE_DEV_AUTH === "true";

export interface AuthState {
  token: string | null;
  skill: SkillId;
  clientId: ClientId;
  devMode: boolean;
  setToken: (t: string) => void;
  clearToken: () => void;
  // In dev mode, sidebar selectors drive these directly
  setSkill: (s: SkillId) => void;
  setClientId: (c: ClientId) => void;
}

const TOKEN_KEY = "argus_token";

function decodeTokenClaims(token: string): { skill?: string; client_id?: string } {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")));
  } catch {
    return {};
  }
}

export const AuthContext = createContext<AuthState>({
  token: null,
  skill: "all_campaigns",
  clientId: "acme_corp",
  devMode: DEV_MODE,
  setToken: () => {},
  clearToken: () => {},
  setSkill: () => {},
  setClientId: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => {
    if (DEV_MODE) return null;
    return localStorage.getItem(TOKEN_KEY);
  });

  const [skill, setSkillState] = useState<SkillId>("all_campaigns");
  const [clientId, setClientIdState] = useState<ClientId>("acme_corp");

  // On mount, decode existing token if in prod mode
  useEffect(() => {
    if (!DEV_MODE && token) {
      const claims = decodeTokenClaims(token);
      if (claims.skill) setSkillState(claims.skill as SkillId);
      if (claims.client_id) setClientIdState(claims.client_id as ClientId);
    }
  }, []);

  // Listen for 401 unauthorized events from apiFetch
  useEffect(() => {
    const handler = () => clearToken();
    window.addEventListener("argus:unauthorized", handler);
    return () => window.removeEventListener("argus:unauthorized", handler);
  }, []);

  const setToken = useCallback((t: string) => {
    localStorage.setItem(TOKEN_KEY, t);
    setTokenState(t);
    const claims = decodeTokenClaims(t);
    if (claims.skill) setSkillState(claims.skill as SkillId);
    if (claims.client_id) setClientIdState(claims.client_id as ClientId);
  }, []);

  const clearToken = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setTokenState(null);
  }, []);

  const setSkill = useCallback((s: SkillId) => {
    if (DEV_MODE) setSkillState(s);
  }, []);

  const setClientId = useCallback((c: ClientId) => {
    if (DEV_MODE) setClientIdState(c);
  }, []);

  return (
    <AuthContext.Provider
      value={{ token, skill, clientId, devMode: DEV_MODE, setToken, clearToken, setSkill, setClientId }}
    >
      {children}
    </AuthContext.Provider>
  );
}
