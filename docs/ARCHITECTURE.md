# Architecture

## Product Shape

The application is an AI Director for animation production. Users describe outcomes; the platform expands intent into scenes, assets, audio, motion, edits, subtitles, and final renders.

The platform does not own AI model code. It owns orchestration and product intelligence:

- understand user intent
- plan scenes and workflow stages
- choose the best provider for each capability
- dispatch jobs locally, in cloud, or hybrid
- track assets, versions, costs, and render state
- produce final video artifacts

## Service Boundaries

The long-term system should split into independently deployable services:

- API Gateway and BFF
- Auth Service
- Project Service
- Workflow Service
- LLM Director Service
- Image Service
- Video Service
- Voice Service
- Music Service
- Rendering Service
- Asset and Storage Service
- Billing Service
- Notification Service

None of these exist as separate services yet. The code is one modular backend service so the domain boundaries are visible before extracting services. Extraction should happen when deployment, scaling, or ownership pressure justifies it.

## Clean Architecture Layers

```text
api -> application -> domain
              |
              v
       infrastructure
```

- `domain`: entities, value objects, contracts, and business rules
- `application`: orchestration use cases such as planning, routing, and executing workflows
- `infrastructure`: concrete registries, provider adapters, and config. The `storage` and `workers` packages are empty placeholders for planned object storage and queue workers.
- `api`: transport layer only

## Registry Model

The critical extensibility mechanism is registry-driven model selection.

- Capability Registry: what tasks the platform understands
- Provider Registry: who can execute work
- Model Registry: model metadata and supported capabilities
- Workflow Registry: reusable workflow templates and stage definitions

A concrete model is never referenced from workflow code. A workflow stage asks for `image_generation`, `voice_generation`, `image_to_video`, or another capability. The router selects a registered model.

All four registries are in memory and seeded at startup in `app/infrastructure/registries/bootstrap.py`. Persisting them is planned.

## Routing Strategy

The initial router is deterministic and explainable:

1. Filter models by requested capability.
2. Drop disabled models and providers, and providers whose registry health is `unavailable`. Health is a static field in the provider registry today (every built-in provider is `healthy`); polling live health into the registry is planned. `GET /api/v1/providers/health` checks the adapters live but does not feed the router.
3. Apply hard constraints: character-reference support for stages that need it, and the optional cost ceiling.
4. Score by quality, estimated latency, and cost, plus a bonus for the preferred execution mode that outweighs the other terms. A model in the preferred mode wins whenever one exists; otherwise the best model in another mode is used and the route reason says so.
5. Return the highest-scoring route with a human-readable explanation.

Later versions should add:

- GPU and VRAM telemetry
- queue depth and SLA windows
- per-user budget policies
- provider failure rates
- model evaluation scores
- brand/template constraints

## Workflow Engine

The workflow engine plans the `text_to_animated_video` template, a fixed set of replaceable stages:

| Stage | Depends on |
| --- | --- |
| `story_generation` | (none) |
| `scene_planning` | `story_generation` |
| `prompt_enhancement` | `scene_planning` |
| `character_generation` | `prompt_enhancement` |
| `image_generation` | `character_generation` |
| `image_to_video` | `image_generation` |
| `voice_generation` | `story_generation` |
| `music_generation` | `scene_planning` |
| `video_composition` | `image_to_video`, `voice_generation`, `music_generation` |
| `final_rendering` | `video_composition` |

Each stage declares its required capability and its dependencies. `CapabilityDefinition` has `input_contract` and `output_contract` fields, but they are empty and not enforced yet (planned). Stages currently run inside the API request; moving execution to background workers is planned.

## Workflow Execution

The `WorkflowExecutor` runs a planned workflow synchronously:

1. Stages are ordered topologically from their `depends_on` declarations.
2. Each stage is dispatched to the provider adapter registered for its routed
   model's provider slug. Stages whose provider has no adapter, or whose adapter
   does not implement the capability, fall back to a mock adapter. They are
   reported with status `simulated` (not `completed`) and listed in the run's
   `simulated_stages`, because the mock returns placeholder `mock://` URIs and
   produces no media.
3. Only meaningful output of a stage's direct dependencies is forwarded: text
   in `payload["context"]` and artifact URIs in `payload["artifacts"]`, both
   keyed by stage. The scene planner sees the story and the prompt enhancer
   sees the scenes; provider bookkeeping fields are not forwarded.
4. A failed stage marks its downstream dependents as skipped; the run result
   records per-stage status, output, and error detail.

The Ollama adapter implements the Director capabilities (story generation,
scene planning, prompt enhancement) against a local Ollama server. The model
is configured with `AI_VIDEO_OLLAMA_DIRECTOR_MODEL`.

The ComfyUI adapter implements character generation and image generation with a
checkpoint text-to-image graph: it submits the graph to `POST /prompt`, polls
`GET /history/{prompt_id}`, and returns the image URLs. It uses
`AI_VIDEO_COMFYUI_CHECKPOINT` or the first installed checkpoint. No other
capability has a real adapter yet.

## Recommended Next Milestones

None of these are implemented yet. `infra/docker-compose.yml` already starts PostgreSQL, Redis and MinIO for this work, but the backend does not connect to them.

1. Persist projects, assets, model definitions, and workflow runs in PostgreSQL.
2. Move stage execution to Celery workers with Redis queues and idempotency keys.
3. Add adapters for the simulated capabilities: image-to-video, voice, music, and FFmpeg composition and rendering.
4. Add MinIO asset storage and signed upload/download URLs.
5. Add workflow run state machine and event log.
6. Add user authentication and workspace authorization.
7. Poll live provider health into the provider registry for routing decisions.
8. Define and enforce stage input and output contracts.
