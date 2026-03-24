import { apiFetch } from "./client";

export async function fetchToken(clientId: string, skill: string): Promise<string> {
  const res = await apiFetch("/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_id: clientId, skill }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
    throw new Error(err.detail);
  }
  const data = await res.json();
  return data.token;
}
