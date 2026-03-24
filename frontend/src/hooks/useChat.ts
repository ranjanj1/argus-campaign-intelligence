import { useCallback, useEffect, useState } from "react";
import { chatJson } from "../api/chat";
import type { Message, Source } from "../api/types";

const SESSION_KEY = "argus_session_id";

export function useChat(token: string | null, skill: string, clientId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingText, setStreamingText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(
    () => sessionStorage.getItem(SESSION_KEY) ?? undefined
  );

  // Reset messages + session when client or skill changes
  useEffect(() => {
    setMessages([]);
    setError(null);
    sessionStorage.removeItem(SESSION_KEY);
    setSessionId(undefined);
  }, [clientId, skill]);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || isStreaming) return;

      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: text }]);
      setIsStreaming(true);
      setStreamingText("");

      try {
        const { answer, sources, session_id } = await chatJson(text, sessionId, skill, clientId, token);

        setSessionId(session_id);
        sessionStorage.setItem(SESSION_KEY, session_id);

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: answer,
            sources,
            graphNodes: extractGraphNodes(sources),
          },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unexpected error");
      } finally {
        setIsStreaming(false);
        setStreamingText("");
      }
    },
    [isStreaming, sessionId, skill, clientId, token]
  );

  const clearHistory = useCallback(() => {
    setMessages([]);
    setError(null);
    sessionStorage.removeItem(SESSION_KEY);
    setSessionId(undefined);
  }, []);

  return { messages, streamingText, isStreaming, error, send, clearHistory };
}

// Build graph node strings from sources for display in the knowledge graph panel
function extractGraphNodes(sources: Source[]): string[] {
  const nodes: string[] = [];
  const seen = new Set<string>();
  for (const src of sources) {
    const label = src.collection
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
    if (!seen.has(label)) {
      seen.add(label);
      nodes.push(label);
    }
  }
  // Return as chain notation if multiple collections
  if (nodes.length > 1) return [nodes.join(" → ")];
  return [];
}
