# Soullab Kernel Services

This directory contains the kernel capability services that power the Soullab API.

## Architecture

```
Node.js (Fastify)              Python Services        In-Process
┌────────────────────┐        ┌──────────────────┐   ┌─────────────┐
│   kernelRoutes.ts  │───────▶│spiralogic_service│   │memory-store │
│                    │  HTTP  │    port 5100     │   │ (in-memory) │
│  /v1/spiralogic ───┼────────┘                  │   └──────┬──────┘
│  /v1/ain ──────────┼────────┐                  │          │
│  /v1/memory ───────┼────────┼──────────────────┼──────────┘
│  /v1/practices     │        ▼                  │
└────────────────────┘  ┌──────────────────┐
                        │   ain_service    │
                        │    port 5200     │
                        └──────────────────┘
```

## Running the Services

### 1. Start the Spiralogic Service

```bash
cd /Users/soullab/soullab-platform/src/kernel
python spiralogic_service.py
```

The service will start on port 5100.

### 2. Start the AIN Service (in another terminal)

```bash
cd /Users/soullab/soullab-platform/src/kernel
python ain_service.py
```

The service will start on port 5200.

### 3. Start the Main API (in another terminal)

```bash
cd /Users/soullab/soullab-platform
npm run dev
```

## Testing

### Health Check

```bash
curl http://localhost:5100/health
```

### Detect Facet

```bash
curl -X POST http://localhost:5100/detect \
  -H "Content-Type: application/json" \
  -d '{
    "signals": {
      "text": "I feel a profound transformation emerging. The fire of creativity is igniting new possibilities.",
      "recent_themes": ["breakthrough", "creativity"]
    },
    "behavior_version": "2026-01"
  }'
```

### Get Facet Info

```bash
curl http://localhost:5100/facet/W2
```

### Full API Test (through Node)

```bash
# Spiralogic detect
curl -X POST http://localhost:3000/v1/spiralogic/detect \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_test",
    "user_id": "usr_test",
    "signals": {
      "text": "I feel grief rising, old wounds surfacing. There is something that needs to be witnessed.",
      "recent_themes": ["loss", "healing"]
    }
  }'
```

### AIN Deliberation Test

```bash
# Health check
curl http://localhost:5200/health

# Deliberate (direct)
curl -X POST http://localhost:5200/deliberate \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the right next step for Kernel v1?",
    "agents": ["GuideAgent", "EarthAgent", "AirAgent"],
    "context": {"phase": "v1_wiring"}
  }'

# Through Node (full stack)
curl -X POST http://localhost:3000/v1/ain/deliberate \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "question": "What is the right next step for Kernel v1?",
    "agents": ["GuideAgent", "EarthAgent", "AirAgent"],
    "context": {"phase": "v1_wiring", "goal": "ship_1_customer_use_case"}
  }'
```

### Memory API Test

**Privacy-First Design**: Memory uses "sanctuary mode" by default. Data is NOT stored unless you explicitly set `mode: "save"`. This is intentional - privacy-first means nothing persists without consent.

```bash
# Health check (in-memory store)
curl http://localhost:3000/v1/memory/health

# Write a memory (sanctuary mode - NOT stored, just acknowledged)
curl -X POST http://localhost:3000/v1/memory/write \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "kind": "journal",
    "facet_code": "W2",
    "entities": ["grief", "mother"],
    "tags": ["healing", "family"],
    "significance": 0.8,
    "payload": {"content": "Today I sat with the grief of losing my mother..."}
  }'
# Returns: {"stored": false, "reason": "SANCTUARY_MODE", "behavior_version": "2026-01"}

# Write a memory (save mode - ACTUALLY stored)
curl -X POST http://localhost:3000/v1/memory/write \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "kind": "journal",
    "facet_code": "W2",
    "entities": ["grief", "mother"],
    "tags": ["healing", "family"],
    "significance": 0.8,
    "mode": "save",
    "payload": {"content": "Today I sat with the grief of losing my mother..."}
  }'
# Returns: {"id": "mem_xxx", "stored": true, ...}

# Retrieve memories
curl -X POST http://localhost:3000/v1/memory/retrieve \
  -H "Content-Type: application/json" \
  -H "X-SK-Behavior-Version: 2026-01" \
  -d '{
    "org_id": "org_demo",
    "space_id": "spc_demo",
    "user_id": "usr_demo",
    "query": {
      "facet_codes": ["W2"],
      "min_significance": 0.5
    },
    "limit": 10
  }'

# Get patterns
curl "http://localhost:3000/v1/memory/patterns/usr_demo?org_id=org_demo&space_id=spc_demo"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPIRALOGIC_PORT` | 5100 | Port for spiralogic service |
| `SPIRALOGIC_SERVICE_URL` | http://localhost:5100 | URL for Node to call spiralogic |
| `AIN_SERVICE_PORT` | 5200 | Port for AIN service |
| `AIN_SERVICE_URL` | http://localhost:5200 | URL for Node to call AIN |
| `SK_DEFAULT_BEHAVIOR_VERSION` | 2026-01 | Default behavior version |

## Service Dependencies

The spiralogic service requires:
- Python 3.9+
- Flask (`pip install flask`)
- The root-level `spiralogic_integration.py` and `complete_spiralogic_atlas.py`

Install dependencies:
```bash
pip install flask
```

## Adding New Kernel Services

1. Create a new Python service file (e.g., `ain_service.py`)
2. Add the service client in `kernelRoutes.ts`
3. Wire the endpoint to call the service
4. Add startup instructions to this README
