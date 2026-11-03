import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.v1.router import api_router
from app.application.services.model_router import NoModelRouteError
from app.application.services.workflow_executor import WorkflowExecutionError
from app.infrastructure.config.settings import get_settings
from app.infrastructure.providers.comfyui_provider import ComfyUIExecutionError
from app.infrastructure.providers.ollama_provider import OllamaExecutionError


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NoModelRouteError)
    async def no_model_route_handler(request: Request, error: NoModelRouteError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @app.exception_handler(WorkflowExecutionError)
    async def workflow_execution_handler(
        request: Request, error: WorkflowExecutionError
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(error)})

    @app.exception_handler(OllamaExecutionError)
    async def ollama_execution_handler(
        request: Request, error: OllamaExecutionError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    @app.exception_handler(ComfyUIExecutionError)
    async def comfyui_execution_handler(
        request: Request, error: ComfyUIExecutionError
    ) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", response_class=HTMLResponse, tags=["system"])
    async def root() -> str:
        return """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>AI Video Platform API</title>
            <style>
              :root { color-scheme: dark; }
              body {
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                background: #0b0d10;
                color: #f3f7fb;
                font-family: Inter, ui-sans-serif, system-ui, sans-serif;
              }
              main {
                width: min(720px, calc(100vw - 32px));
                border: 1px solid #27303a;
                border-radius: 8px;
                background: #12161b;
                padding: 28px;
                box-shadow: 0 22px 70px rgba(0, 0, 0, 0.38);
              }
              h1 { margin: 0 0 8px; font-size: 24px; }
              p { margin: 0 0 20px; color: #9ca9b7; line-height: 1.6; }
              nav { display: grid; gap: 10px; }
              a {
                display: block;
                border: 1px solid #27303a;
                border-radius: 6px;
                padding: 12px 14px;
                color: #3dd6c6;
                text-decoration: none;
                background: #0b0d10;
              }
              a:hover { border-color: #3dd6c6; }
            </style>
          </head>
          <body>
            <main>
              <h1>AI Video Platform API</h1>
              <p>
                The backend is running. Open the creator workspace for the app UI,
                or use the API docs and health endpoints for backend development.
              </p>
              <nav>
                <a href="http://127.0.0.1:3000/">Open creator workspace</a>
                <a href="/docs">Open API docs</a>
                <a href="/health">Check backend health</a>
                <a href="/api/v1/registry/models">View registered models</a>
              </nav>
            </main>
          </body>
        </html>
        """

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
