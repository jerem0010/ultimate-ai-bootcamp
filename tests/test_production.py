
from test_api import client


PAYLOAD = {
    "model": "GPT",
    "prompt": "Explain how Redis rate limiting works",
    "max_tokens": 100,
}


def test_rate_limit(client):
    # Les dix premières requêtes sont autorisées.
    for _ in range(10):
        response = client.post(
            "/tasks",
            json=PAYLOAD,
        )

        assert response.status_code == 201, response.json()

    # La onzième est bloquée.
    response = client.post(
        "/tasks",
        json=PAYLOAD,
    )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_idempotency(client):
    headers = {
        "Idempotency-Key": "test-request-001",
    }

    first = client.post(
        "/tasks",
        json=PAYLOAD,
        headers=headers,
    )

    second = client.post(
        "/tasks",
        json=PAYLOAD,
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 200

    assert (
        first.json()["task_id"]
        == second.json()["task_id"]
    )

    # Une seule tâche doit être dans la queue.
    async def queue_length():
        redis = client.app.state.redis

        return await redis.llen(
            "ai:tasks:test:queue"
        )

    assert client.portal.call(queue_length) == 1


def test_idempotency_conflict(client):
    headers = {
        "Idempotency-Key": "test-request-002",
    }

    first = client.post(
        "/tasks",
        json=PAYLOAD,
        headers=headers,
    )

    assert first.status_code == 201

    different_payload = {
        **PAYLOAD,
        "max_tokens": 200,
    }

    second = client.post(
        "/tasks",
        json=different_payload,
        headers=headers,
    )

    assert second.status_code == 409
