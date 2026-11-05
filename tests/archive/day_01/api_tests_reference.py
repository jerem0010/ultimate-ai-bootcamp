
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app import storage


# ---------- FIXTURES ----------

@pytest.fixture
def client():
    storage.reset_storage()

    with TestClient(app) as test_client:
        yield test_client


# ---------- TASK TESTS ----------

def test_create_task(client):
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain smart contract reentrancy",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    assert response.status_code == 201
    assert response.json()["task_id"] == 1
    assert response.json()["status"] == "pending"


def test_create_and_get_task(client):
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain smart contract reentrancy",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    assert response.status_code == 201

    task_id = response.json()["task_id"]

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["prompt"] == "Explain smart contract reentrancy"


def test_background_task_completed(client):
    payload = {
        "prompt": "Explain Ethereum reentrancy",
        "model": "GPT",
        "max_tokens": 500
    }

    response = client.post("/tasks", json=payload)

    assert response.status_code == 201

    task_id = response.json()["task_id"]

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


# ---------- BASIC ENDPOINT TESTS ----------

def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_square(client):
    response = client.get("/square/7")

    assert response.status_code == 200
    assert response.json() == {"square": 49}


# ---------- ERROR TESTS ----------

def test_task_not_found(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404


def test_invalid_task(client):
    response = client.post(
        "/tasks",
        json={
            "prompt": "short",
            "model": "GPT",
            "max_tokens": 500
        }
    )

    assert response.status_code == 422


def test_invalid_model(client):
    response = client.post(
        "/tasks",
        json={
            "prompt": "Explain Ethereum reentrancy",
            "model": "UnknownAI",
            "max_tokens": 500
        }
    )

    assert response.status_code == 422
