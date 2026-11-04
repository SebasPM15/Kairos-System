def test_metrics_shape_and_defaults(client):
    project = client.post("/projects", json={"name": "A"}).json()
    client.post("/ideas", json={"content": "x", "project_id": project["id"]})
    client.post("/ideas", json={"content": "y"})

    response = client.get("/metrics")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "generated_at",
        "timezone",
        "weeks",
        "current_week_start",
        "projects_by_status",
        "project_progress",
        "milestones_completed",
        "ideas_captured",
        "ideas_assigned",
        "idea_totals",
    }
    assert body["weeks"] == 12
    assert body["timezone"] == "America/Guayaquil"
    assert len(body["projects_by_status"]) == 4
    for key in ("milestones_completed", "ideas_captured", "ideas_assigned"):
        assert len(body[key]) == 12
        assert set(body[key][0]) == {"week_start", "count"}
    assert body["ideas_captured"][-1]["count"] == 2
    assert body["ideas_assigned"][-1]["count"] == 1
    assert body["idea_totals"] == {"captured": 2, "in_inbox": 1, "assigned": 1}
    assert body["project_progress"][0]["name"] == "A"


def test_metrics_weeks_parameter_sets_the_series_length(client):
    body = client.get("/metrics", params={"weeks": 52}).json()

    assert body["weeks"] == 52
    assert len(body["ideas_captured"]) == 52
    assert len(client.get("/metrics", params={"weeks": 1}).json()["ideas_captured"]) == 1


def test_metrics_rejects_weeks_out_of_range(client):
    assert client.get("/metrics", params={"weeks": 0}).status_code == 422
    assert client.get("/metrics", params={"weeks": 53}).status_code == 422
    assert client.get("/metrics", params={"weeks": "x"}).status_code == 422


def test_metrics_are_isolated_between_users(client, users):
    project = client.post("/projects", json={"name": "Mine"}).json()
    client.post("/ideas", json={"content": "x", "project_id": project["id"]})

    client.as_user(users[1])
    body = client.get("/metrics").json()

    assert body["project_progress"] == []
    assert body["idea_totals"] == {"captured": 0, "in_inbox": 0, "assigned": 0}
    assert sum(point["count"] for point in body["ideas_captured"]) == 0
