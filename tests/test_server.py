from fastapi.testclient import TestClient

from loreweave.server import create_app


def test_full_flow(tmp_path):
    c = TestClient(create_app(store_root=str(tmp_path), backend="mock"))
    assert c.get("/").status_code == 200
    meta = c.get("/api/meta").json()
    assert any(a["key"] == "tsundere" for a in meta["archetypes"])
    pid = c.post("/api/projects", json={"title": "Neon Ronin", "genres": ["manga", "cyberpunk"], "target_pages": 50}).json()["id"]
    assert len(c.post(f"/api/projects/{pid}/characters/generate", json={"count": 2, "archetype": "kuudere"}).json()) == 2
    assert c.post(f"/api/projects/{pid}/world/generate", json={}).json()["name"]
    assert c.post(f"/api/projects/{pid}/style/analyze", json={"preset": "light_novel"}).json()["summary"]
    assert c.post(f"/api/projects/{pid}/outline/generate").json()["chapters"]
    with c.stream("POST", f"/api/projects/{pid}/preview", json={}) as r:
        body = "".join(r.iter_text())
    assert '"type": "done"' in body
    job = c.post(f"/api/projects/{pid}/write", json={"start": 1, "end": 2}).json()["job_id"]
    with c.stream("GET", f"/api/jobs/{job}/events") as r:
        ev = "".join(r.iter_text())
    assert '"type": "closed"' in ev and '"type": "chapter_done"' in ev
    p = c.get(f"/api/projects/{pid}").json()
    assert len(p["chapters"]) == 2
    assert c.get(f"/api/projects/{pid}/export?format=epub").status_code == 200
    rv = c.post(f"/api/projects/{pid}/chapters/1/revise", json={"notes": "more tension"})
    assert rv.status_code == 200 and rv.json()["revised"]
