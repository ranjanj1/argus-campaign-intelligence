import { apiFetch } from "./client";

export interface CollectionStat {
  id: string;
  vector_count: number;
}

export interface Neo4jStats {
  nodes: number;
  edges: number;
  entity_types: number;
  rel_types: number;
  connected: boolean;
}

export interface CollectionsStatsResponse {
  collections: CollectionStat[];
  neo4j: Neo4jStats;
}

export async function fetchCollectionStats(): Promise<CollectionsStatsResponse> {
  const res = await apiFetch("/v1/collections/stats");
  if (!res.ok) throw new Error(`Failed to fetch collection stats (${res.status})`);
  return res.json();
}
