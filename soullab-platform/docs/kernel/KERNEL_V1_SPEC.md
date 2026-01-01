# Soullab Kernel API v1 Specification

## Overview

The Kernel API provides consciousness-centric capabilities for developers building on Soullab.

**Base URL:** `http://localhost:3000` (development)

**Behavior Versioning:** All requests should include `X-SK-Behavior-Version: 2026-01` header.

---

## Core Capabilities

| Capability | Endpoint | Status |
|------------|----------|--------|
| Spiralogic | `POST /v1/spiralogic/detect` | Live |
| AIN | `POST /v1/ain/deliberate` | Live |
| Memory | `POST /v1/memory/write` | Live |
| Memory | `POST /v1/memory/retrieve` | Live |
| Memory | `GET /v1/memory/patterns/:user_id` | Live |
| Practices | `POST /v1/practices/generate` | Stub |
| Biomarkers | `POST /v1/biomarkers/analyze` | Stub |

---

## Sanctuary Mode (Privacy-First Default)

Memory operations use **sanctuary mode** by default. This means:

- **Default (no mode):** Data is acknowledged but **NOT stored**
- **Explicit `mode: "save"`:** Data is persisted and retrievable

This is intentional. Privacy-first means nothing persists without explicit consent.

### Example: Sanctuary Mode (default)

```bash
curl -X POST http://localhost:3000/v1/memory/write \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "kind": "journal",
    "facet_code": "W2",
    "tags": ["healing"],
    "payload": {"content": "This will NOT be stored."}
  }'
```

**Response (200 OK):**
```json
{
  "stored": false,
  "reason": "SANCTUARY_MODE",
  "behavior_version": "2026-01"
}
```

### Example: Save Mode (explicit persistence)

```bash
curl -X POST http://localhost:3000/v1/memory/write \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "kind": "journal",
    "facet_code": "W2",
    "tags": ["healing"],
    "mode": "save",
    "payload": {"content": "This WILL be stored."}
  }'
```

**Response (201 Created):**
```json
{
  "id": "mem_abc123",
  "org_id": "org_demo",
  "space_id": "spc_demo",
  "user_id": "usr_demo",
  "kind": "journal",
  "facet_code": "W2",
  "tags": ["healing"],
  "significance": 0.5,
  "timestamp": "2026-01-01T12:00:00.000Z",
  "stored": true,
  "behavior_version": "2026-01"
}
```

---

## Tenancy Model

All requests are scoped by:

| Field | Description |
|-------|-------------|
| `org_id` | Organization identifier |
| `space_id` | Space/workspace within org |
| `user_id` | Individual user |

---

## Error Envelope

All errors follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "retry_after_ms": 5000
  }
}
```

Common error codes:
- `BAD_REQUEST` - Invalid request body
- `SPIRALOGIC_UNAVAILABLE` - Python sidecar unreachable
- `AIN_UNAVAILABLE` - AIN service unreachable
- `MEMORY_WRITE_FAILED` - Memory operation failed

---

## Running Locally

### 1. Start Python sidecars

```bash
# Terminal 1: Spiralogic (port 5100)
cd src/kernel && python spiralogic_service.py

# Terminal 2: AIN (port 5200)
cd src/kernel && python ain_service.py
```

### 2. Start Node.js API

```bash
npm run dev
```

### 3. Health checks

```bash
curl http://localhost:3000/v1/health
curl http://localhost:3000/v1/spiralogic/health
curl http://localhost:3000/v1/ain/health
curl http://localhost:3000/v1/memory/health
```

---

## Facet Codes

| Code | Element | Description |
|------|---------|-------------|
| F1 | Fire | Initiation, spark |
| F2 | Fire | Transformation, alchemy |
| W1 | Water | Receptivity, flow |
| W2 | Water | Grief, depth |
| W3 | Water | Intuition, dreams |
| E1 | Earth | Foundation, stability |
| E2 | Earth | Structure, discipline |
| E3 | Earth | Manifestation |
| E4 | Earth | Completion, harvest |
| A1 | Air | Clarity, insight |
| A2 | Air | Communication |
| A3 | Air | Integration, synthesis |
| AETHER | Aether | Unity, transcendence |

---

## OpenAPI

Full OpenAPI 3.0 spec available at: `docs/kernel/openapi.v1.yaml`
