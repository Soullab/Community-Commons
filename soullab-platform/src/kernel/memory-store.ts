/**
 * Memory Store - Kernel v1 MVP
 *
 * In-memory implementation for development/demo.
 * Swap to Postgres with same interface when ready.
 *
 * Tenancy: org_id → space_id → user_id
 */

export interface MemoryItem {
  id: string;
  org_id: string;
  space_id: string;
  user_id: string;
  kind: "journal" | "insight" | "session" | "transcript" | "practice" | "milestone";
  facet_code?: string;
  entities: string[];
  tags: string[];
  significance: number;
  timestamp: string;
  content?: string;
  payload?: Record<string, any>;
  mode?: "sanctuary" | "save";
}

export interface MemoryQuery {
  org_id: string;
  space_id?: string;
  user_id: string;
  semantic?: string;
  facet_codes?: string[];
  entities?: string[];
  tags?: string[];
  kinds?: string[];
  time_range?: { from?: string; to?: string };
  min_significance?: number;
  limit?: number;
}

export interface MemoryPatterns {
  user_id: string;
  range: { from: string | null; to: string | null };
  facet_frequency: Record<string, number>;
  top_entities: Array<{ entity: string; count: number }>;
  top_tags: Array<{ tag: string; count: number }>;
  transitions: Array<{ from: string; to: string; count: number }>;
  total_memories: number;
}

export interface SanctuaryResponse {
  stored: false;
  reason: "SANCTUARY_MODE";
  behavior_version?: string;
}

export type WriteMemoryResult = MemoryItem | SanctuaryResponse;

// In-memory store (replace with Postgres queries later)
const memoryStore: Map<string, MemoryItem> = new Map();

/**
 * Generate tenant-scoped key for lookups
 */
function tenantKey(org_id: string, space_id: string, user_id: string): string {
  return `${org_id}:${space_id}:${user_id}`;
}

/**
 * Write a memory item
 *
 * Privacy-first: defaults to "sanctuary" mode where data is NOT stored.
 * Only persists when mode === "save" is explicitly set.
 */
export function writeMemory(item: MemoryItem, behaviorVersion?: string): WriteMemoryResult {
  const mode = item.mode ?? "sanctuary";

  // Sanctuary mode: acknowledge but don't persist
  if (mode !== "save") {
    return {
      stored: false,
      reason: "SANCTUARY_MODE",
      behavior_version: behaviorVersion,
    };
  }

  memoryStore.set(item.id, item);
  return item;
}

/**
 * Retrieve memories with filtering
 */
export function retrieveMemories(query: MemoryQuery): {
  items: MemoryItem[];
  summary: { total_matches: number; returned: number; dominant_facet: string | null };
} {
  const limit = query.limit ?? 20;

  // Filter memories by tenancy and query params
  let items = Array.from(memoryStore.values()).filter((m) => {
    // Tenancy check
    if (m.org_id !== query.org_id) return false;
    if (query.space_id && m.space_id !== query.space_id) return false;
    if (m.user_id !== query.user_id) return false;

    // Facet filter
    if (query.facet_codes?.length && m.facet_code) {
      if (!query.facet_codes.includes(m.facet_code)) return false;
    }

    // Kind filter
    if (query.kinds?.length) {
      if (!query.kinds.includes(m.kind)) return false;
    }

    // Entity filter (any match)
    if (query.entities?.length) {
      const hasEntity = query.entities.some((e) => m.entities.includes(e));
      if (!hasEntity) return false;
    }

    // Tag filter (any match)
    if (query.tags?.length) {
      const hasTag = query.tags.some((t) => m.tags.includes(t));
      if (!hasTag) return false;
    }

    // Significance filter
    if (query.min_significance !== undefined) {
      if (m.significance < query.min_significance) return false;
    }

    // Time range filter
    if (query.time_range) {
      const ts = new Date(m.timestamp).getTime();
      if (query.time_range.from) {
        if (ts < new Date(query.time_range.from).getTime()) return false;
      }
      if (query.time_range.to) {
        if (ts > new Date(query.time_range.to).getTime()) return false;
      }
    }

    // Semantic search (simple contains for MVP - upgrade to embeddings later)
    if (query.semantic) {
      const searchText = query.semantic.toLowerCase();
      const contentMatch = m.content?.toLowerCase().includes(searchText);
      const tagMatch = m.tags.some((t) => t.toLowerCase().includes(searchText));
      const entityMatch = m.entities.some((e) => e.toLowerCase().includes(searchText));
      if (!contentMatch && !tagMatch && !entityMatch) return false;
    }

    return true;
  });

  // Sort by timestamp descending (most recent first)
  items.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const totalMatches = items.length;

  // Apply limit
  items = items.slice(0, limit);

  // Calculate dominant facet
  const facetCounts: Record<string, number> = {};
  for (const item of items) {
    if (item.facet_code) {
      facetCounts[item.facet_code] = (facetCounts[item.facet_code] ?? 0) + 1;
    }
  }
  const dominantFacet =
    Object.entries(facetCounts).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;

  return {
    items,
    summary: {
      total_matches: totalMatches,
      returned: items.length,
      dominant_facet: dominantFacet,
    },
  };
}

/**
 * Get memory patterns for a user (basic aggregations)
 */
export function getMemoryPatterns(
  org_id: string,
  user_id: string,
  space_id?: string
): MemoryPatterns {
  // Get all memories for this user
  const userMemories = Array.from(memoryStore.values()).filter((m) => {
    if (m.org_id !== org_id) return false;
    if (space_id && m.space_id !== space_id) return false;
    if (m.user_id !== user_id) return false;
    return true;
  });

  if (userMemories.length === 0) {
    return {
      user_id,
      range: { from: null, to: null },
      facet_frequency: {},
      top_entities: [],
      top_tags: [],
      transitions: [],
      total_memories: 0,
    };
  }

  // Sort by timestamp
  userMemories.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  // Time range
  const range = {
    from: userMemories[0].timestamp,
    to: userMemories[userMemories.length - 1].timestamp,
  };

  // Facet frequency
  const facetFrequency: Record<string, number> = {};
  for (const m of userMemories) {
    if (m.facet_code) {
      facetFrequency[m.facet_code] = (facetFrequency[m.facet_code] ?? 0) + 1;
    }
  }

  // Entity counts
  const entityCounts: Record<string, number> = {};
  for (const m of userMemories) {
    for (const e of m.entities) {
      entityCounts[e] = (entityCounts[e] ?? 0) + 1;
    }
  }
  const topEntities = Object.entries(entityCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([entity, count]) => ({ entity, count }));

  // Tag counts
  const tagCounts: Record<string, number> = {};
  for (const m of userMemories) {
    for (const t of m.tags) {
      tagCounts[t] = (tagCounts[t] ?? 0) + 1;
    }
  }
  const topTags = Object.entries(tagCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([tag, count]) => ({ tag, count }));

  // Facet transitions (consecutive memories with different facets)
  const transitionCounts: Record<string, number> = {};
  for (let i = 1; i < userMemories.length; i++) {
    const prev = userMemories[i - 1].facet_code;
    const curr = userMemories[i].facet_code;
    if (prev && curr && prev !== curr) {
      const key = `${prev}→${curr}`;
      transitionCounts[key] = (transitionCounts[key] ?? 0) + 1;
    }
  }
  const transitions = Object.entries(transitionCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([key, count]) => {
      const [from, to] = key.split("→");
      return { from, to, count };
    });

  return {
    user_id,
    range,
    facet_frequency: facetFrequency,
    top_entities: topEntities,
    top_tags: topTags,
    transitions,
    total_memories: userMemories.length,
  };
}

/**
 * Get a single memory by ID
 */
export function getMemory(id: string): MemoryItem | undefined {
  return memoryStore.get(id);
}

/**
 * Delete a memory by ID
 */
export function deleteMemory(id: string): boolean {
  return memoryStore.delete(id);
}

/**
 * Clear all memories (for testing)
 */
export function clearAllMemories(): void {
  memoryStore.clear();
}

/**
 * Get store stats (for health checks)
 */
export function getStoreStats(): { total_items: number; memory_bytes: number } {
  return {
    total_items: memoryStore.size,
    memory_bytes: 0, // Would need proper measurement
  };
}
