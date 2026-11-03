# Roadmap

Each item is marked **done**, **partial** or **planned** based on the current code.
The README status table lists which workflow stages run on real providers.

## Phase 1: Foundation

- Registry-driven model routing (**done**; the registries are in memory)
- Workflow planning API (**done**)
- Project and workflow UI shell (**partial**: planning and routing views call the API;
  projects, assets and the render queue are placeholder UI)
- Local Postgres, Redis, and MinIO (**partial**: defined in `infra/docker-compose.yml`,
  not used by the backend yet)
- Test coverage for planner and router (**done**)

## Phase 2: Durable Runs (planned)

- PostgreSQL persistence with SQLAlchemy repositories
- Workflow run state machine
- Celery queues with idempotent task execution
- Event log for every stage transition
- MinIO asset bucket lifecycle

## Phase 3: First Real Providers

- Ollama Director adapter for story, scene planning and prompt enhancement (**done**)
- ComfyUI adapter for image generation and image editing (**partial**: character and
  image generation use a text-to-image graph; image editing is not implemented)
- FFmpeg/MoviePy rendering adapter (**planned**; composition and final rendering are
  simulated by the mock provider)
- Provider health checks and route fallbacks (**partial**: `GET /api/v1/providers/health`
  checks the adapters live, but routing uses the static health field in the provider
  registry; the router falls back to another execution mode when no model runs in the
  preferred one, but not when a provider fails)

## Phase 4: Creator Product (planned)

- Auth.js workspaces and projects
- Asset browser
- Character library
- Timeline editor
- Prompt library and reusable workflow templates
- Render queue controls

## Phase 5: Production Scale (planned)

- Cloud rendering workers
- Hybrid route policy based on VRAM, queue depth, cost, and SLA
- Billing meters
- Team collaboration
- Observability, tracing, and workflow replay
