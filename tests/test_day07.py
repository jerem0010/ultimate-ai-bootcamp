from unittest.mock import AsyncMock
from app import storage
from test_api import client


def test_readiness_success(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "postgres": "ok", "redis": "ok"}


def test_readiness_redis_failure(client, monkeypatch):
    monkeypatch.setattr(client.app.state.redis, "ping", AsyncMock(side_effect=ConnectionError("Redis down")))
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["redis"] == "error"
    assert response.json()["postgres"] == "ok"


def test_readiness_postgres_failure(client, monkeypatch):
    def unavailable_pool():
        raise ConnectionError("PostgreSQL down")
    monkeypatch.setattr(storage, "get_pool", unavailable_pool)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["postgres"] == "error"
    assert response.json()["redis"] == "ok"
