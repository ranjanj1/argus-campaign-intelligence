import { apiFetch } from "./client";
import type { SSEEvent, ChatResponse } from "./types";

/**
 * SSE streaming chat via fetch + ReadableStream.
 * EventSource doesn't support POST, so we use fetch and parse SSE frames manually.
 *
 * Backend emits three event types:
 *   event: token   data: {"token": "..."}
 *   event: done    data: {"answer": "...", "sources": [...], "session_id": "..."}
 *   event: error   data: {"detail": "..."}
 */
export async function* chatStream(
  message: string,
  sessionId: string | undefined,
  skill: string,
  clientId: string,
  token: string | null
): AsyncGenerator<SSEEvent> {
  let res: Response;
  try {
    res = await apiFetch(
      "/v1/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          stream: true,
          skill,
          client_id: clientId,
        }),
      },
      token
    );
  } catch {
    yield { type: "error", detail: "Network error — could not reach the server." };
    return;
  }

  if (!res.ok || !res.body) {
    let detail = `Server error (${res.status})`;
    try {
      const err = await res.json();
      detail = err.detail ?? detail;
    } catch { /* ignore */ }
    yield { type: "error", detail };
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames are separated by "\n\n"
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      if (!frame.trim()) continue;

      const lines = frame.split("\n");
      const eventLine = lines.find((l) => l.startsWith("event: "));
      const dataLine = lines.find((l) => l.startsWith("data: "));
      if (!dataLine) continue;

      const eventType = eventLine ? eventLine.slice(7).trim() : "message";
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(dataLine.slice(6));
      } catch {
        continue;
      }

      if (eventType === "token") {
        yield { type: "token", token: payload.token as string };
      } else if (eventType === "done") {
        yield { type: "done", response: payload as unknown as ChatResponse };
      } else if (eventType === "error") {
        yield { type: "error", detail: payload.detail as string };
      }
    }
  }
}

export async function chatJson(
  message: string,
  sessionId: string | undefined,
  skill: string,
  clientId: string,
  token: string | null
): Promise<ChatResponse> {
  const res = await apiFetch(
    "/v1/chat",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        stream: false,
        skill,
        client_id: clientId,
      }),
    },
    token
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
    throw new Error(err.detail);
  }
  return res.json();
}
