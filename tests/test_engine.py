import asyncio

import pytest

from loreweave.backends.mock import MockBackend
from loreweave.content import ContentPolicyError, content_instructions, validate_project_content
from loreweave.engine.core import LoreWeaveEngine, plan_dimensions
from loreweave.engine.jsonutil import parse_json_object
from loreweave.export import to_epub, to_markdown
from loreweave.models import Character, ContentSettings, LengthMode, Project, Relationship, RomanceLevel


def run(c):
    return asyncio.run(c)


async def build(p, engine):
    p.characters = await engine.generate_characters(p, 3)
    p.world = await engine.generate_world(p)
    p.style = await engine.analyze_style(p, ["Ursula K. Le Guin"])
    p.outline = await engine.generate_outline(p)
    return [ev async for ev in engine.write(p)]


def test_plan_dimensions_standard_and_ultra():
    p = Project(target_pages=75)
    n, wpc, acts = plan_dimensions(p)
    assert 6 <= n <= 12 and acts == 3 and n * wpc >= p.target_words
    u = Project(length_mode=LengthMode.ULTRA, target_pages=120)
    n, wpc, acts = plan_dimensions(u)
    assert u.target_pages == 200 and n >= 24


def test_standard_manuscript_end_to_end():
    p = Project(title="Test", genres=["manga", "urban"], target_pages=50)
    events = run(build(p, LoreWeaveEngine(MockBackend())))
    assert events[-1]["type"] == "done"
    assert len(p.chapters) == len(p.outline.chapters)
    assert all(c.summary for c in p.chapters)
    assert p.ledger.facts and p.ledger.characters
    assert p.ledger.compressed_through > 0  # rolling summary kicked in
    assert "## Chapter 1" in to_markdown(p)
    assert to_epub(p)[:2] == b"PK"


def test_ultra_outline_is_hierarchical():
    p = Project(length_mode=LengthMode.ULTRA, target_pages=220, genres=["fantasy"])
    e = LoreWeaveEngine(MockBackend())

    async def go():
        p.characters = await e.generate_characters(p, 3)
        return await e.generate_outline(p)

    o = run(go())
    n, _, _ = plan_dimensions(p)
    assert len(o.chapters) == n
    assert [c.number for c in o.chapters] == list(range(1, n + 1))
    assert len(o.subplots) >= 2


def test_rewrite_from_middle_rebuilds_ledger():
    p = Project(target_pages=40)
    e = LoreWeaveEngine(MockBackend())
    run(build(p, e))
    total = len(p.chapters)

    async def rewrite():
        return [ev async for ev in e.write(p, start=3)]

    run(rewrite())
    assert sorted(c.number for c in p.chapters) == list(range(1, total + 1))


def test_branch_replans_later_chapters():
    p = Project(target_pages=60)
    e = LoreWeaveEngine(MockBackend())

    async def go():
        p.characters = await e.generate_characters(p, 2)
        p.outline = await e.generate_outline(p)
        return await e.choose_branch(p, 0, 1)

    o = run(go())
    assert o.branch_points[0].chosen == 1
    assert [c.number for c in o.chapters] == list(range(1, len(o.chapters) + 1))


def test_minor_cannot_be_in_sensual_romance():
    p = Project(content=ContentSettings(romance=RomanceLevel.SENSUAL))
    p.characters = [
        Character(name="Aki", age=16, relationships=[Relationship(target="Ren", kind="love interest")]),
        Character(name="Ren", age=19),
    ]
    with pytest.raises(ContentPolicyError):
        validate_project_content(p)
    p.content.romance = RomanceLevel.ROMANTIC
    assert validate_project_content(p)  # allowed, with a warning


def test_content_instructions_always_include_hard_rules():
    text = content_instructions(ContentSettings(romance=RomanceLevel.EXPLICIT))
    assert "under 18" in text and "consenting adults" in text


def test_json_parse_tolerates_fences_and_trailing_commas():
    assert parse_json_object('Here:\n```json\n{"a": [1, 2,],}\n```') == {"a": [1, 2]}
