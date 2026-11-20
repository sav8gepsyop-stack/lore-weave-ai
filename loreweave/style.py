"""Style Infusion: style presets and the style-instruction renderer.

"Copy Author" works by describing an influence's *techniques* (syntax, diction, pacing, devices)
as a StyleProfile. The engine writes original prose guided by those descriptors; it never asks the
model to quote or reproduce an author's text.
"""

from __future__ import annotations

from .models import StyleProfile

PRESETS: dict[str, dict] = {
    "mythic_epic": {
        "summary": "Elevated, mythic register with a sense of deep history.",
        "sentence_structure": "Long, rolling sentences with balanced clauses; occasional archaic inversion for gravity.",
        "vocabulary": "Old-root English words, place names with invented etymology, songs and lineages.",
        "pacing": "Unhurried travel and landscape, with sudden dread and swift battle.",
        "dialogue": "Formal, oath-laden, proverbs and courtesies that reveal culture.",
        "imagery": "Landscape as character; light and shadow, trees, stone, stars.",
        "narrative_voice": "Omniscient chronicler with warmth.",
        "signature_devices": ["embedded songs or verse", "appendix-like lore asides kept brief"],
        "avoid": ["modern slang", "snark"],
    },
    "light_novel": {
        "summary": "Brisk, character-forward prose in the manner of Japanese light novels and manga adaptations.",
        "sentence_structure": "Short paragraphs, frequent single-line beats, punchy reaction lines.",
        "vocabulary": "Accessible and vivid; named techniques; occasional untranslated honorifics if the setting is Japanese.",
        "pacing": "Fast; each scene ends on a reaction or hook.",
        "dialogue": "Dialogue-heavy, with distinct verbal tics per character.",
        "imagery": "Panel-like staging: establishing shot, close-up, reaction.",
        "narrative_voice": "Close first or third person with candid inner commentary.",
        "signature_devices": ["inner monologue asides", "dramatic reveal lines on their own paragraph"],
        "avoid": ["long exposition blocks"],
    },
    "street_lit_voice": {
        "summary": "Voice-driven urban narration with rhythm, humour and heat.",
        "sentence_structure": "Conversational cadence; run-ons for momentum, fragments for impact.",
        "vocabulary": "Contemporary, regionally specific idiom used authentically, never as caricature.",
        "pacing": "Momentum-driven; tension builds through pressure from many sides.",
        "dialogue": "Sharp, layered, full of callbacks and code-switching where it fits the character.",
        "imagery": "Specific city texture: corner stores, transit, music, food, weather.",
        "narrative_voice": "First person confessional or close third with attitude.",
        "signature_devices": ["direct address to reader", "chapter-opening hooks"],
        "avoid": ["stereotyped dialect spelling"],
    },
    "hardboiled_noir": {
        "summary": "Terse, wry, atmospheric noir.",
        "sentence_structure": "Short declaratives; similes with bite.",
        "vocabulary": "Plain words, hard edges, period or genre slang sparingly.",
        "pacing": "Steady investigation punctuated by sudden violence.",
        "dialogue": "Clipped, evasive, everyone lying a little.",
        "imagery": "Rain, neon, smoke, cheap rooms.",
        "narrative_voice": "Cynical first person.",
        "signature_devices": ["wisecrack under pressure", "bleak aphorism"],
        "avoid": ["melodrama"],
    },
    "literary_minimalist": {
        "summary": "Spare, precise, emotionally restrained prose where subtext carries the weight.",
        "sentence_structure": "Simple sentences, careful repetition.",
        "vocabulary": "Plain and exact.",
        "pacing": "Measured; white space does work.",
        "dialogue": "Understated, oblique.",
        "imagery": "Few, precise images.",
        "narrative_voice": "Detached close third.",
        "signature_devices": ["iceberg subtext"],
        "avoid": ["explaining emotions"],
    },
    "lush_romantic": {
        "summary": "Sensory, emotionally rich prose focused on longing and connection.",
        "sentence_structure": "Flowing sentences that slow down at emotional peaks.",
        "vocabulary": "Sensory and evocative; touch, scent, warmth.",
        "pacing": "Slow-burn with escalating tension.",
        "dialogue": "Banter and vulnerable confessions.",
        "imagery": "Body language, light, intimate details.",
        "narrative_voice": "Dual close third or first person.",
        "signature_devices": ["alternating POV", "charged pauses"],
        "avoid": ["clinical description"],
    },
}


def preset_profile(key: str, **overrides) -> StyleProfile:
    data = dict(PRESETS[key])
    data.update(overrides)
    return StyleProfile(**data)


def style_instructions(s: StyleProfile) -> str:
    pov_text = {
        "first": "first person",
        "third_limited": "close third person, limited to the chapter's POV character",
        "third_omniscient": "third person omniscient",
        "second": "second person",
    }[s.pov]
    lines = [f"PROSE STYLE: {pov_text}, {s.tense} tense."]
    if s.influences:
        lines.append(
            "Influences (emulate technique only; write wholly original sentences and never quote or "
            "closely paraphrase their published work): " + ", ".join(s.influences)
        )
    for label, val in [
        ("Overall", s.summary),
        ("Sentence structure", s.sentence_structure),
        ("Vocabulary", s.vocabulary),
        ("Pacing", s.pacing),
        ("Dialogue", s.dialogue),
        ("Imagery", s.imagery),
        ("Narrative voice", s.narrative_voice),
    ]:
        if val:
            lines.append(f"- {label}: {val}")
    if s.signature_devices:
        lines.append("- Devices: " + "; ".join(s.signature_devices))
    if s.avoid:
        lines.append("- Avoid: " + "; ".join(s.avoid))
    return "\n".join(lines)
