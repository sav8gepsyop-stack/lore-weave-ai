"""FastAPI server: REST API for the builders plus Server-Sent Events for live writing previews."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import export
from .archetypes import list_archetypes
from .backends import BackendError, make_backend
from .content import ContentPolicyError, validate_project_content
from .engine.core import LoreWeaveEngine, plan_dimensions
from .genres import STRUCTURES, list_genres
from .models import Character, Project, new_id
from .storage import Store
from .style import PRESETS, preset_profile

WEB = Path(__file__).parent / "web"


class Job:
    def __init__(self, project_id: str):
        self.id = new_id("job_")
        self.project_id = project_id
        self.events: list[dict] = []
        self.done = False
        self.stop = False
        self.cond = asyncio.Condition()
        self.started = time.time()

    async def push(self, ev: dict):
        async with self.cond:
            self.events.append(ev)
            self.cond.notify_all()


class State:
    def __init__(self):
        self.store = Store()
        self.backend_name = os.environ.get("LOREWEAVE_BACKEND", "claude")
        self._backend = None
        self.jobs: dict[str, Job] = {}
        self.project_job: dict[str, str] = {}

    @property
    def backend(self):
        if self._backend is None:
            self._backend = make_backend(self.backend_name)
        return self._backend

    def engine(self) -> LoreWeaveEngine:
        return LoreWeaveEngine(self.backend)


def create_app(store_root: str | None = None, backend: str | None = None) -> FastAPI:
    app = FastAPI(title="Lore Weave AI")
    st = State()
    if store_root:
        st.store = Store(store_root)
    if backend:
        st.backend_name = backend
    app.state.lw = st

    def load(pid: str) -> Project:
        try:
            return st.store.load(pid)
        except KeyError:
            raise HTTPException(404, "project not found")

    def busy(pid: str):
        jid = st.project_job.get(pid)
        if jid and not st.jobs[jid].done:
            raise HTTPException(409, "a writing job is running for this project")

    async def guarded(coro):
        try:
            return await coro
        except BackendError as e:
            raise HTTPException(502, str(e))
        except ContentPolicyError as e:
            raise HTTPException(422, str(e))

    # ----------------------------------------------------------- meta / settings
    @app.get("/api/meta")
    def meta():
        return {"genres": list_genres(), "archetypes": list_archetypes(), "style_presets": PRESETS,
                "structures": STRUCTURES, "backend": st.backend_name}

    class SettingsIn(BaseModel):
        backend: str

    @app.get("/api/settings")
    def get_settings():
        info = {"backend": st.backend_name}
        if st._backend:
            info.update(st._backend.describe())
        return info

    @app.put("/api/settings")
    def put_settings(s: SettingsIn):
        if s.backend not in ("claude", "hf", "mock"):
            raise HTTPException(400, "backend must be claude, hf or mock")
        st.backend_name, st._backend = s.backend, None
        try:
            _ = st.backend
        except BackendError as e:
            st.backend_name, st._backend = "mock", None
            raise HTTPException(400, f"{e} (switched to mock)")
        return get_settings()

    # ----------------------------------------------------------- projects
    @app.get("/api/projects")
    def list_projects():
        return st.store.list()

    @app.post("/api/projects")
    def create_project(p: Project):
        p.id = new_id("prj_")
        p.chapters, p.ledger.facts = [], []
        return st.store.save(p)

    @app.get("/api/projects/{pid}")
    def get_project(pid: str):
        p = load(pid)
        n, wpc, acts = plan_dimensions(p.model_copy(deep=True))
        return {**p.model_dump(), "plan": {"chapters": n, "words_per_chapter": wpc, "acts": acts},
                "warnings": _warnings(p)}

    def _warnings(p: Project):
        try:
            return validate_project_content(p)
        except ContentPolicyError as e:
            return [f"BLOCKING: {e}"]

    @app.put("/api/projects/{pid}")
    def update_project(pid: str, p: Project):
        old = load(pid)
        busy(pid)
        p.id = pid
        p.chapters, p.ledger = old.chapters, old.ledger  # manuscript state is owned by the engine
        return st.store.save(p)

    @app.delete("/api/projects/{pid}")
    def delete_project(pid: str):
        st.store.delete(pid)
        return {"ok": True}

    # ----------------------------------------------------------- builders
    class CharGen(BaseModel):
        count: int = 1
        hints: str = ""
        archetype: str | None = None
        role: str | None = None

    @app.post("/api/projects/{pid}/characters/generate")
    async def gen_chars(pid: str, body: CharGen):
        p = load(pid)
        chars = await guarded(st.engine().generate_characters(p, max(1, min(body.count, 8)), body.hints, body.archetype, body.role))
        p.characters.extend(chars)
        st.store.save(p)
        return [c.model_dump() for c in chars]

    class Hints(BaseModel):
        hints: str = ""

    @app.post("/api/projects/{pid}/world/generate")
    async def gen_world(pid: str, body: Hints):
        p = load(pid)
        p.world = await guarded(st.engine().generate_world(p, body.hints))
        st.store.save(p)
        return p.world

    class StyleIn(BaseModel):
        influences: list[str] = []
        sample: str = ""
        preset: str | None = None

    @app.post("/api/projects/{pid}/style/analyze")
    async def style(pid: str, body: StyleIn):
        p = load(pid)
        if body.preset:
            if body.preset not in PRESETS:
                raise HTTPException(400, "unknown preset")
            p.style = preset_profile(body.preset, pov=p.style.pov, tense=p.style.tense, influences=body.influences)
        else:
            if not body.influences:
                raise HTTPException(400, "give at least one influence or a preset")
            p.style = await guarded(st.engine().analyze_style(p, body.influences, body.sample))
        st.store.save(p)
        return p.style

    @app.post("/api/projects/{pid}/outline/generate")
    async def gen_outline(pid: str):
        p = load(pid)
        busy(pid)
        p.outline = await guarded(st.engine().generate_outline(p))
        st.store.save(p)
        return p.outline

    class BranchIn(BaseModel):
        index: int
        option: int

    @app.post("/api/projects/{pid}/outline/branch")
    async def branch(pid: str, body: BranchIn):
        p = load(pid)
        busy(pid)
        if not (0 <= body.index < len(p.outline.branch_points)) or not (0 <= body.option < len(p.outline.branch_points[body.index].options)):
            raise HTTPException(400, "bad branch index/option")
        await guarded(st.engine().choose_branch(p, body.index, body.option))
        st.store.save(p)
        return p.outline

    # ----------------------------------------------------------- streaming
    def sse(gen):
        async def body():
            async for ev in gen:
                yield f"data: {json.dumps(ev)}\n\n"
        return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})

    class PreviewIn(BaseModel):
        instruction: str = ""

    @app.post("/api/projects/{pid}/preview")
    async def preview(pid: str, body: PreviewIn):
        p = load(pid)

        async def gen():
            try:
                async for chunk in st.engine().preview(p, body.instruction):
                    yield {"type": "delta", "text": chunk}
                yield {"type": "done"}
            except BackendError as e:
                yield {"type": "error", "message": str(e)}
        return sse(gen())

    class WriteIn(BaseModel):
        start: int = 1
        end: int | None = None

    @app.post("/api/projects/{pid}/write")
    async def write(pid: str, body: WriteIn):
        p = load(pid)
        busy(pid)
        try:
            validate_project_content(p)
        except ContentPolicyError as e:
            raise HTTPException(422, str(e))
        job = Job(pid)
        st.jobs[job.id] = job
        st.project_job[pid] = job.id

        async def run():
            try:
                async for ev in st.engine().write(p, body.start, body.end, should_stop=lambda: job.stop, on_save=st.store.save):
                    await job.push(ev)
            except Exception as e:  # report every failure to the UI
                await job.push({"type": "error", "message": str(e)})
            finally:
                st.store.save(p)
                job.done = True
                await job.push({"type": "closed"})

        asyncio.create_task(run())
        return {"job_id": job.id}

    @app.get("/api/jobs/{jid}/events")
    async def job_events(jid: str, request: Request, since: int = 0):
        job = st.jobs.get(jid)
        if not job:
            raise HTTPException(404, "job not found")

        async def gen():
            i = since
            while True:
                async with job.cond:
                    while i >= len(job.events) and not job.done:
                        try:
                            await asyncio.wait_for(job.cond.wait(), timeout=15)
                        except asyncio.TimeoutError:
                            break
                    new = job.events[i:]
                for ev in new:
                    i += 1
                    yield {**ev, "seq": i}
                if job.done and i >= len(job.events):
                    return
                if await request.is_disconnected():
                    return
                if not new:
                    yield {"type": "ping"}
        return sse(gen())

    @app.get("/api/projects/{pid}/job")
    def project_job(pid: str):
        jid = st.project_job.get(pid)
        if not jid:
            return {"job_id": None}
        j = st.jobs[jid]
        return {"job_id": jid, "done": j.done, "events": len(j.events)}

    @app.post("/api/jobs/{jid}/stop")
    def stop(jid: str):
        job = st.jobs.get(jid)
        if not job:
            raise HTTPException(404, "job not found")
        job.stop = True
        return {"ok": True}

    # ----------------------------------------------------------- chapters / export
    class ReviseIn(BaseModel):
        notes: str = ""

    @app.post("/api/projects/{pid}/chapters/{n}/revise")
    async def revise(pid: str, n: int, body: ReviseIn):
        p = load(pid)
        busy(pid)
        if not any(c.number == n for c in p.chapters):
            raise HTTPException(404, "chapter not written")
        rec = await guarded(st.engine().revise_chapter(p, n, body.notes))
        st.store.save(p)
        return rec

    @app.get("/api/projects/{pid}/export")
    def do_export(pid: str, format: str = "md"):
        p = load(pid)
        safe = "".join(ch for ch in p.title if ch.isalnum() or ch in " -_").strip() or "manuscript"
        if format == "md":
            return PlainTextResponse(export.to_markdown(p), headers={"Content-Disposition": f'attachment; filename="{safe}.md"'})
        if format == "txt":
            return PlainTextResponse(export.to_text(p), headers={"Content-Disposition": f'attachment; filename="{safe}.txt"'})
        if format == "html":
            return Response(export.to_html(p), media_type="text/html")
        if format == "epub":
            return Response(export.to_epub(p), media_type="application/epub+zip",
                            headers={"Content-Disposition": f'attachment; filename="{safe}.epub"'})
        raise HTTPException(400, "format must be md, txt, html or epub")

    # ----------------------------------------------------------- UI
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    return app


app = None


def get_app():
    global app
    if app is None:
        app = create_app()
    return app
