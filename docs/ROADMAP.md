# Roadmap

## Phase 1: Foundation

- Registry-driven model routing
- Workflow planning API
- Project and workflow UI shell
- Local Postgres, Redis, and MinIO
- Test coverage for planner and router

## Phase 2: Durable Runs

- PostgreSQL persistence with SQLAlchemy repositories
- Workflow run state machine
- Celery queues with idempotent task execution
- Event log for every stage transition
- MinIO asset bucket lifecycle

## Phase 3: First Real Providers

- Ollama Director adapter for story and scene planning
- ComfyUI adapter for image generation and image editing
- FFmpeg/MoviePy rendering adapter
- Provider health checks and route fallbacks

## Phase 4: Creator Product

- Auth.js workspaces and projects
- Asset browser
- Character library
- Timeline editor
- Prompt library and reusable workflow templates
- Render queue controls

## Phase 5: Production Scale

- Cloud rendering workers
- Hybrid route policy based on VRAM, queue depth, cost, and SLA
- Billing meters
- Team collaboration
- Observability, tracing, and workflow replay
