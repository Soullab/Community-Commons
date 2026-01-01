/**
 * Soullab Kernel API v1 Routes
 *
 * Pattern: validate → resolve behavior version → call capability → return object
 *
 * Each capability module (spiralogic, ain, memory, etc.) is called from here.
 * The actual implementations live in /src/core/ and Python modules.
 */

import type { FastifyInstance, FastifyRequest, FastifyReply } from "fastify";
import { z } from "zod";
import {
  writeMemory,
  retrieveMemories,
  getMemoryPatterns,
  getStoreStats,
  type MemoryItem,
  type WriteMemoryResult,
  type SanctuaryResponse,
} from "../../kernel/memory-store.js";

// ============================================================================
// Kernel Service Clients
// ============================================================================

const SPIRALOGIC_SERVICE_URL = process.env.SPIRALOGIC_SERVICE_URL || "http://localhost:5100";
const AIN_SERVICE_URL = process.env.AIN_SERVICE_URL || "http://localhost:5200";
const PRACTICES_SERVICE_URL = process.env.PRACTICES_SERVICE_URL || "http://localhost:5300";
const DEFAULT_TIMEOUT_MS = 8000; // 8 seconds - fail fast

interface SpiralogicDetectResponse {
  facet_code: string;
  confidence: number;
  signals: Array<{ type: string; value: string; weight: number }>;
  spiral_position: {
    phase: string;
    level: number;
    angular_position: number;
    radial_distance: number;
    elemental_blend: Record<string, number>;
  };
  behavior_version: string;
}

interface AinDeliberationResponse {
  id: string;
  question: string;
  agents: string[];
  votes: Array<{ agent: string; score: number; recommendation: string }>;
  synthesis: string;
  emergence_score: number;
  behavior_version: string;
}

interface KernelError {
  code: string;
  message: string;
  retry_after_ms?: number;
}

/**
 * Typed upstream service error with retry hints
 */
class UpstreamServiceError extends Error {
  status: number;
  upstreamBody?: unknown;
  retryAfterMs?: number;
  constructor(message: string, status: number, upstreamBody?: unknown, retryAfterMs?: number) {
    super(message);
    this.name = "UpstreamServiceError";
    this.status = status;
    this.upstreamBody = upstreamBody;
    this.retryAfterMs = retryAfterMs;
  }
}

function parseRetryAfterMs(headerValue: string | null): number | undefined {
  if (!headerValue) return undefined;
  const n = Number(headerValue);
  if (Number.isFinite(n) && n >= 0) return n * 1000;
  const d = Date.parse(headerValue);
  if (!Number.isNaN(d)) {
    const delta = d - Date.now();
    return delta > 0 ? delta : 0;
  }
  return undefined;
}

async function readJsonOrText(response: Response): Promise<{ json?: any; text?: string }> {
  const text = await response.text().catch(() => "");
  if (!text) return {};
  try {
    return { json: JSON.parse(text) };
  } catch {
    return { text };
  }
}

/**
 * Bulletproof POST with timeout - never hangs, throws on non-2xx
 */
async function postJsonWithTimeout<T>(
  url: string,
  payload: unknown,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  extraHeaders: Record<string, string> = {}
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...extraHeaders,
      },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const { json, text } = await readJsonOrText(response);

    if (!response.ok) {
      const retryAfterMs = parseRetryAfterMs(response.headers.get("Retry-After"));
      const msg =
        json?.error?.message ||
        json?.message ||
        (typeof text === "string" && text.trim() ? text.trim() : `Service error: ${response.status}`);
      throw new UpstreamServiceError(msg, response.status, json ?? text, retryAfterMs);
    }

    // If upstream returned no body, still return a typed empty object
    return (json ?? ({} as any)) as T;
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Normalize AIN response to stable v1 contract (handles snake_case/camelCase drift)
 */
function normalizeAinDeliberationResponse(
  raw: any,
  fallbackQuestion: string,
  fallbackBehaviorVersion: string
): AinDeliberationResponse {
  const votes = Array.isArray(raw?.votes) ? raw.votes : [];
  const agents = Array.isArray(raw?.agents) ? raw.agents : [];
  const emergence =
    typeof raw?.emergence_score === "number"
      ? raw.emergence_score
      : typeof raw?.emergenceScore === "number"
        ? raw.emergenceScore
        : 0;

  return {
    id: typeof raw?.id === "string" ? raw.id : generateId("delib"),
    question: typeof raw?.question === "string" ? raw.question : fallbackQuestion,
    agents,
    votes: votes
      .filter((v: any) => v && typeof v === "object")
      .map((v: any) => ({
        agent: typeof v.agent === "string" ? v.agent : "UnknownAgent",
        score: typeof v.score === "number" ? v.score : 0,
        recommendation: typeof v.recommendation === "string" ? v.recommendation : "",
      })),
    synthesis: typeof raw?.synthesis === "string" ? raw.synthesis : "",
    emergence_score: emergence,
    behavior_version:
      typeof raw?.behavior_version === "string" ? raw.behavior_version : fallbackBehaviorVersion,
  };
}

/**
 * Normalize Practices response to stable v1 contract
 */
type PracticeItem = {
  id: string;
  facet_code: string;
  element: "fire" | "water" | "earth" | "air" | "aether";
  title: string;
  duration_min: number;
  difficulty: "easy" | "moderate" | "advanced" | string;
  steps: string[];
  tags: string[];
  contraindications: string[];
};

function normalizePracticesResponse(
  raw: any,
  fallbackFacet: string,
  fallbackBehaviorVersion: string
): { practices: PracticeItem[]; behavior_version: string } {
  const list = Array.isArray(raw?.practices) ? raw.practices : [];

  const practices: PracticeItem[] = list
    .filter((p: any) => p && typeof p === "object")
    .map((p: any) => ({
      id: typeof p.id === "string" ? p.id : generateId("prac"),
      facet_code: typeof p.facet_code === "string" ? p.facet_code : fallbackFacet,
      element:
        p.element === "fire" ||
        p.element === "water" ||
        p.element === "earth" ||
        p.element === "air" ||
        p.element === "aether"
          ? p.element
          : "aether",
      title: typeof p.title === "string" ? p.title : "",
      duration_min: typeof p.duration_min === "number" ? p.duration_min : 10,
      difficulty: typeof p.difficulty === "string" ? p.difficulty : "easy",
      steps: Array.isArray(p.steps) ? p.steps.filter((s: any) => typeof s === "string") : [],
      tags: Array.isArray(p.tags) ? p.tags.filter((t: any) => typeof t === "string") : [],
      contraindications: Array.isArray(p.contraindications)
        ? p.contraindications.filter((c: any) => typeof c === "string")
        : [],
    }));

  return {
    practices,
    behavior_version:
      typeof raw?.behavior_version === "string" ? raw.behavior_version : fallbackBehaviorVersion,
  };
}

/**
 * Consistent error envelope - never lies
 */
function kernelErrorEnvelope(
  code: string,
  message: string,
  retryAfterMs?: number
): { error: KernelError } {
  const err: KernelError = { code, message };
  if (retryAfterMs) err.retry_after_ms = retryAfterMs;
  return { error: err };
}

// ============================================================================
// Request Schemas
// ============================================================================

const TenantContext = z.object({
  org_id: z.string().min(1),
  space_id: z.string().min(1),
  user_id: z.string().min(1),
});

const FacetCode = z.enum([
  "F1", "F2",           // Fire
  "W1", "W2", "W3",     // Water
  "E1", "E2", "E3", "E4", // Earth
  "A1", "A2", "A3",     // Air
  "AETHER"              // Aether
]);

// --- Insights ---
const InsightExtractBody = TenantContext.extend({
  input: z.object({
    type: z.enum(["text", "journal", "transcript"]),
    content: z.string().min(1),
    timestamp: z.string().optional(),
  }),
  context: z.record(z.any()).optional(),
});

// --- Spiralogic ---
const FacetDetectBody = z.object({
  org_id: z.string().min(1),
  user_id: z.string().min(1),
  signals: z.object({
    text: z.string().optional(),
    recent_themes: z.array(z.string()).optional(),
    biomarker_ref: z.string().optional(),
  }),
});

// --- AIN ---
const DeliberateBody = TenantContext.extend({
  question: z.string().min(1),
  context: z.object({
    facet_code: FacetCode.optional(),
    memory_refs: z.array(z.string()).optional(),
    framings: z.array(z.string()).optional(),
  }).optional(),
  agents: z.array(z.string()).optional(),
});

// --- Memory ---
const MemoryWriteBody = TenantContext.extend({
  kind: z.enum(["journal", "insight", "session", "transcript", "practice", "milestone"]),
  facet_code: FacetCode.optional(),
  entities: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  significance: z.number().min(0).max(1).optional(),
  payload: z.record(z.any()).optional(),
  mode: z.enum(["sanctuary", "save"]).optional(), // Privacy-first: defaults to sanctuary
});

const MemoryRetrieveBody = TenantContext.extend({
  query: z.object({
    semantic: z.string().optional(),
    facet_codes: z.array(FacetCode).optional(),
    entities: z.array(z.string()).optional(),
    tags: z.array(z.string()).optional(),
    kinds: z.array(z.enum(["journal", "insight", "session", "transcript", "practice", "milestone"])).optional(),
    time_range: z.object({
      from: z.string().optional(),
      to: z.string().optional(),
    }).optional(),
    min_significance: z.number().min(0).max(1).optional(),
  }),
  limit: z.number().min(1).max(100).default(20),
});

// --- Practices ---
const PracticeGenerateBody = z.object({
  org_id: z.string().min(1),
  user_id: z.string().min(1),
  facet_code: FacetCode,
  element_preference: z.enum(["fire", "water", "earth", "air", "aether"]).optional(),
  duration_available_min: z.number().default(15),
  difficulty: z.enum(["easy", "moderate", "advanced"]).default("moderate"),
  contraindications: z.array(z.string()).optional(),
});

// --- Biomarkers ---
const BiomarkerAnalyzeBody = z.object({
  org_id: z.string().min(1),
  user_id: z.string().min(1),
  input: z.union([
    z.object({
      type: z.literal("audio_ref"),
      ref: z.string(),
    }),
    z.object({
      type: z.literal("features"),
      f0_mean: z.number(),
      formants: z.object({
        F1: z.number(),
        F2: z.number(),
        F3: z.number().optional(),
        F4: z.number().optional(),
      }),
      energy: z.number(),
      spectral_centroid: z.number().optional(),
    }),
  ]),
});

// ============================================================================
// Helpers
// ============================================================================

function resolveBehaviorVersion(req: FastifyRequest): string {
  const header = req.headers["x-sk-behavior-version"];
  return typeof header === "string" ? header : "2026-01";
}

function generateId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).substring(2, 10)}`;
}

function setResponseHeaders(reply: FastifyReply, behaviorVersion: string, traceId: string) {
  reply.header("X-SK-Behavior-Version-Resolved", behaviorVersion);
  reply.header("X-SK-Trace-Id", traceId);
}

// ============================================================================
// Route Definitions
// ============================================================================

export async function kernelRoutes(app: FastifyInstance) {

  // ---------------------------------------------------------------------------
  // Insights
  // ---------------------------------------------------------------------------

  app.post("/v1/insights/extract", async (req, reply) => {
    const body = InsightExtractBody.parse(req.body);
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");

    // TODO: Call actual capability
    // const insight = await app.kernel.insights.extract({ ...body, behaviorVersion });

    const insight = {
      id: generateId("ins"),
      facet_code: "W2",
      themes: ["placeholder"],
      archetypes: [],
      tension: "Placeholder tension - wire to spiralogic_integration.py",
      invitation: "Placeholder invitation",
      confidence: 0.0,
      sources: [],
      behavior_version: behaviorVersion,
    };

    setResponseHeaders(reply, behaviorVersion, traceId);
    return insight;
  });

  // ---------------------------------------------------------------------------
  // Spiralogic
  // ---------------------------------------------------------------------------

  app.post("/v1/spiralogic/detect", async (req, reply) => {
    const body = FacetDetectBody.parse(req.body);
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");

    // Backward compatibility: accept both `input` (old) and `signals` (new)
    const signals = body.signals ?? (body as any).input ?? {};

    setResponseHeaders(reply, behaviorVersion, traceId);

    try {
      // Call the Python spiralogic service with timeout + trace propagation
      const serviceResponse = await postJsonWithTimeout<SpiralogicDetectResponse>(
        `${SPIRALOGIC_SERVICE_URL}/detect`,
        {
          signals,
          behavior_version: behaviorVersion,
        },
        DEFAULT_TIMEOUT_MS,
        {
          "X-SK-Trace-Id": traceId,
          "X-SK-Behavior-Version": behaviorVersion,
        }
      );

      return {
        facet_code: serviceResponse.facet_code,
        confidence: serviceResponse.confidence,
        signals: serviceResponse.signals,
        spiral_position: serviceResponse.spiral_position,
        behavior_version: serviceResponse.behavior_version,
      };
    } catch (error) {
      const isTimeout = error instanceof Error && error.name === "AbortError";

      if (isTimeout) {
        return reply.status(504).send(
          kernelErrorEnvelope("SPIRALOGIC_TIMEOUT", "Spiralogic service timed out", 2000)
        );
      }

      const retryAfterMs =
        error instanceof UpstreamServiceError ? error.retryAfterMs : undefined;
      console.warn(`Spiralogic service unavailable: ${error}`);
      return reply.status(503).send(
        kernelErrorEnvelope(
          "SPIRALOGIC_UNAVAILABLE",
          "Spiralogic service temporarily unavailable",
          retryAfterMs ?? 5000
        )
      );
    }
  });

  // Health proxy - check if spiralogic service is up
  app.get("/v1/spiralogic/health", async (_req, reply) => {
    const traceId = generateId("tr");
    reply.header("X-SK-Trace-Id", traceId);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    try {
      const response = await fetch(`${SPIRALOGIC_SERVICE_URL}/health`, {
        signal: controller.signal,
        headers: { "X-SK-Trace-Id": traceId },
      });

      if (response.ok) {
        const { json } = await readJsonOrText(response);
        return { status: "ok", service: "spiralogic", upstream: json ?? {} };
      }

      return reply
        .status(503)
        .send(kernelErrorEnvelope("SPIRALOGIC_UNHEALTHY", "Service returned non-ok"));
    } catch (_error) {
      return reply
        .status(503)
        .send(kernelErrorEnvelope("SPIRALOGIC_UNREACHABLE", "Cannot reach spiralogic service"));
    } finally {
      clearTimeout(timeout); // no timer leaks
    }
  });

  // ---------------------------------------------------------------------------
  // AIN (Multi-Agent Deliberation)
  // ---------------------------------------------------------------------------

  app.post("/v1/ain/deliberate", async (req, reply) => {
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");
    setResponseHeaders(reply, behaviorVersion, traceId);

    let body: z.infer<typeof DeliberateBody>;
    try {
      body = DeliberateBody.parse(req.body);
    } catch (e: any) {
      return reply.status(400).send(
        kernelErrorEnvelope("BAD_REQUEST", e?.message || "Invalid request body")
      );
    }

    try {
      // Call the Python AIN service with timeout + trace propagation
      const raw = await postJsonWithTimeout<any>(
        `${AIN_SERVICE_URL}/deliberate`,
        {
          question: body.question,
          context: body.context ?? {},
          agents: body.agents ?? [],
          behavior_version: behaviorVersion,
        },
        DEFAULT_TIMEOUT_MS,
        {
          "X-SK-Trace-Id": traceId,
          "X-SK-Behavior-Version": behaviorVersion,
        }
      );

      // Response normalization (stable v1 contract)
      return normalizeAinDeliberationResponse(raw, body.question, behaviorVersion);
    } catch (error) {
      const isTimeout = error instanceof Error && error.name === "AbortError";

      if (isTimeout) {
        return reply.status(504).send(
          kernelErrorEnvelope("AIN_TIMEOUT", "AIN service timed out", 2000)
        );
      }

      const retryAfterMs =
        error instanceof UpstreamServiceError ? error.retryAfterMs : undefined;
      console.warn(`AIN service unavailable: ${error}`);
      return reply.status(503).send(
        kernelErrorEnvelope(
          "AIN_UNAVAILABLE",
          "AIN service temporarily unavailable",
          retryAfterMs ?? 5000
        )
      );
    }
  });

  // Health proxy - check if AIN service is up
  app.get("/v1/ain/health", async (_req, reply) => {
    const traceId = generateId("tr");
    reply.header("X-SK-Trace-Id", traceId);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    try {
      const response = await fetch(`${AIN_SERVICE_URL}/health`, {
        signal: controller.signal,
        headers: { "X-SK-Trace-Id": traceId },
      });

      if (response.ok) {
        const { json } = await readJsonOrText(response);
        return { status: "ok", service: "ain", upstream: json ?? {} };
      }

      return reply
        .status(503)
        .send(kernelErrorEnvelope("AIN_UNHEALTHY", "Service returned non-ok"));
    } catch (_error) {
      return reply
        .status(503)
        .send(kernelErrorEnvelope("AIN_UNREACHABLE", "Cannot reach AIN service"));
    } finally {
      clearTimeout(timeout); // no timer leaks
    }
  });

  app.get("/v1/ain/sessions/:id", async (req, reply) => {
    const { id } = req.params as { id: string };
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");

    // TODO: Retrieve from storage

    setResponseHeaders(reply, behaviorVersion, traceId);
    return reply.status(404).send({
      error: {
        code: "NOT_FOUND",
        message: `Deliberation session ${id} not found`,
      },
    });
  });

  // ---------------------------------------------------------------------------
  // Memory
  // ---------------------------------------------------------------------------

  app.post("/v1/memory/write", async (req, reply) => {
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");
    setResponseHeaders(reply, behaviorVersion, traceId);

    let body: z.infer<typeof MemoryWriteBody>;
    try {
      body = MemoryWriteBody.parse(req.body);
    } catch (e: any) {
      return reply.status(400).send(
        kernelErrorEnvelope("BAD_REQUEST", e?.message || "Invalid request body")
      );
    }

    try {
      const memoryItem: MemoryItem = {
        id: generateId("mem"),
        org_id: body.org_id,
        space_id: body.space_id,
        user_id: body.user_id,
        kind: body.kind,
        facet_code: body.facet_code,
        entities: body.entities ?? [],
        tags: body.tags ?? [],
        significance: body.significance ?? 0.5,
        timestamp: new Date().toISOString(),
        content: body.payload?.content as string | undefined,
        payload: body.payload,
        mode: body.mode, // Privacy-first: defaults to sanctuary in store
      };

      const result = writeMemory(memoryItem, behaviorVersion);

      // Sanctuary mode: acknowledged but not stored
      if ("stored" in result && result.stored === false) {
        return {
          stored: false,
          reason: result.reason,
          behavior_version: behaviorVersion,
        };
      }

      // Data was persisted
      const stored = result as MemoryItem;
      reply.status(201);
      return {
        id: stored.id,
        org_id: stored.org_id,
        space_id: stored.space_id,
        user_id: stored.user_id,
        kind: stored.kind,
        facet_code: stored.facet_code,
        entities: stored.entities,
        tags: stored.tags,
        significance: stored.significance,
        timestamp: stored.timestamp,
        stored: true,
        behavior_version: behaviorVersion,
      };
    } catch (error) {
      console.error(`Memory write failed: ${error}`);
      return reply.status(500).send(
        kernelErrorEnvelope("MEMORY_WRITE_FAILED", "Failed to write memory")
      );
    }
  });

  app.post("/v1/memory/retrieve", async (req, reply) => {
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");
    setResponseHeaders(reply, behaviorVersion, traceId);

    let body: z.infer<typeof MemoryRetrieveBody>;
    try {
      body = MemoryRetrieveBody.parse(req.body);
    } catch (e: any) {
      return reply.status(400).send(
        kernelErrorEnvelope("BAD_REQUEST", e?.message || "Invalid request body")
      );
    }

    try {
      const result = retrieveMemories({
        org_id: body.org_id,
        space_id: body.space_id,
        user_id: body.user_id,
        semantic: body.query.semantic,
        facet_codes: body.query.facet_codes,
        entities: body.query.entities,
        tags: body.query.tags,
        kinds: body.query.kinds,
        time_range: body.query.time_range,
        min_significance: body.query.min_significance,
        limit: body.limit,
      });

      return {
        items: result.items.map((m) => ({
          id: m.id,
          kind: m.kind,
          facet_code: m.facet_code,
          entities: m.entities,
          tags: m.tags,
          significance: m.significance,
          timestamp: m.timestamp,
          content_preview: m.content?.slice(0, 200),
        })),
        summary: result.summary,
        behavior_version: behaviorVersion,
      };
    } catch (error) {
      console.error(`Memory retrieve failed: ${error}`);
      return reply.status(500).send(
        kernelErrorEnvelope("MEMORY_RETRIEVE_FAILED", "Failed to retrieve memories")
      );
    }
  });

  app.get("/v1/memory/patterns/:user_id", async (req, reply) => {
    const { user_id } = req.params as { user_id: string };
    const query = req.query as { org_id?: string; space_id?: string };
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");
    setResponseHeaders(reply, behaviorVersion, traceId);

    // org_id is required for tenancy
    if (!query.org_id) {
      return reply.status(400).send(
        kernelErrorEnvelope("BAD_REQUEST", "org_id query parameter is required")
      );
    }

    try {
      const patterns = getMemoryPatterns(query.org_id, user_id, query.space_id);

      return {
        user_id: patterns.user_id,
        range: patterns.range,
        facet_frequency: patterns.facet_frequency,
        top_entities: patterns.top_entities,
        top_tags: patterns.top_tags,
        transitions: patterns.transitions,
        total_memories: patterns.total_memories,
        behavior_version: behaviorVersion,
      };
    } catch (error) {
      console.error(`Memory patterns failed: ${error}`);
      return reply.status(500).send(
        kernelErrorEnvelope("MEMORY_PATTERNS_FAILED", "Failed to get memory patterns")
      );
    }
  });

  // Memory health endpoint
  app.get("/v1/memory/health", async (_req, reply) => {
    const traceId = generateId("tr");
    reply.header("X-SK-Trace-Id", traceId);

    try {
      const stats = getStoreStats();
      return {
        status: "ok",
        service: "memory",
        store_type: "in-memory",
        total_items: stats.total_items,
      };
    } catch (error) {
      return reply.status(503).send(
        kernelErrorEnvelope("MEMORY_UNHEALTHY", "Memory store is unhealthy")
      );
    }
  });

  // ---------------------------------------------------------------------------
  // Practices / Journeys
  // ---------------------------------------------------------------------------

  app.post("/v1/practices/generate", async (req, reply) => {
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");
    setResponseHeaders(reply, behaviorVersion, traceId);

    let body: z.infer<typeof PracticeGenerateBody>;
    try {
      body = PracticeGenerateBody.parse(req.body);
    } catch (e: any) {
      return reply.status(400).send(
        kernelErrorEnvelope("BAD_REQUEST", e?.message || "Invalid request body")
      );
    }

    try {
      const raw = await postJsonWithTimeout<any>(
        `${PRACTICES_SERVICE_URL}/generate`,
        {
          facet_code: body.facet_code,
          element_preference: body.element_preference,
          duration_available_min: body.duration_available_min ?? 15,
          difficulty: body.difficulty ?? "easy",
          contraindications: body.contraindications ?? [],
          behavior_version: behaviorVersion,
        },
        DEFAULT_TIMEOUT_MS,
        {
          "X-SK-Trace-Id": traceId,
          "X-SK-Behavior-Version": behaviorVersion,
        }
      );

      return normalizePracticesResponse(raw, body.facet_code, behaviorVersion);
    } catch (error) {
      const isTimeout = error instanceof Error && error.name === "AbortError";

      if (isTimeout) {
        return reply
          .status(504)
          .send(
            kernelErrorEnvelope(
              "PRACTICES_TIMEOUT",
              "Practices service timed out",
              2000
            )
          );
      }

      const retryAfterMs =
        error instanceof UpstreamServiceError ? error.retryAfterMs : undefined;
      console.warn(`Practices service unavailable: ${error}`);
      return reply
        .status(503)
        .send(
          kernelErrorEnvelope(
            "PRACTICES_UNAVAILABLE",
            "Practices service temporarily unavailable",
            retryAfterMs ?? 5000
          )
        );
    }
  });

  // Health proxy - check if practices service is up
  app.get("/v1/practices/health", async (_req, reply) => {
    const traceId = generateId("tr");
    reply.header("X-SK-Trace-Id", traceId);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
      const response = await fetch(`${PRACTICES_SERVICE_URL}/health`, {
        signal: controller.signal,
        headers: { "X-SK-Trace-Id": traceId },
      });

      const { json } = await readJsonOrText(response);

      if (response.ok) {
        return { status: "ok", service: "practices", upstream: json ?? {} };
      }

      return reply
        .status(503)
        .send(kernelErrorEnvelope("PRACTICES_UNHEALTHY", "Service returned non-ok"));
    } catch (_error) {
      return reply
        .status(503)
        .send(kernelErrorEnvelope("PRACTICES_UNREACHABLE", "Cannot reach practices service"));
    } finally {
      clearTimeout(timeout);
    }
  });

  app.get("/v1/timeline/summary", async (req, reply) => {
    const query = req.query as {
      org_id: string;
      space_id: string;
      user_id: string;
      from: string;
      to: string;
    };
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");

    // TODO: Call timeline synthesis

    setResponseHeaders(reply, behaviorVersion, traceId);
    return {
      user_id: query.user_id,
      range: { from: query.from, to: query.to },
      dominant_themes: [],
      turning_points: [],
      cycles: [],
      next_edges: [],
      behavior_version: behaviorVersion,
    };
  });

  // ---------------------------------------------------------------------------
  // Biomarkers (Builder+ tier)
  // ---------------------------------------------------------------------------

  app.post("/v1/biomarkers/analyze", async (req, reply) => {
    const body = BiomarkerAnalyzeBody.parse(req.body);
    const behaviorVersion = resolveBehaviorVersion(req);
    const traceId = generateId("tr");

    // TODO: Check tier, call consciousness-biomarkers/src/acoustic_detector.py

    // Placeholder - would check tier from JWT claims
    const tier = "explorer"; // Replace with actual tier check
    if (tier === "explorer") {
      return reply.status(403).send({
        error: {
          code: "INSUFFICIENT_TIER",
          message: "Biomarker analysis requires Builder tier or above",
          tier_required: "builder",
          upgrade_url: "https://soullab.ai/pricing",
        },
      });
    }

    setResponseHeaders(reply, behaviorVersion, traceId);
    return {
      id: generateId("bio"),
      input_type: body.input.type,
      elemental_signature: {
        fire: 0.2,
        water: 0.3,
        earth: 0.25,
        air: 0.2,
        aether: 0.05,
      },
      stress_level: 0.5,
      coherence_score: 0.5,
      notes: [],
      behavior_version: behaviorVersion,
    };
  });

  // ---------------------------------------------------------------------------
  // Health & Discovery
  // ---------------------------------------------------------------------------

  app.get("/v1/health", async () => {
    return {
      status: "ok",
      version: "1.0.0",
      behavior_versions: ["2026-01"],
      capabilities: [
        "insights.extract",
        "spiralogic.detect",
        "ain.deliberate",
        "memory.write",
        "memory.retrieve",
        "memory.patterns",
        "practices.generate",
        "timeline.summary",
        "biomarkers.analyze",
      ],
    };
  });
}
