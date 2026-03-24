import { useCallback, useState } from "react";

const STORAGE_KEY = "argus_query_history";
const MAX_ITEMS = 20;

export interface HistoryEntry {
  q: string;
  t: string; // display time label
  ts: number; // unix ms for sorting
}

function load(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function formatAge(ts: number): string {
  const diff = Date.now() - ts;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return "Yesterday";
}

export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(load);

  const push = useCallback((query: string) => {
    setHistory((prev) => {
      // Deduplicate — remove any existing entry with the same query
      const filtered = prev.filter((h) => h.q !== query);
      const next: HistoryEntry = { q: query, t: "just now", ts: Date.now() };
      const updated = [next, ...filtered].slice(0, MAX_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const refreshLabels = useCallback(() => {
    setHistory((prev) => {
      const updated = prev.map((h) => ({ ...h, t: formatAge(h.ts) }));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  const remove = useCallback((ts: number) => {
    setHistory((prev) => {
      const updated = prev.filter((h) => h.ts !== ts);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      return updated;
    });
  }, []);

  return { history, push, refreshLabels, remove };
}
