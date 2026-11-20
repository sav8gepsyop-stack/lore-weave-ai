"""Offline backend that produces deterministic, schema-valid output.

Used for tests, UI development and demoing the pipeline without an API key. It reads hints from
GenerationRequest.meta (chapter counts, names) so every pipeline stage receives valid data.
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import AsyncIterator

from .base import Backend, GenerationRequest

NAMES = ["Amara Okafor", "Kenji Arakawa", "Lucía Ferrer", "Dev Malhotra", "Noa Kahale", "Rhys Bellweather"]
ROLES = ["protagonist", "antagonist", "deuteragonist", "supporting", "supporting", "npc"]


class MockBackend(Backend):
    name = "mock"

    def __init__(self, delay: float = 0.0, seed: int = 7):
        self.delay = delay
        self.seed = seed

    async def stream(self, req: GenerationRequest) -> AsyncIterator[str]:
        text = self._render(req)
        step = 60
        for i in range(0, len(text), step):
            if self.delay:
                await asyncio.sleep(self.delay)
            yield text[i : i + step]

    # ------------------------------------------------------------------
    def _render(self, req: GenerationRequest) -> str:
        m = req.meta
        rng = random.Random(f"{self.seed}-{req.task}-{m.get('chapter', 0)}")
        t = req.task
        if t == "characters":
            n = m.get("count", 3)
            out = []
            for i in range(n):
                name = NAMES[i % len(NAMES)]
                out.append(
                    {
                        "name": name,
                        "role": ROLES[i % len(ROLES)],
                        "age": 24 + i * 3,
                        "pronouns": ["she/her", "he/him", "they/them"][i % 3],
                        "archetype": m.get("archetype") or ["reluctant_hero", "fallen_idealist_villain", "tsundere"][i % 3],
                        "appearance": "Distinctive, specific features with one memorable detail.",
                        "cultural_background": "A specific community rendered with care and lived detail.",
                        "backstory": f"{name} grew up between two worlds and lost someone to the city's old war.",
                        "motivation": "Protect the people who still depend on them.",
                        "fear": "Becoming the thing they fight.",
                        "wound": "Abandoned at the moment they most needed help.",
                        "want_vs_need": "Wants control; needs trust.",
                        "psychology": "Hypervigilant, dry humour, secure only with a chosen few.",
                        "voice": "Short sentences, sharp jokes, avoids naming feelings.",
                        "skills": ["improvisation", "reading people"],
                        "flaws": ["pride", "secrecy"],
                        "arc": "From isolation to leadership.",
                        "relationships": [],
                        "milestones": [{"description": "Admits the truth about their past"}],
                        "is_pov": i < 2,
                    }
                )
            return json.dumps({"characters": out})
        if t == "world":
            return json.dumps(
                {
                    "name": "Veyra",
                    "era": "Late industrial age with living magic",
                    "premise": "A river city where contracts with spirits power the grid.",
                    "geography": "A delta city of canals, stilt districts and a drowned old town.",
                    "locations": [
                        {"name": "Lantern Market", "description": "Night market on boats.", "significance": "Neutral ground"},
                        {"name": "The Spire Ward", "description": "Corporate towers.", "significance": "Seat of power"},
                    ],
                    "politics": "A council of guild-corporations rules; districts organise mutual aid.",
                    "factions": [{"name": "Tidewardens", "goals": "Keep the pacts", "methods": "Rituals and audits", "relations": "Uneasy with guilds"}],
                    "economy": "Spirit-contract energy and river trade.",
                    "mythology": "The river was once a goddess who agreed to sleep.",
                    "magic_or_tech": "Pact-craft: every working borrows from a spirit and must be repaid.",
                    "power_rules": ["Every pact must be repaid within a moon", "No pact can raise the dead"],
                    "cultural_norms": "Debts are sacred; names are given twice.",
                    "languages": "Trade creole and old temple tongue.",
                    "history": "The Flood Accord ended a war forty years ago.",
                    "sensory_palette": "Wet stone, lantern oil, brass bells, river mist.",
                }
            )
        if t == "style":
            return json.dumps(
                {
                    "summary": "Lyrical but propulsive; vivid concrete imagery with clipped action beats.",
                    "sentence_structure": "Mix of long cumulative sentences and short fragments at peaks.",
                    "vocabulary": "Concrete nouns, strong verbs, sparse adverbs, occasional archaic word.",
                    "pacing": "Slow-burn description, sudden acceleration in conflict.",
                    "dialogue": "Subtext-heavy; characters rarely say what they mean.",
                    "imagery": "Water and light motifs; sensory specificity.",
                    "narrative_voice": "Close third with wry interiority.",
                    "signature_devices": ["chapter-ending images", "recurring motif"],
                    "avoid": ["purple prose", "info dumps"],
                }
            )
        if t in ("outline", "replan"):
            start = m.get("start", 1)
            n = m.get("chapters", 10)
            povs = m.get("povs") or ["Amara Okafor"]
            chapters = []
            for i in range(start, start + n):
                chapters.append(
                    {
                        "number": i,
                        "title": f"Chapter {i} Title",
                        "pov": povs[(i - 1) % len(povs)],
                        "act": 1 + (i - 1) * 3 // max(1, m.get("total", start + n - 1)),
                        "summary": f"Events of chapter {i} escalate the central conflict.",
                        "beats": ["Opening image", "Complication", "Turn", "Hook"],
                        "subplots": [],
                        "has_action": i % 3 == 0,
                        "milestones": [],
                    }
                )
            if t == "replan":
                return json.dumps({"chapters": chapters})
            return json.dumps(
                {
                    "logline": "A pact-broker must break the oldest contract in the city to save it.",
                    "structure": "three_act",
                    "themes": ["debt and obligation", "chosen family"],
                    "central_question": "What do we owe the people who came before us?",
                    "twists": ["The mentor wrote the pact that is killing the river"],
                    "climax": "A duel of pacts on the flooded steps.",
                    "ending": "Bittersweet renewal.",
                    "subplots": [{"name": "Rivalry to alliance", "description": "Two brokers learn to trust.", "characters": povs[:2], "resolution": "They share the final pact."}],
                    "chapters": chapters,
                    "branch_points": [
                        {
                            "after_chapter": max(1, n // 2),
                            "question": "Does the protagonist expose the mentor publicly?",
                            "options": [
                                {"label": "Expose", "consequence": "The city turns on the guild; chaos rises."},
                                {"label": "Bargain", "consequence": "A secret alliance with a hidden price."},
                            ],
                        }
                    ],
                }
            )
        if t == "macro_outline":
            return json.dumps(
                {
                    "logline": "An ultra-length saga of pact-breakers.",
                    "structure": "five_act",
                    "themes": ["debt", "legacy"],
                    "central_question": "Can a city survive its own bargains?",
                    "twists": ["The river goddess is awake"],
                    "climax": "The Accord is renegotiated in blood and ink.",
                    "ending": "Renewal at a cost.",
                    "subplots": [
                        {"name": "Rival brokers", "description": "Enemies to allies.", "characters": [], "resolution": "Alliance"},
                        {"name": "Sibling secret", "description": "A hidden heir.", "characters": [], "resolution": "Revealed"},
                    ],
                    "acts": [{"act": a, "summary": f"Act {a} movement", "chapters": m.get("per_act", 5)} for a in range(1, m.get("acts", 3) + 1)],
                }
            )
        if t == "extract":
            ch = m.get("chapter", 1)
            pov = m.get("pov") or "Amara Okafor"
            return json.dumps(
                {
                    "summary": f"In chapter {ch}, {pov} pushes the conflict forward and uncovers a new clue.",
                    "new_facts": [f"Fact established in chapter {ch}"],
                    "character_states": [{"name": pov, "status": "alive", "location": "Lantern Market", "condition": "tired but resolved", "knows": [f"clue {ch}"], "possessions": [], "relationship_shifts": []}],
                    "threads_opened": [f"Thread from chapter {ch}"] if ch % 2 else [],
                    "threads_resolved": [f"Thread from chapter {ch - 1}"] if ch % 2 == 0 and ch > 1 else [],
                    "milestones_hit": [],
                }
            )
        if t == "continuity":
            return json.dumps({"issues": []})
        if t == "compress":
            return "Story so far: the conflict has escalated across several chapters; alliances are shifting."
        if t == "repair_json":
            return "{}"
        # Prose tasks: chapter, revise, preview
        words = m.get("target_words", 400)
        pov = m.get("pov") or "Amara"
        sentences = [
            f"{pov} watched the lanterns drift along the canal, counting debts the way other people counted stars.",
            "The air smelled of wet stone and brass, and somewhere a bell rang twice for a name given twice.",
            '"You came back," said a voice from the dark, and it was not a question.',
            "There was a cost to every working, and tonight the river meant to collect.",
            "Steel met spirit-light in a shower of sparks; she gave ground, read the rhythm, and answered.",
            "Afterward, in the quiet, the fear came for her the way it always did: late, and thorough.",
        ]
        out, count = [], 0
        while count < words:
            s = rng.choice(sentences)
            out.append(s)
            count += len(s.split())
            if rng.random() < 0.25:
                out.append("\n\n")
        return " ".join(out).replace(" \n\n ", "\n\n").strip()
