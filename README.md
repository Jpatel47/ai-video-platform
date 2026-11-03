# AI Video Platform

An experimental orchestration service and web UI for turning a text brief into an
animated video. A FastAPI backend plans a ten-stage workflow (story, scenes, prompts,
characters, images, motion, voice, music, composition, rendering), routes each stage
to a registered model, and runs the stages in dependency order through provider
adapters. A Next.js 14 frontend sends a brief to the planner and shows the planned
stages and routing decisions.

The repository contains no model code. Stages ask for a capability (for example
`image_generation`), the router picks a model from registry metadata, and a provider
adapter calls an external tool (Ollama or ComfyUI) to do the work.

## Status

What works today:

- `POST /api/v1/workflows/plan` builds the ten-stage plan and routes every stage by
  capability, quality, preferred execution mode (local, cloud or hybrid), cost and
  latency. Each route includes a readable reason. The built-in registry has one model
  per stage capability, so today the score and `preferred_execution_mode` only change
  the route reason; they decide between models once a capability has more than one
  registered model.
- `POST /api/v1/workflows/execute` plans and then runs the workflow synchronously,
  inside the request. Text stages call a local Ollama server and image stages call a
  local ComfyUI server. A failed stage marks its dependents as skipped.
- Stages without a real adapter run on a mock provider. They are reported with status
  `simulated` and listed in `simulated_stages`, never as `completed`.
- The frontend plans a workflow from a brief and shows the stages and routes.
- A GitHub Actions workflow runs ruff, mypy (strict), pytest and the TypeScript check.

| Stage | Routed model (provider) | Execution today |
| --- | --- | --- |
| `story_generation` | `ollama-director` (`ollama-local`) | Real: Ollama |
| `scene_planning` | `ollama-director` (`ollama-local`) | Real: Ollama |
| `prompt_enhancement` | `ollama-director` (`ollama-local`) | Real: Ollama |
| `character_generation` | `flux-image` (`comfyui-local`) | Real: ComfyUI text-to-image |
| `image_generation` | `flux-image` (`comfyui-local`) | Real: ComfyUI text-to-image |
| `image_to_video` | `ltx-video` (`cloud-video`) | Simulated: no adapter for `cloud-video` |
| `voice_generation` | `kokoro-voice` (`comfyui-local`) | Simulated: the ComfyUI adapter only implements image capabilities |
| `music_generation` | `musicgen` (`comfyui-local`) | Simulated: the ComfyUI adapter only implements image capabilities |
| `video_composition` | `ffmpeg-composer` (`renderer`) | Simulated: no adapter for `renderer` |
| `final_rendering` | `ffmpeg-composer` (`renderer`) | Simulated: no adapter for `renderer` |

A run therefore produces text (story, scene plan, image prompts) and still images,
but no video or audio yet. Known limitations:

- Model names in the registry (FLUX, LTX, Kokoro, MusicGen, FFmpeg) are routing
  metadata only. The ComfyUI adapter renders with `AI_VIDEO_COMFYUI_CHECKPOINT` or the
  first checkpoint installed in ComfyUI.
- `image_generation` depends only on `character_generation`, so it renders from the
  original brief rather than from the enhanced prompts.
- `image_generation` receives `character_generation`'s image URIs in
  `payload["artifacts"]`, but the ComfyUI adapter does not use them yet (no
  image-to-image or reference conditioning), so character consistency is not
  implemented. `supports_character_reference` is registry metadata only.
- Without a running Ollama server, a run fails at `story_generation` and every other
  stage is skipped. Planning does not need Ollama or ComfyUI.

Planned, not implemented:

- Adapters for image-to-video, voice, music, and FFmpeg composition and rendering.
- Persistence (PostgreSQL), background workers and queues (Redis), and asset storage
  (MinIO). `infra/docker-compose.yml` starts these services, but the backend does not
  connect to them yet.
- Live provider health in routing. The router reads a static health field from the
  provider registry. `GET /api/v1/providers/health` checks the Ollama and ComfyUI
  adapters live, but its result does not feed the router.
- Enforced stage input and output contracts.
- Authentication, projects, an asset library and a real render queue. In the UI, the
  sidebar and the queue panel show placeholder content, and the mode and tool toggles
  are not sent to the API.

## Architecture

```text
backend/    FastAPI service
  app/domain/          Pydantic models (capabilities, providers, models, routing, workflows)
                       and registry interfaces
  app/application/     model router, workflow engine (planning), workflow executor
  app/infrastructure/  in-memory registries seeded in registries/bootstrap.py, settings,
                       and the Ollama, ComfyUI and mock provider adapters
  app/api/             HTTP routes under /api/v1
frontend/   Next.js 14 (App Router) and Tailwind CSS; lib/api.ts is the API client
infra/      docker-compose file for PostgreSQL, Redis and MinIO (not used yet)
docs/       ARCHITECTURE.md and ROADMAP.md
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for routing and execution details and
[docs/ROADMAP.md](docs/ROADMAP.md) for planned work.

## Running locally

Requirements: Python 3.11+ and Node.js 18.17+ (CI uses Python 3.12 and Node.js 22).
Ollama and ComfyUI are optional; see the Status section for what fails without them.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env    # optional: every setting has a default
uvicorn app.main:app --reload --port 8000
```

Settings are read from `AI_VIDEO_*` environment variables or from `backend/.env`. API
docs are served at http://localhost:8000/docs.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local    # NEXT_PUBLIC_API_BASE_URL, default http://localhost:8000
npm run dev                   # http://localhost:3000
```

### Ollama (text stages)

```bash
ollama serve
ollama pull llama3.2
```

Set `AI_VIDEO_OLLAMA_DIRECTOR_MODEL` to use a different model. Small models keep each
stage to seconds; very large models can take minutes per stage on a laptop.

### ComfyUI (image stages)

Start ComfyUI on port 8188 (for example `python main.py --listen 127.0.0.1 --port 8188`
in a ComfyUI checkout) and install at least one checkpoint into
`ComfyUI/models/checkpoints/`. Set `AI_VIDEO_COMFYUI_BASE_URL` or
`AI_VIDEO_COMFYUI_CHECKPOINT` in `backend/.env` if the defaults do not fit.

### Infrastructure (optional, not used by the backend yet)

```bash
cp infra/.env.example infra/.env    # set your own passwords
docker compose --env-file infra/.env -f infra/docker-compose.yml up -d
```

## API examples

```bash
# Plan a workflow, preferring local models where one exists for a stage
curl -X POST http://localhost:8000/api/v1/workflows/plan \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A rabbit learns addition with friends.","quality":"high","preferred_execution_mode":"local"}'

# Plan and run it (needs Ollama for the text stages and ComfyUI for the image stages)
curl -X POST http://localhost:8000/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A rabbit learns addition with friends.","quality":"high"}'

# Live adapter health and the registries
curl http://localhost:8000/api/v1/providers/health
curl http://localhost:8000/api/v1/registry/models
curl http://localhost:8000/api/v1/registry/providers
```

## Tests and checks

CI runs the same commands (`.github/workflows/ci.yml`):

```bash
cd backend              # with the virtualenv active
ruff check .
ruff format --check .
mypy app tests          # strict settings from pyproject.toml
pytest

cd ../frontend
npx tsc --noEmit
```

The backend tests use fake providers and `httpx.MockTransport`, so they do not need
Ollama or ComfyUI.

## License

MIT. See [LICENSE](LICENSE).

Developed with AI pair-programming assistance (Claude Code).
