"""Prompt builders.

The system prompt is the *story bible*: stable across a writing run so backends can cache it.
Volatile context (ledger, recent chapters, the current chapter plan) goes in the user prompt.
"""

from __future__ import annotations

import json

from ..archetypes import archetype_brief
from ..content import content_instructions, minor_guard_text
from ..genres import STRUCTURES, combat_brief, genre_brief
from ..models import ChapterPlan, Character, LengthMode, Project
from ..style import style_instructions

ROLE = (
    "You are Lore Weave, a master novelist and story architect collaborating with an author. You write "
    "immersive long-form fiction with layered characters, coherent worlds and earned emotional payoffs. "
    "You keep strict continuity with the story bible and the continuity ledger. Casts are diverse in "
    "culture, gender, body, class and temperament, and every character is written as a specific person "
    "rather than a stereotype."
)


def _character_block(c: Character, full: bool = True) -> str:
    bits = [f"### {c.name} ({c.role}{', POV' if c.is_pov else ''})"]
    fields = [
        ("Age", c.age),
        ("Pronouns", c.pronouns),
        ("Archetype", archetype_brief(c.archetype) if c.archetype else ""),
        ("Appearance", c.appearance),
        ("Background", c.cultural_background),
        ("Backstory", c.backstory),
        ("Motivation", c.motivation),
        ("Fear", c.fear),
        ("Wound", c.wound),
        ("Want vs need", c.want_vs_need),
        ("Psychology", c.psychology),
        ("Voice", c.voice),
        ("Skills", ", ".join(c.skills)),
        ("Flaws", ", ".join(c.flaws)),
        ("Arc", c.arc),
    ]
    for k, v in fields:
        if v not in (None, "", []):
            if not full and k in ("Backstory", "Psychology", "Appearance"):
                v = str(v)[:240]
            bits.append(f"- {k}: {v}")
    if c.relationships:
        bits.append("- Relationships: " + "; ".join(f"{r.kind} of {r.target}" + (f" ({r.dynamic})" if r.dynamic else "") for r in c.relationships))
    if c.milestones:
        bits.append(
            "- Milestones: "
            + "; ".join((f"ch{m.chapter}: " if m.chapter else "") + m.description for m in c.milestones)
        )
    return "\n".join(bits)


def world_block(p: Project) -> str:
    w = p.world
    parts = [f"## WORLD: {w.name or 'Untitled setting'}"]
    for label, val in [
        ("Era", w.era),
        ("Genre blend", ", ".join(w.genre_blend or p.genres)),
        ("Premise", w.premise),
        ("Geography", w.geography),
        ("Politics", w.politics),
        ("Economy", w.economy),
        ("Mythology", w.mythology),
        ("Magic / technology", w.magic_or_tech),
        ("Cultural norms", w.cultural_norms),
        ("Languages", w.languages),
        ("History", w.history),
        ("Sensory palette", w.sensory_palette),
    ]:
        if val:
            parts.append(f"- {label}: {val}")
    if w.locations:
        parts.append("- Locations: " + "; ".join(f"{l.name} ({l.description})" for l in w.locations))
    if w.factions:
        parts.append("- Factions: " + "; ".join(f"{f.name}: {f.goals}" for f in w.factions))
    if w.power_rules:
        parts.append("- HARD RULES that must never be broken: " + " | ".join(w.power_rules))
    return "\n".join(parts)


def outline_block(p: Project, compact: bool = True) -> str:
    o = p.outline
    if not o.chapters and not o.logline:
        return ""
    parts = ["## PLOT"]
    for label, val in [
        ("Logline", o.logline),
        ("Structure", STRUCTURES.get(o.structure, o.structure)),
        ("Themes", ", ".join(o.themes)),
        ("Central question", o.central_question),
        ("Planned twists", "; ".join(o.twists)),
        ("Climax", o.climax),
        ("Ending", o.ending),
    ]:
        if val:
            parts.append(f"- {label}: {val}")
    for sp in o.subplots:
        parts.append(f"- Subplot [{sp.id}] {sp.name}: {sp.description} -> {sp.resolution}")
    if o.chapters:
        parts.append("### Chapter map")
        for ch in o.chapters:
            line = f"{ch.number}. {ch.title} [POV: {ch.pov}] {ch.summary}"
            parts.append(line[:300] if compact else line)
    for bp in o.branch_points:
        if bp.chosen is not None:
            opt = bp.options[bp.chosen]
            parts.append(f"- Branch chosen after ch{bp.after_chapter}: {bp.question} -> {opt.label}: {opt.consequence}")
    return "\n".join(parts)


def bible(p: Project, include_outline: bool = True) -> str:
    """The cached system prompt: everything stable about the story."""
    sections = [
        ROLE,
        f"# STORY BIBLE: {p.title}",
        f"Genres: {', '.join(p.genres)}\n{genre_brief(p.genres)}",
    ]
    if p.premise:
        sections.append(f"Premise: {p.premise}")
    if p.audience_notes:
        sections.append(f"Author notes: {p.audience_notes}")
    sections.append(world_block(p))
    if p.characters:
        sections.append("## CHARACTERS\n" + "\n\n".join(_character_block(c) for c in p.characters))
    sections.append(style_instructions(p.style))
    sections.append(content_instructions(p.content))
    guard = minor_guard_text(p)
    if guard:
        sections.append(guard)
    cs = p.conflict
    sections.append(
        "CONFLICT & ACTION:\n"
        f"- Combat conventions: {combat_brief(p.genres, cs.combat_system)}\n"
        f"- Roughly {int(cs.action_ratio * 100)}% of page time on action; stakes escalation: {cs.stakes_escalation}.\n"
        "- Every fight should change something: a relationship, a belief, a resource, a body. "
        "Balance spectacle with the POV character's emotional experience."
        + ("\n- Injuries, losses and costs persist into later chapters." if cs.emphasize_consequences else "")
    )
    if include_outline:
        ob = outline_block(p)
        if ob:
            sections.append(ob)
    return "\n\n".join(s for s in sections if s)


# ---------------------------------------------------------------------------
# Builders for each task
# ---------------------------------------------------------------------------

JSON_RULE = "Respond with a single JSON object only, no prose before or after, no markdown fences."


def characters_prompt(p: Project, count: int, hints: str, archetype: str | None, role: str | None) -> str:
    existing = ", ".join(f"{c.name} ({c.role})" for c in p.characters) or "none yet"
    return f"""Create {count} new character(s) for this story.
Existing cast: {existing}.
Author's request: {hints or 'Fill the most important gaps in the cast.'}
{f'Required archetype: {archetype_brief(archetype)}' if archetype else ''}
{f'Required role: {role}' if role else ''}

Make each character layered: a formative wound, a want that conflicts with their need, a specific
cultural background rendered with lived detail (not stereotype), a distinctive speaking voice, and an
arc with 2-4 milestones. Archetypes are starting shapes; give each one a twist that makes it a person.
Vary cultures, genders, body types, ages and temperaments across the cast. Default to adult ages
unless the author specifies otherwise. Relationships may reference existing characters.

{JSON_RULE}
Schema: {{"characters": [{{"name": str, "role": "protagonist|deuteragonist|antagonist|supporting|npc", "age": int, "pronouns": str,
"archetype": str, "appearance": str, "cultural_background": str, "backstory": str, "motivation": str, "fear": str,
"wound": str, "want_vs_need": str, "psychology": str, "voice": str, "skills": [str], "flaws": [str], "arc": str,
"relationships": [{{"target": str, "kind": str, "dynamic": str}}], "milestones": [{{"description": str}}], "is_pov": bool}}]}}"""


def world_prompt(p: Project, hints: str) -> str:
    return f"""Design the world for this story.
Genres to blend: {', '.join(p.genres)}. Premise: {p.premise or '(author has not set one; invent a compelling one)'}
Author's request: {hints or 'Build a setting that generates conflict for this cast.'}

Cover geography, politics and factions with competing goals, economy, mythology/faith, the magic or
technology system with concrete costs and limits, cultural norms, languages, history and a recurring
sensory palette. Cultures should be internally diverse and drawn with specificity; avoid mapping
fictional peoples onto real-world ethnic stereotypes. Include 3-6 "power_rules": hard constraints
the story must never break.

{JSON_RULE}
Schema: {{"name": str, "era": str, "premise": str, "geography": str, "locations": [{{"name": str, "description": str, "significance": str}}],
"politics": str, "factions": [{{"name": str, "goals": str, "methods": str, "relations": str}}], "economy": str, "mythology": str,
"magic_or_tech": str, "power_rules": [str], "cultural_norms": str, "languages": str, "history": str, "sensory_palette": str}}"""


def style_prompt(influences: list[str], sample: str = "") -> str:
    infl = ", ".join(influences)
    sample_part = (
        f"\nThe author also supplied a sample of the voice they want (analyse it, do not continue it):\n<sample>\n{sample[:6000]}\n</sample>\n"
        if sample
        else ""
    )
    return f"""Build a style profile from these literary influences: {infl}.{sample_part}
Describe the observable craft techniques: sentence structure and rhythm, vocabulary register, pacing,
dialogue habits, imagery, narrative voice, and signature devices. If several influences are listed,
synthesise a single coherent voice. If an influence is not a writer you recognise (for example a band,
a game, or a misspelt name), infer the mood it suggests and say so in the summary.
Describe techniques only. Do not quote, paraphrase or reproduce any passages from their works.

{JSON_RULE}
Schema: {{"summary": str, "sentence_structure": str, "vocabulary": str, "pacing": str, "dialogue": str, "imagery": str,
"narrative_voice": str, "signature_devices": [str], "avoid": [str]}}"""


def _ultra_rules(p: Project) -> str:
    if p.length_mode != LengthMode.ULTRA:
        return ""
    povs = [c.name for c in p.characters if c.is_pov] or [c.name for c in p.characters[:3]]
    return f"""ULTRA MODE requirements:
- Multi-POV: rotate between these POV characters with purpose: {', '.join(povs)}. Each POV has its own arc and voice.
- At least 3 subplots that braid into the main plot and pay off before or at the climax.
- Map each character's milestones to specific chapters so growth is paced across the whole book.
- Use act breaks, midpoint reversal, and at least two major twists set up early with fair clues."""


def outline_prompt(p: Project, n_chapters: int, words_per_chapter: int) -> str:
    povs = [c.name for c in p.characters if c.is_pov] or [c.name for c in p.characters[:1]]
    return f"""Architect the full plot for a {p.target_pages}-page novel (about {p.target_words:,} words) in exactly {n_chapters} chapters of roughly {words_per_chapter:,} words each.

Requirements:
- Choose the structure that best serves the genre blend (three_act, kishotenketsu, heros_journey, five_act or romance_beats).
- Every chapter has a purpose: it changes the situation, reveals character, or raises stakes. Name 3-6 beats per chapter.
- Plant set-ups early and pay them off; twists must be surprising yet inevitable in hindsight.
- Themes recur and deepen; the climax tests the protagonist's central flaw.
- POV characters available: {', '.join(povs)}.
- Mark chapters with significant action (has_action) so conflict is spread with breathing room.
- Include 1-3 branch points: key decisions where the story could fork, each with 2-3 options and consequences.
{_ultra_rules(p)}

{JSON_RULE}
Schema: {{"logline": str, "structure": str, "themes": [str], "central_question": str, "twists": [str], "climax": str, "ending": str,
"subplots": [{{"name": str, "description": str, "characters": [str], "resolution": str}}],
"chapters": [{{"number": int, "title": str, "pov": str, "act": int, "summary": str, "beats": [str], "subplots": [str], "has_action": bool, "milestones": [str]}}],
"branch_points": [{{"after_chapter": int, "question": str, "options": [{{"label": str, "consequence": str}}]}}]}}"""


def macro_outline_prompt(p: Project, n_chapters: int, acts: int) -> str:
    return f"""Architect the macro structure for an ULTRA-length novel: {p.target_pages} pages (~{p.target_words:,} words), {n_chapters} chapters, {acts} acts.
{_ultra_rules(p)}
Plan the themes, the central question, twists (with where their clues are planted), the climax and ending,
at least 3 subplots, and a summary of what each act accomplishes plus how many chapters it gets
(chapter counts must add up to {n_chapters}).

{JSON_RULE}
Schema: {{"logline": str, "structure": str, "themes": [str], "central_question": str, "twists": [str], "climax": str, "ending": str,
"subplots": [{{"name": str, "description": str, "characters": [str], "resolution": str}}],
"acts": [{{"act": int, "summary": str, "chapters": int}}]}}"""


def act_chapters_prompt(p: Project, act: dict, start: int, count: int, prior: str) -> str:
    return f"""Plan the chapters for Act {act.get('act')} of this novel: "{act.get('summary', '')}".
Produce exactly {count} chapters numbered {start} to {start + count - 1}.
Chapters already planned in earlier acts:
{prior or '(none)'}

Advance the subplots (reference them by name or id), rotate POVs with purpose, place character milestones,
and end the act on a turn that propels the next one. Include 0-2 branch points inside this act.

{JSON_RULE}
Schema: {{"chapters": [{{"number": int, "title": str, "pov": str, "act": int, "summary": str, "beats": [str], "subplots": [str], "has_action": bool, "milestones": [str]}}],
"branch_points": [{{"after_chapter": int, "question": str, "options": [{{"label": str, "consequence": str}}]}}]}}"""


def replan_prompt(p: Project, after: int, choice_text: str, remaining: int) -> str:
    return f"""The author chose a branch after chapter {after}: {choice_text}
Re-plan chapters {after + 1} to {after + remaining} so the story follows this choice while still reaching a
satisfying climax consistent with the themes, world rules and character arcs. Keep the same chapter count.

{JSON_RULE}
Schema: {{"chapters": [{{"number": int, "title": str, "pov": str, "act": int, "summary": str, "beats": [str], "subplots": [str], "has_action": bool, "milestones": [str]}}]}}"""


def ledger_block(p: Project, recent_window: int = 3, upto: int | None = None) -> str:
    L = p.ledger
    done = [c for c in p.chapters if c.text and (upto is None or c.number < upto)]
    parts = ["## CONTINUITY LEDGER (canon so far; never contradict it)"]
    if L.story_so_far:
        parts.append(f"### Story so far (chapters 1-{L.compressed_through})\n{L.story_so_far}")
    recent = [c for c in done if c.number > L.compressed_through][-max(recent_window, 1) :]
    older_uncompressed = [c for c in done if c.number > L.compressed_through and c not in recent]
    for c in older_uncompressed + recent:
        parts.append(f"### Chapter {c.number} summary ({c.pov})\n{c.summary}")
    if L.characters:
        parts.append("### Character states")
        for s in L.characters.values():
            line = f"- {s.name}: {s.status}"
            if s.location:
                line += f", at {s.location}"
            if s.condition:
                line += f"; {s.condition}"
            if s.knows:
                line += f"; knows: {', '.join(s.knows[-6:])}"
            if s.possessions:
                line += f"; has: {', '.join(s.possessions[-6:])}"
            parts.append(line)
    if L.facts:
        parts.append("### Established facts\n" + "\n".join(f"- {f}" for f in L.facts[-40:]))
    if L.open_threads:
        parts.append("### Open threads to keep alive or pay off\n" + "\n".join(f"- {t}" for t in L.open_threads[-20:]))
    if L.milestones_hit:
        parts.append("### Milestones already reached\n" + "\n".join(f"- {m}" for m in L.milestones_hit[-20:]))
    return "\n\n".join(parts)


def chapter_prompt(p: Project, plan: ChapterPlan, prev_tail: str, next_plan: ChapterPlan | None) -> str:
    pov = p.character(plan.pov) if plan.pov else None
    sub_names = []
    for sid in plan.subplots:
        sp = next((s for s in p.outline.subplots if s.id == sid or s.name == sid), None)
        sub_names.append(f"{sp.name}: {sp.description}" if sp else sid)
    branch_note = ""
    for bp in p.outline.branch_points:
        if bp.chosen is not None and bp.after_chapter < plan.number:
            o = bp.options[bp.chosen]
            branch_note += f"\n- Story follows the branch '{o.label}' ({o.consequence})."
    return f"""{ledger_block(p, upto=plan.number)}

## PREVIOUS CHAPTER ENDING (continue seamlessly from here)
{prev_tail or '(This is the opening chapter. Open with a strong hook that establishes voice, world and the POV character's desire.)'}

## WRITE CHAPTER {plan.number}: {plan.title}
- POV: {plan.pov or 'as planned'}{f' (voice: {pov.voice})' if pov and pov.voice else ''}
- Purpose: {plan.summary}
- Beats, in order: {' | '.join(plan.beats) or 'as fits the purpose'}
{('- Subplots to advance: ' + ' | '.join(sub_names)) if sub_names else ''}
{('- Character milestones to land here: ' + ' | '.join(plan.milestones)) if plan.milestones else ''}
{'- This chapter features significant action: stage it clearly (space, stakes, turns) and let it change something.' if plan.has_action else ''}{branch_note}
{f'- Set up (without spoiling) the next chapter: {next_plan.summary}' if next_plan else '- This is the final chapter: resolve the central question and the main arcs with an earned ending.'}

Length: about {plan.target_words:,} words. Write in full scenes with dialogue, interiority and sensory
grounding; dramatise rather than summarise. Keep every name, rule, injury, location and relationship
consistent with the bible and ledger. Output only the chapter prose: no title, no notes, no commentary."""


def continue_prompt(plan: ChapterPlan, so_far_tail: str, words_left: int) -> str:
    return f"""Continue chapter {plan.number} ("{plan.title}") from exactly where it stops below, for about {words_left:,} more words,
completing the remaining beats: {' | '.join(plan.beats)}. Output only the continuation prose.

<chapter_so_far_tail>
{so_far_tail}
</chapter_so_far_tail>"""


def extract_prompt(p: Project, number: int, text: str) -> str:
    names = ", ".join(c.name for c in p.characters)
    return f"""Read chapter {number} below and update the continuity ledger.
Known characters: {names}.

<chapter>
{text}
</chapter>

Return: a 120-200 word summary focused on plot changes and emotional shifts; new canon facts (concrete
and checkable: names, places, rules revealed, deaths, injuries, promises, objects); the state of every
character who appears; story threads opened and resolved; and character milestones reached.

{JSON_RULE}
Schema: {{"summary": str, "new_facts": [str], "character_states": [{{"name": str, "status": str, "location": str, "condition": str,
"knows": [str], "possessions": [str], "relationship_shifts": [str]}}], "threads_opened": [str], "threads_resolved": [str], "milestones_hit": [str]}}"""


def continuity_prompt(p: Project, number: int, text: str) -> str:
    return f"""{ledger_block(p, upto=number)}

Act as a meticulous continuity editor. Compare chapter {number} below against the story bible (world rules,
character profiles, ages, voices, content settings) and the continuity ledger above.

<chapter>
{text}
</chapter>

Report only real problems: contradictions of established facts, dead or absent characters acting, broken
world/power rules, characters acting against their established psychology without cause, timeline errors,
POV slips, voice drift from the style profile, and content beyond the author's settings. Ignore matters of taste.

{JSON_RULE}
Schema: {{"issues": [{{"severity": "low|medium|high", "description": str, "suggestion": str}}]}}"""


def revise_prompt(plan: ChapterPlan, text: str, issues: list[dict], author_notes: str = "") -> str:
    return f"""Revise chapter {plan.number} ("{plan.title}") to fix the problems listed, keeping everything else
(voice, length, events that are not in question) as close to the original as possible.

Problems:
{json.dumps(issues, indent=1)}
{f'Author notes: {author_notes}' if author_notes else ''}

<chapter>
{text}
</chapter>

Output only the full revised chapter prose."""


def compress_prompt(prev_summary: str, summaries: list[tuple[int, str]]) -> str:
    joined = "\n".join(f"Chapter {n}: {s}" for n, s in summaries)
    return f"""Merge the existing 'story so far' with the new chapter summaries into a single compressed recap of
350-700 words. Preserve every plot-critical fact, unresolved thread, relationship change, injury, death, secret
and promise; drop scene-level detail. Output only the recap.

Existing story so far:
{prev_summary or '(none)'}

New chapter summaries:
{joined}"""


def preview_prompt(p: Project, instruction: str) -> str:
    pov = next((c for c in p.characters if c.is_pov), p.characters[0] if p.characters else None)
    return f"""Write a ~400 word preview scene so the author can feel the voice, tone and content settings before
committing to a full manuscript. {f'POV: {pov.name}.' if pov else ''}
{instruction or 'Make it an evocative opening scene that introduces the POV character and the world.'}
Output only the prose."""
