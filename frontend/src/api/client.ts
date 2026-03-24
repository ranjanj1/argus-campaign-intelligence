// Base fetch wrapper — injects auth header, emits 401 event

// Empty string → relative paths → handled by Vite proxy in dev
// In production, VITE_API_BASE_URL is the absolute backend URL
const BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "";

export async function apiFetch(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<Response> {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent("argus:unauthorized"));
  }

  return res;
}
