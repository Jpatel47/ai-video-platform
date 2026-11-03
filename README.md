# AI Video Generation Platform

Production-minded scaffold for an AI Director platform that orchestrates animation generation across interchangeable local and remote AI providers.

The product goal is not to implement models inside the application. The platform owns planning, routing, workflow orchestration, asset management, rendering coordination, and user experience. Model implementations remain plugins behind provider interfaces.

## Monorepo Layout

```text
ai-video-platform/
  backend/     FastAPI service with clean architecture boundaries
  frontend/    Next.js workspace UI
  infra/       Local development infrastructure
  docs/        Architecture and engineering decisions
```

## Backend Capabilities In This Scaffold

- Capability, provider, model, and workflow registries
- Model router that selects models by capability, quality, execution mode, and cost
- Workflow engine that composes replaceable stages from a user prompt
- Workflow executor that runs stages in dependency order through provider adapters
- Ollama Director adapter: story generation, scene planning, and prompt enhancement
  run against a real local LLM (configure with `AI_VIDEO_OLLAMA_DIRECTOR_MODEL`)
- Mock adapters for image/video/audio providers until real adapters land
- FastAPI endpoints for health, registries, provider health, planning, and execution
- Tests for routing, planning, execution, and the HTTP API

## Frontend Capabilities In This Scaffold

- Dark AI Director workspace inspired by Cursor, Linear, Notion, and ComfyUI
- Prompt command center
- Workflow stage timeline
- Project/sidebar navigation
- Rendering queue and model routing summary panels

## Local Development

Backend:

```bash
cd ai-video-platform/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd ai-video-platform/frontend
npm install
npm run dev
```

Infrastructure:

```bash
cd ai-video-platform
docker compose -f infra/docker-compose.yml up
```

## Local LLM Setup

The Director stages (story, scenes, prompts) run on a local Ollama model.

```bash
ollama serve            # if not already running
ollama pull llama3.2    # small and fast; ideal for the director role
```

Point the backend at your model via `backend/.env`:

```bash
AI_VIDEO_OLLAMA_BASE_URL=http://localhost:11434
AI_VIDEO_OLLAMA_DIRECTOR_MODEL=llama3.2
```

Avoid very large models (30B+) for the director role — they run for minutes per
stage on a laptop and generate significant heat for no product benefit.

## Local Image Generation Setup (ComfyUI)

Character and image generation stages run on a local ComfyUI server.

```bash
cd ~/ComfyUI
.venv/bin/python main.py --listen 127.0.0.1 --port 8188
```

Download at least one checkpoint into `~/ComfyUI/models/checkpoints/`
(for example DreamShaper 8 or SDXL-Turbo from Hugging Face / Civitai). The
backend auto-discovers the first installed checkpoint, or set
`AI_VIDEO_COMFYUI_CHECKPOINT` explicitly in `backend/.env`.

## First API Calls

Plan a workflow:

```bash
curl -X POST http://localhost:8000/api/v1/workflows/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a magical children story about a rabbit learning addition.","quality":"high"}'
```

Execute a workflow (LLM stages run on Ollama, other stages are mocked for now):

```bash
curl -X POST http://localhost:8000/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Create a magical children story about a rabbit learning addition.","quality":"high"}'
```

Check provider health and registries:

```bash
curl http://localhost:8000/api/v1/providers/health
curl http://localhost:8000/api/v1/registry/models
curl http://localhost:8000/api/v1/registry/providers
```

## Architecture Principle

No workflow stage should know about Wan, LTX, FLUX, SDXL, Kokoro, or any other concrete model. Stages request capabilities. The router picks models through registry metadata and provider health.
