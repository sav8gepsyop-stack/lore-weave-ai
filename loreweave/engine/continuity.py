"""Continuity: ledger bookkeeping plus fast deterministic checks that run before the model-based review."""

from __future__ import annotations

import difflib
import re

from ..models import ChapterPlan, ChapterRecord, CharacterState, ContinuityIssue, Ledger, Project

DEAD = {"dead", "deceased", "killed", "died"}
_CAP_WORD = re.compile(r"\b[A-Z][a-z]{3,}\b")
COMMON = {
    "They", "There", "Then", "That", "This", "When", "What", "Where", "With", "Without", "Their", "Even", "Every",
    "Some", "Something", "Nothing", "Maybe", "Just", "Still", "After", "Before", "Because", "Behind", "Above",
    "Below", "Inside", "Outside", "Later", "Once", "Again", "Instead", "Perhaps", "Somewhere", "Nobody", "Everyone",
}


def merge_extraction(ledger: Ledger, record: ChapterRecord) -> None:
    """Fold one chapter's extracted facts into the ledger."""
    for f in record.new_facts:
        if f and f not in ledger.facts:
            ledger.facts.append(f)
    for st in record.character_states:
        cur = ledger.characters.get(st.name)
        if cur is None:
            ledger.characters[st.name] = st.model_copy(deep=True)
            continue
        if st.status:
            cur.status = st.status
        if st.location:
            cur.location = st.location
        if st.condition:
            cur.condition = st.condition
        for k in st.knows:
            if k not in cur.knows:
                cur.knows.append(k)
        for item in st.possessions:
            if item not in cur.possessions:
                cur.possessions.append(item)
        cur.relationship_shifts.extend(st.relationship_shifts)
    for t in record.open_threads:
        if t and t not in ledger.open_threads:
            ledger.open_threads.append(t)
    for t in record.threads_resolved:
        match = difflib.get_close_matches(t, ledger.open_threads, n=1, cutoff=0.6)
        if match:
            ledger.open_threads.remove(match[0])
        ledger.resolved_threads.append(t)
    for m in record.milestones_hit:
        if m not in ledger.milestones_hit:
            ledger.milestones_hit.append(m)


def rebuild_ledger(project: Project, upto: int) -> Ledger:
    """Recreate the ledger from chapter records before `upto` (used when rewriting from a chapter)."""
    ledger = Ledger()
    for rec in sorted(project.chapters, key=lambda c: c.number):
        if rec.number >= upto:
            break
        merge_extraction(ledger, rec)
    return ledger


def apply_extraction(record: ChapterRecord, data: dict) -> None:
    record.summary = str(data.get("summary", "")).strip()
    record.new_facts = [str(x) for x in data.get("new_facts", []) if x]
    record.open_threads = [str(x) for x in data.get("threads_opened", []) if x]
    record.threads_resolved = [str(x) for x in data.get("threads_resolved", []) if x]
    record.milestones_hit = [str(x) for x in data.get("milestones_hit", []) if x]
    states = []
    for s in data.get("character_states", []) or []:
        if isinstance(s, dict) and s.get("name"):
            try:
                states.append(CharacterState(**{k: v for k, v in s.items() if k in CharacterState.model_fields}))
            except Exception:
                continue
    record.character_states = states


def _first(name: str) -> str:
    return name.split()[0] if name else name


def quick_checks(project: Project, plan: ChapterPlan, text: str) -> list[ContinuityIssue]:
    issues: list[ContinuityIssue] = []
    n = plan.number
    words = len(text.split())
    if plan.target_words and words < plan.target_words * 0.6:
        issues.append(
            ContinuityIssue(chapter=n, severity="low", description=f"Chapter is short: {words} words vs ~{plan.target_words} planned.",
                            suggestion="Regenerate or extend the chapter.")
        )
    if plan.pov:
        if _first(plan.pov).lower() not in text.lower() and project.style.pov != "first":
            issues.append(
                ContinuityIssue(chapter=n, severity="medium", description=f"Planned POV character '{plan.pov}' is never named in the chapter.",
                                suggestion="Check the chapter is told from the planned POV.")
            )
    for st in project.ledger.characters.values():
        if st.status.lower() in DEAD:
            first = _first(st.name)
            if re.search(rf"\b{re.escape(first)}\b\s+(said|says|asked|replied|shouted|whispered|smiled|walked|ran)", text):
                issues.append(
                    ContinuityIssue(chapter=n, severity="high", description=f"{st.name} is dead in the ledger but appears to act or speak.",
                                    suggestion="Make it a memory/flashback or remove the appearance.")
                )
    known = {c.name for c in project.characters} | {_first(c.name) for c in project.characters}
    known |= {l.name for l in project.world.locations}
    counts: dict[str, int] = {}
    for w in _CAP_WORD.findall(text):
        if w not in known and w not in COMMON:
            counts[w] = counts.get(w, 0) + 1
    firsts = [_first(c.name) for c in project.characters]
    for w, cnt in counts.items():
        close = difflib.get_close_matches(w, firsts, n=1, cutoff=0.84)
        if close and close[0] != w:
            issues.append(
                ContinuityIssue(chapter=n, severity="medium", description=f"Possible name drift: '{w}' ({cnt}x) looks like '{close[0]}'.",
                                suggestion=f"Replace '{w}' with '{close[0]}' if it is the same character.")
            )
    return issues
