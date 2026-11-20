"""The Lore Weave engine: builders (characters, world, style, plot) and the manuscript writer.

Coherence strategy for long manuscripts:
1. Story bible (characters, world, style, content, outline) is the cached system prompt for every call.
2. Each chapter is written from its plan plus the continuity ledger and the previous chapter's ending.
3. After each chapter an extraction pass updates the ledger: summary, canon facts, character states,
   open/resolved threads, milestones.
4. Deterministic checks and a model-based continuity review flag contradictions; high-severity issues
   trigger an automatic revision pass.
5. Older chapter summaries are compressed into a rolling "story so far", so context stays bounded
   even at 200+ pages.
"""

from __future__ import annotations

import asyncio
import math
from typing import AsyncIterator, Callable

from ..backends import Backend, GenerationRequest
from ..content import validate_project_content
from ..models import (
    BranchPoint,
    Character,
    ChapterPlan,
    ChapterRecord,
    ContinuityIssue,
    LengthMode,
    PlotOutline,
    Project,
    StyleProfile,
    Subplot,
    World,
)
from . import prompts
from .continuity import apply_extraction, merge_extraction, quick_checks, rebuild_ledger
from .jsonutil import JSONParseError, parse_json_object

RECENT_WINDOW = 3  # chapter summaries kept verbatim before compression
COMPRESS_EVERY = 3  # compress once this many extra summaries accumulate beyond the window


def plan_dimensions(p: Project) -> tuple[int, int, int]:
    """Return (chapters, words_per_chapter, acts) for the project's length mode."""
    if p.length_mode == LengthMode.ULTRA:
        p.target_pages = max(p.target_pages, 200)
        wpc = 3000
        n = max(24, round(p.target_words / wpc))
        acts = 5 if n >= 40 else 4 if n >= 30 else 3
    else:
        p.target_pages = min(max(p.target_pages, 20), 150)
        wpc = 2500
        n = min(max(round(p.target_words / wpc), 6), 40)
        acts = 3
    wpc = math.ceil(p.target_words / n)
    return n, wpc, acts


class LoreWeaveEngine:
    def __init__(self, backend: Backend, check_continuity: bool = True, auto_revise: bool = True):
        self.backend = backend
        self.check_continuity = check_continuity
        self.auto_revise = auto_revise

    # ------------------------------------------------------------------ helpers
    async def _json(self, p: Project, prompt: str, task: str, meta: dict | None = None, max_tokens: int = 16000,
                    include_outline: bool = True) -> dict:
        req = GenerationRequest(system=prompts.bible(p, include_outline), prompt=prompt, task=task,
                                max_tokens=max_tokens, expect_json=True, meta=meta or {})
        text = await self.backend.complete(req)
        try:
            return parse_json_object(text)
        except JSONParseError:
            fix = GenerationRequest(
                system="You repair malformed JSON. Output only valid JSON.",
                prompt=f"Fix this into valid JSON with the same content:\n{text[-60000:]}",
                task="repair_json", max_tokens=max_tokens, expect_json=True, meta=meta or {},
            )
            return parse_json_object(await self.backend.complete(fix))

    # ------------------------------------------------------------------ builders
    async def generate_characters(self, p: Project, count: int = 3, hints: str = "", archetype: str | None = None,
                                  role: str | None = None) -> list[Character]:
        data = await self._json(p, prompts.characters_prompt(p, count, hints, archetype, role), "characters",
                                {"count": count, "archetype": archetype})
        out = []
        for raw in data.get("characters", [])[:count]:
            try:
                fields = {k: v for k, v in raw.items() if k in Character.model_fields and k != "id"}
                if role:
                    fields["role"] = role
                out.append(Character(**fields))
            except Exception:
                continue
        return out

    async def generate_world(self, p: Project, hints: str = "") -> World:
        data = await self._json(p, prompts.world_prompt(p, hints), "world", include_outline=False)
        data.setdefault("genre_blend", p.genres)
        return World(**{k: v for k, v in data.items() if k in World.model_fields})

    async def analyze_style(self, p: Project, influences: list[str], sample: str = "") -> StyleProfile:
        data = await self._json(p, prompts.style_prompt(influences, sample), "style", include_outline=False)
        keep = {k: v for k, v in data.items() if k in StyleProfile.model_fields and k not in ("pov", "tense", "influences")}
        return StyleProfile(influences=influences, pov=p.style.pov, tense=p.style.tense, **keep)

    async def generate_outline(self, p: Project) -> PlotOutline:
        n, wpc, acts = plan_dimensions(p)
        povs = [c.name for c in p.characters if c.is_pov] or [c.name for c in p.characters[:1]]
        if p.length_mode == LengthMode.ULTRA:
            return await self._ultra_outline(p, n, wpc, acts, povs)
        data = await self._json(p, prompts.outline_prompt(p, n, wpc), "outline",
                                {"chapters": n, "start": 1, "total": n, "povs": povs}, max_tokens=32000,
                                include_outline=False)
        return self._to_outline(data, n, wpc)

    async def _ultra_outline(self, p: Project, n: int, wpc: int, acts: int, povs: list[str]) -> PlotOutline:
        macro = await self._json(p, prompts.macro_outline_prompt(p, n, acts), "macro_outline",
                                 {"acts": acts, "per_act": n // acts}, include_outline=False)
        act_list = macro.get("acts") or [{"act": a + 1, "summary": "", "chapters": n // acts} for a in range(acts)]
        counts = [max(1, int(a.get("chapters", n // acts))) for a in act_list]
        diff = n - sum(counts)  # normalise so chapter counts add up
        counts[-1] = max(1, counts[-1] + diff)
        outline = self._to_outline({**macro, "chapters": [], "branch_points": []}, n, wpc)
        start = 1
        for act, count in zip(act_list, counts):
            p.outline = outline  # so the bible includes what's planned so far
            prior = "\n".join(f"{c.number}. {c.title}: {c.summary}" for c in outline.chapters[-12:])
            data = await self._json(p, prompts.act_chapters_prompt(p, act, start, count, prior), "outline",
                                    {"chapters": count, "start": start, "total": n, "povs": povs}, max_tokens=32000)
            part = self._to_outline(data, count, wpc, start=start)
            for ch in part.chapters:
                ch.act = int(act.get("act", ch.act))
            outline.chapters.extend(part.chapters)
            outline.branch_points.extend(part.branch_points)
            start += count
        return outline

    def _to_outline(self, data: dict, n: int, wpc: int, start: int = 1) -> PlotOutline:
        subplots = [Subplot(**{k: v for k, v in s.items() if k in Subplot.model_fields and k != "id"})
                    for s in data.get("subplots", []) if isinstance(s, dict) and s.get("name")]
        chapters = []
        for i, raw in enumerate(data.get("chapters", [])[:n]):
            fields = {k: v for k, v in raw.items() if k in ChapterPlan.model_fields}
            fields["number"] = start + i
            fields["target_words"] = wpc
            fields["beats"] = [str(b) for b in fields.get("beats", [])]
            fields["subplots"] = [str(s) for s in fields.get("subplots", [])]
            fields["milestones"] = [str(m) for m in fields.get("milestones", [])]
            chapters.append(ChapterPlan(**fields))
        branches = []
        for b in data.get("branch_points", []):
            try:
                branches.append(BranchPoint(**b))
            except Exception:
                continue
        return PlotOutline(
            logline=data.get("logline", ""), structure=data.get("structure", ""),
            themes=[str(t) for t in data.get("themes", [])], central_question=data.get("central_question", ""),
            twists=[str(t) for t in data.get("twists", [])], climax=data.get("climax", ""),
            ending=data.get("ending", ""), subplots=subplots, chapters=chapters, branch_points=branches,
        )

    async def choose_branch(self, p: Project, index: int, option: int) -> PlotOutline:
        bp = p.outline.branch_points[index]
        bp.chosen = option
        after = bp.after_chapter
        remaining = [c for c in p.outline.chapters if c.number > after]
        if not remaining:
            return p.outline
        opt = bp.options[option]
        wpc = remaining[0].target_words
        povs = [c.name for c in p.characters if c.is_pov]
        data = await self._json(p, prompts.replan_prompt(p, after, f"{bp.question} -> {opt.label}: {opt.consequence}", len(remaining)),
                                "replan", {"chapters": len(remaining), "start": after + 1, "total": len(p.outline.chapters), "povs": povs},
                                max_tokens=32000)
        new = self._to_outline({"chapters": data.get("chapters", [])}, len(remaining), wpc, start=after + 1).chapters
        if len(new) == len(remaining):
            p.outline.chapters = [c for c in p.outline.chapters if c.number <= after] + new
        return p.outline

    async def preview(self, p: Project, instruction: str = "") -> AsyncIterator[str]:
        pov = next((c.name for c in p.characters if c.is_pov), None)
        req = GenerationRequest(system=prompts.bible(p), prompt=prompts.preview_prompt(p, instruction), task="preview",
                                max_tokens=4000, meta={"target_words": 400, "pov": pov})
        async for chunk in self.backend.stream(req):
            yield chunk

    # ------------------------------------------------------------------ manuscript
    async def write(self, p: Project, start: int = 1, end: int | None = None,
                    should_stop: Callable[[], bool] = lambda: False,
                    on_save: Callable[[Project], None] | None = None) -> AsyncIterator[dict]:
        """Write chapters start..end, yielding progress events. Rewrites from `start` onward."""
        warnings = validate_project_content(p)
        for w in warnings:
            yield {"type": "warning", "message": w}
        if not p.outline.chapters:
            yield {"type": "status", "message": "No outline yet; architecting the plot first."}
            p.outline = await self.generate_outline(p)
            if on_save:
                on_save(p)
            yield {"type": "outline", "chapters": len(p.outline.chapters)}
        end = min(end or len(p.outline.chapters), len(p.outline.chapters))
        # Rewriting from `start` invalidates later chapters and the ledger built from them.
        p.chapters = [c for c in p.chapters if c.number < start]
        p.ledger = rebuild_ledger(p, start)
        system = prompts.bible(p)  # stable for the whole run -> cache hits on every call

        for plan in p.outline.chapters[start - 1 : end]:
            if should_stop():
                yield {"type": "stopped", "chapter": plan.number}
                return
            yield {"type": "chapter_start", "chapter": plan.number, "title": plan.title, "pov": plan.pov,
                   "target_words": plan.target_words}
            prev = next((c for c in p.chapters if c.number == plan.number - 1), None)
            prev_tail = prev.text[-2500:] if prev else ""
            nxt = next((c for c in p.outline.chapters if c.number == plan.number + 1), None)
            meta = {"chapter": plan.number, "pov": plan.pov, "target_words": plan.target_words}

            text = ""
            req = GenerationRequest(system=system, prompt=prompts.chapter_prompt(p, plan, prev_tail, nxt),
                                    task="chapter", max_tokens=min(64000, plan.target_words * 4), meta=meta)
            async for chunk in self.backend.stream(req):
                text += chunk
                yield {"type": "delta", "chapter": plan.number, "text": chunk}
                if should_stop():
                    break
            for _ in range(2):  # extend short chapters
                words = len(text.split())
                if should_stop() or words >= plan.target_words * 0.75:
                    break
                yield {"type": "status", "message": f"Chapter {plan.number} is short ({words} words); extending."}
                left = plan.target_words - words
                creq = GenerationRequest(system=system, prompt=prompts.continue_prompt(plan, text[-3000:], left),
                                         task="chapter", max_tokens=min(32000, left * 4), meta={**meta, "target_words": left})
                text += "\n\n"
                yield {"type": "delta", "chapter": plan.number, "text": "\n\n"}
                async for chunk in self.backend.stream(creq):
                    text += chunk
                    yield {"type": "delta", "chapter": plan.number, "text": chunk}

            record = ChapterRecord(number=plan.number, title=plan.title, pov=plan.pov, text=text.strip())
            record.word_count = len(record.text.split())
            await self._extract(p, record, meta)

            if self.check_continuity:
                yield {"type": "status", "message": f"Checking continuity for chapter {plan.number}."}
                record.issues = await self.continuity_issues(p, plan, record.text)
                if record.issues:
                    yield {"type": "issues", "chapter": plan.number, "issues": [i.model_dump() for i in record.issues]}
                severe = [i for i in record.issues if i.severity == "high"]
                if severe and self.auto_revise:
                    yield {"type": "status", "message": f"Revising chapter {plan.number} to fix {len(severe)} serious issue(s)."}
                    record.text = await self.backend.complete(GenerationRequest(
                        system=system, prompt=prompts.revise_prompt(plan, record.text, [i.model_dump() for i in severe]),
                        task="revise", max_tokens=min(64000, plan.target_words * 4), meta=meta))
                    record.text = record.text.strip()
                    record.word_count = len(record.text.split())
                    record.revised = True
                    record.issues = [i for i in record.issues if i.severity != "high"]
                    await self._extract(p, record, meta)
                    yield {"type": "revised", "chapter": plan.number, "text": record.text}

            p.chapters.append(record)
            merge_extraction(p.ledger, record)
            await self._maybe_compress(p)
            if on_save:
                on_save(p)
            yield {"type": "chapter_done", "chapter": plan.number, "word_count": record.word_count,
                   "summary": record.summary, "total_words": p.word_count}
        yield {"type": "done", "total_words": p.word_count, "chapters": len(p.chapters)}

    async def _extract(self, p: Project, record: ChapterRecord, meta: dict) -> None:
        try:
            data = await self._json(p, prompts.extract_prompt(p, record.number, record.text), "extract", meta, max_tokens=8000)
            apply_extraction(record, data)
        except Exception as e:  # bookkeeping failure should not lose the chapter
            record.summary = record.summary or record.text[:600]
            record.issues.append(ContinuityIssue(chapter=record.number, severity="low",
                                                 description=f"Ledger extraction failed: {e}"))

    async def continuity_issues(self, p: Project, plan: ChapterPlan, text: str) -> list[ContinuityIssue]:
        issues = quick_checks(p, plan, text)
        try:
            data = await self._json(p, prompts.continuity_prompt(p, plan.number, text), "continuity",
                                    {"chapter": plan.number}, max_tokens=8000)
            for raw in data.get("issues", []):
                if isinstance(raw, dict) and raw.get("description"):
                    sev = raw.get("severity", "low")
                    issues.append(ContinuityIssue(chapter=plan.number, severity=sev if sev in ("low", "medium", "high") else "low",
                                                  description=str(raw["description"]), suggestion=str(raw.get("suggestion", ""))))
        except Exception:
            pass
        return issues

    async def _maybe_compress(self, p: Project) -> None:
        L = p.ledger
        pending = [c for c in sorted(p.chapters, key=lambda c: c.number) if c.number > L.compressed_through]
        if len(pending) < RECENT_WINDOW + COMPRESS_EVERY:
            return
        fold = pending[:-RECENT_WINDOW]
        req = GenerationRequest(system=prompts.bible(p, include_outline=False),
                                prompt=prompts.compress_prompt(L.story_so_far, [(c.number, c.summary) for c in fold]),
                                task="compress", max_tokens=4000)
        L.story_so_far = (await self.backend.complete(req)).strip()
        L.compressed_through = fold[-1].number

    async def revise_chapter(self, p: Project, number: int, notes: str = "") -> ChapterRecord:
        rec = next(c for c in p.chapters if c.number == number)
        plan = next(c for c in p.outline.chapters if c.number == number)
        issues = [i.model_dump() for i in rec.issues] or [{"severity": "low", "description": "Author-requested revision"}]
        rec.text = (await self.backend.complete(GenerationRequest(
            system=prompts.bible(p), prompt=prompts.revise_prompt(plan, rec.text, issues, notes), task="revise",
            max_tokens=min(64000, plan.target_words * 4), meta={"chapter": number, "pov": plan.pov,
                                                                "target_words": plan.target_words}))).strip()
        rec.word_count = len(rec.text.split())
        rec.revised = True
        rec.issues = []
        await self._extract(p, rec, {"chapter": number, "pov": plan.pov})
        p.ledger = rebuild_ledger(p, 10**9)
        return rec


def run_sync(coro):
    return asyncio.run(coro)
