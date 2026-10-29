import pytest


@pytest.fixture
def owned(client):
    """One of each resource, created by the first user."""
    project = client.post("/projects", json={"name": "Mine"}).json()
    pid = project["id"]
    milestone = client.post(f"/projects/{pid}/milestones", json={"title": "step"}).json()
    idea = client.post(f"/projects/{pid}/ideas", json={"content": "idea"}).json()
    decision = client.post(
        f"/projects/{pid}/decisions", json={"title": "Pick X", "rationale": "because"}
    ).json()
    return {"pid": pid, "mid": milestone["id"], "iid": idea["id"], "did": decision["id"]}


# (method, path template, json body) for every route that addresses someone else's resource
FOREIGN_REQUESTS = [
    ("GET", "/projects/{pid}", None),
    ("PATCH", "/projects/{pid}", {"name": "Hijacked"}),
    ("DELETE", "/projects/{pid}", None),
    ("GET", "/projects/{pid}/milestones", None),
    ("POST", "/projects/{pid}/milestones", {"title": "intruder"}),
    ("PATCH", "/milestones/{mid}", {"done": True}),
    ("DELETE", "/milestones/{mid}", None),
    ("GET", "/projects/{pid}/ideas", None),
    ("POST", "/projects/{pid}/ideas", {"content": "intruder"}),
    ("PATCH", "/ideas/{iid}", {"content": "Hijacked"}),
    ("DELETE", "/ideas/{iid}", None),
    ("GET", "/projects/{pid}/decisions", None),
    ("POST", "/projects/{pid}/decisions", {"title": "intruder", "rationale": "x"}),
    ("DELETE", "/decisions/{did}", None),
]


@pytest.mark.parametrize(
    ("method", "path", "body"),
    FOREIGN_REQUESTS,
    ids=[f"{m} {p}" for m, p, _ in FOREIGN_REQUESTS],
)
def test_foreign_resource_is_404(client, users, owned, method, path, body):
    client.as_user(users[1])

    response = client.request(method, path.format(**owned), json=body)

    assert response.status_code == 404


def test_foreign_attempts_leave_owner_data_untouched(client, users, owned):
    client.as_user(users[1])
    for method, path, body in FOREIGN_REQUESTS:
        client.request(method, path.format(**owned), json=body)

    client.as_user(users[0])
    pid = owned["pid"]
    project = client.get(f"/projects/{pid}").json()
    assert project["name"] == "Mine"
    assert project["milestones_total"] == 1
    assert project["milestones_done"] == 0
    assert [i["content"] for i in client.get(f"/projects/{pid}/ideas").json()] == ["idea"]
    assert len(client.get(f"/projects/{pid}/decisions").json()) == 1


def test_collections_do_not_leak(client, users, owned):
    client.post("/ideas", json={"content": "inbox idea"})
    client.as_user(users[1])

    assert client.get("/projects").json() == []
    assert client.get("/ideas").json() == []
