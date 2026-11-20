"""Genre conventions, combat systems and structure presets.

Genres can be blended freely ("sci-fi noir", "urban fantasy manga"); the engine merges the
conventions of every selected genre into the story bible.
"""

from __future__ import annotations

GENRES: dict[str, dict] = {
    "manga": {
        "label": "Manga-style",
        "conventions": [
            "Strong visual staging: describe scenes like panels, with clear establishing shots, close-ups and reaction beats",
            "Emotional beats are heightened and named; internal monologue is vivid and immediate",
            "Chapter endings land on a hook, reveal or striking image",
            "Ensemble dynamics, rivalries and found family matter as much as plot",
            "Power progression and training arcs, where present, follow clear and consistent rules",
        ],
        "structure": "kishotenketsu or arc-based shonen/shojo/seinen pacing",
        "combat": "Named techniques with visible costs and counters; fights turn on insight, resolve and the rules of the power system, not just raw strength. Use pre-fight tension, an exchange, a turn where the loser adapts, and an emotional climax.",
        "pitfalls": ["Avoid fan-service framing of characters", "Avoid stereotyped foreign/ethnic side characters"],
    },
    "urban": {
        "label": "Urban fiction",
        "conventions": [
            "A specific, lived-in city: named blocks, local businesses, transit lines, weather, music",
            "Voice-driven narration and dialogue with authentic rhythm, without caricature",
            "Pressures of money, family, loyalty, ambition and systems (housing, policing, work) shape choices",
            "Community is a character: neighbours, crews, churches, barbershops, group chats",
        ],
        "structure": "rising-pressure three-act with a reckoning",
        "combat": "Grounded, fast and messy confrontations; violence has legal, physical and emotional fallout that ripples through community and family. Prefer tension and de-escalation choices over spectacle.",
        "pitfalls": ["No crime-as-default for characters of colour", "Give characters careers, humour, dreams and tenderness"],
    },
    "fantasy": {
        "label": "Fantasy",
        "conventions": [
            "A magic or power system with clear costs and limits",
            "Cultures, faiths and politics that feel historically layered",
            "A sense of wonder balanced against grounded stakes",
            "Geography matters: travel takes time and terrain shapes conflict",
        ],
        "structure": "hero's journey or three-act with multiple arcs",
        "combat": "Magical duels follow the magic system's rules: preparation, counters, resource costs (stamina, mana, lifespan, memory). Battles mix tactics, terrain and morale; a duel should reveal character through choices made under pressure.",
        "pitfalls": ["Avoid coding non-human races as real-world ethnic stereotypes", "Avoid always-evil peoples"],
    },
    "scifi": {
        "label": "Science fiction",
        "conventions": [
            "One or two big speculative ideas explored for their human consequences",
            "Consistent technology rules; science-informed even when soft",
            "Social systems shaped by the technology",
        ],
        "structure": "three-act or investigative structure",
        "combat": "Tech-driven tactics: sensors, range, latency, power budgets, hacking. Ship and mech combat emphasise positioning and crew coordination.",
        "pitfalls": ["Avoid techno-orientalism"],
    },
    "noir": {
        "label": "Noir",
        "conventions": [
            "Moral ambiguity and institutional corruption",
            "Atmospheric narration: shadows, rain, neon, cigarette-smoke similes used sparingly",
            "An investigation that reveals something rotten",
            "Endings are bittersweet at best",
        ],
        "structure": "investigation with escalating revelations",
        "combat": "Short, brutal and consequential. Fights are ugly and lose the protagonist something.",
        "pitfalls": ["Avoid femme-fatale and corrupt-foreigner cliches"],
    },
    "romance": {
        "label": "Romance",
        "conventions": [
            "The relationship is the spine of the plot",
            "Tension through competing goals, not miscommunication alone",
            "An emotionally satisfying ending (HEA/HFN) unless the user asks otherwise",
        ],
        "structure": "romance beat sheet: meet, attraction, deepening, crisis, grand gesture, resolution",
        "combat": "Conflict is mostly emotional; external threats test the bond.",
        "pitfalls": ["Consent and mutual respect on the page"],
    },
    "horror": {
        "label": "Horror",
        "conventions": ["Dread over gore", "Rules of the threat revealed gradually", "Isolation and vulnerability"],
        "structure": "escalating dread with a final confrontation",
        "combat": "Characters are outmatched; survival depends on wit and sacrifice.",
        "pitfalls": ["Avoid mental illness as monstrousness"],
    },
    "historical": {
        "label": "Historical",
        "conventions": ["Period-accurate detail", "Social constraints of the era drive conflict", "Avoid anachronistic attitudes without comment"],
        "structure": "three-act grounded in real events",
        "combat": "Period weapons and tactics; injury and medicine reflect the era.",
        "pitfalls": ["Represent marginalised people of the era with agency and depth"],
    },
    "mystery": {
        "label": "Mystery",
        "conventions": ["Fair-play clues", "Red herrings", "A satisfying, logical reveal"],
        "structure": "crime, investigation, reveal",
        "combat": "Rare; confrontations are verbal and psychological.",
        "pitfalls": [],
    },
    "cyberpunk": {
        "label": "Cyberpunk",
        "conventions": ["High tech, low life", "Corporate power", "Body modification and identity"],
        "structure": "heist or investigation",
        "combat": "Augment-driven, fast, with hacking duels in parallel to physical fights.",
        "pitfalls": ["Avoid techno-orientalism"],
    },
}

STRUCTURES = {
    "three_act": "Setup (25%), confrontation (50%) with a midpoint reversal, resolution (25%).",
    "kishotenketsu": "Introduction, development, twist (a turn that recontextualises), reconciliation.",
    "heros_journey": "Ordinary world, call, refusal, mentor, threshold, trials, ordeal, reward, road back, resurrection, return.",
    "five_act": "Exposition, rising action, climax, falling action, catastrophe/denouement.",
    "romance_beats": "Meet, attraction, deepening, midpoint commitment, crisis/break-up, grand gesture, resolution.",
}


def genre_brief(genres: list[str]) -> str:
    lines = []
    for g in genres:
        info = GENRES.get(g.lower())
        if not info:
            lines.append(f"- {g}: blend in this genre's familiar conventions.")
            continue
        lines.append(f"- {info['label']}: " + "; ".join(info["conventions"]))
        if info["pitfalls"]:
            lines.append(f"  Avoid: {'; '.join(info['pitfalls'])}")
    if len(genres) > 1:
        lines.append(
            "- Blend: fuse these genres so each shapes the others (e.g. noir mood inside a sci-fi world), "
            "rather than alternating between them."
        )
    return "\n".join(lines)


def combat_brief(genres: list[str], override: str = "auto") -> str:
    if override and override != "auto":
        return override
    parts = [GENRES[g.lower()]["combat"] for g in genres if g.lower() in GENRES]
    return " ".join(parts) or "Conflict follows the story's established rules; consequences persist."


def list_genres() -> list[dict]:
    return [{"key": k, "label": v["label"]} for k, v in GENRES.items()]
