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

This scaffold starts with a modular backend service so the domain boundaries are visible before extracting services. Extraction should happen when deployment, scaling, or ownership pressure justifies it.

## Clean Architecture Layers

```text
api -> application -> domain
              |
              v
       infrastructure
```

- `domain`: entities, value objects, contracts, and business rules
- `application`: orchestration use cases such as planning, routing, and executing workflows
- `infrastructure`: concrete registries, providers, queues, object storage, and config
- `api`: transport layer only

## Registry Model

The critical extensibility mechanism is registry-driven model selection.

- Capability Registry: what tasks the platform understands
- Provider Registry: who can execute work
- Model Registry: model metadata and supported capabilities
- Workflow Registry: reusable workflow templates and stage definitions

A concrete model is never referenced from workflow code. A workflow stage asks for `image_generation`, `voice_generation`, `image_to_video`, or another capability. The router selects a registered model.

## Routing Strategy

The initial router is deterministic and explainable:

1. Filter models by requested capability.
2. Filter by enabled providers and health.
3. Match requested execution mode where possible.
4. Score by quality, estimated latency, and cost.
5. Return the highest-scoring route with a human-readable explanation.

Later versions should add:

- GPU and VRAM telemetry
- queue depth and SLA windows
- per-user budget policies
- provider failure rates
- model evaluation scores
- brand/template constraints

## Workflow Engine

The workflow engine composes replaceable stages:

```text
user_prompt
planner
scene_planner
prompt_enhancer
character_generation
image_generation
image_to_video
voice_generation
music_generation
video_composition
final_render
```

Each stage declares required capabilities, input contracts, and output contracts. Stage execution should move to Celery workers once provider adapters perform real work.

## Workflow Execution

The `WorkflowExecutor` runs a planned workflow synchronously:

1. Stages are ordered topologically from their `depends_on` declarations.
2. Each stage is dispatched to the provider adapter registered for its routed
   model's provider slug; unregistered providers fall back to a mock adapter.
3. Textual output from completed upstream stages is forwarded downstream as
   context, so the scene planner sees the story and the prompt enhancer sees
   the scenes.
4. A failed stage marks its downstream dependents as skipped; the run result
   records per-stage status, output, and error detail.

The Ollama adapter implements the Director capabilities (story generation,
scene planning, prompt enhancement) against a local Ollama server. The model
is configured with `AI_VIDEO_OLLAMA_DIRECTOR_MODEL`.

## Recommended Next Milestones

1. Persist projects, assets, model definitions, and workflow runs in PostgreSQL.
2. Move stage execution to Celery workers with Redis queues and idempotency keys.
3. Implement provider adapters for ComfyUI and a real cloud video provider.
4. Add MinIO asset storage and signed upload/download URLs.
5. Add workflow run state machine and event log.
6. Add user authentication and workspace authorization.
7. Poll live provider health into the provider registry for routing decisions.
