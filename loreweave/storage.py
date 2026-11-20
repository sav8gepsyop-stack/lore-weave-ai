"""JSON file storage for projects (one file per project)."""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

from .models import Project

_ID = re.compile(r"^[A-Za-z0-9_\-]+$")


class Store:
    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root or os.environ.get("LOREWEAVE_DATA", "data")) / "projects"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, pid: str) -> Path:
        if not _ID.match(pid):
            raise KeyError(pid)
        return self.root / f"{pid}.json"

    def save(self, p: Project) -> Project:
        p.updated_at = time.time()
        tmp = self._path(p.id).with_suffix(".tmp")
        tmp.write_text(p.model_dump_json(indent=1), encoding="utf-8")
        tmp.replace(self._path(p.id))
        return p

    def load(self, pid: str) -> Project:
        path = self._path(pid)
        if not path.exists():
            raise KeyError(pid)
        return Project.model_validate_json(path.read_text(encoding="utf-8"))

    def delete(self, pid: str) -> None:
        self._path(pid).unlink(missing_ok=True)

    def list(self) -> list[dict]:
        out = []
        for f in sorted(self.root.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                p = Project.model_validate_json(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            out.append({"id": p.id, "title": p.title, "genres": p.genres, "length_mode": p.length_mode,
                        "chapters": len(p.chapters), "planned": len(p.outline.chapters), "words": p.word_count,
                        "updated_at": p.updated_at})
        return out
