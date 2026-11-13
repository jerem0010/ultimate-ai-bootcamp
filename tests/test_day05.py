from test_api import client
from app import storage


def test_task_pagination_and_filter(client):
    ids = []
    for i in range(3):
        response = client.post("/tasks", json={"model": "GPT", "prompt": f"Explain SQL indexing {i}"})
        assert response.status_code == 201
        task = response.json()
        assert task["created_at"] and task["updated_at"]
        ids.append(task["task_id"])
    client.portal.call(storage.complete_task, ids[1], "done")
    page = client.get("/tasks?limit=2").json()
    assert [t["task_id"] for t in page["items"]] == ids[::-1][:2]
    assert page["next_cursor"] == ids[1]
    page2 = client.get("/tasks", params={"limit": 2, "before_id": page["next_cursor"]}).json()
    assert [t["task_id"] for t in page2["items"]] == ids[:1]
    assert page2["next_cursor"] is None
    filtered = client.get("/tasks?status=completed").json()
    assert [t["task_id"] for t in filtered["items"]] == [ids[1]]
    assert filtered["items"][0]["result"] == "done"


def test_invalid_pagination(client):
    for query in ("limit=0", "limit=101", "before_id=0", "status=unknown"):
        assert client.get(f"/tasks?{query}").status_code == 422
