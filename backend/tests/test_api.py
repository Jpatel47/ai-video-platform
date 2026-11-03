import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_models() -> None:
    response = client.get("/api/v1/registry/models")
    assert response.status_code == 200
    slugs = {model["slug"] for model in response.json()}
    assert "ollama-director" in slugs
    assert "flux-image" in slugs


def test_list_providers() -> None:
    response = client.get("/api/v1/registry/providers")
    assert response.status_code == 200
    slugs = {provider["slug"] for provider in response.json()}
    assert "ollama-local" in slugs


def test_plan_workflow() -> None:
    response = client.post(
        "/api/v1/workflows/plan",
        json={"prompt": "A rabbit learns addition with friends.", "quality": "high"},
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["status"] == "planned"
    assert len(plan["stages"]) == 10
    assert all(stage["route"] is not None for stage in plan["stages"])


@pytest.mark.parametrize("mode", ["local", "cloud", "hybrid"])
def test_plan_workflow_accepts_preferred_execution_mode(mode: str) -> None:
    response = client.post(
        "/api/v1/workflows/plan",
        json={
            "prompt": "A rabbit learns addition with friends.",
            "quality": "high",
            "preferred_execution_mode": mode,
        },
    )
    assert response.status_code == 200, response.text
    plan = response.json()
    assert len(plan["stages"]) == 10
    assert all(stage["route"] is not None for stage in plan["stages"])


def test_plan_workflow_rejects_short_prompt() -> None:
    response = client.post("/api/v1/workflows/plan", json={"prompt": "ab"})
    assert response.status_code == 422
