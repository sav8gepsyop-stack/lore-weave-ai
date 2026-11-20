"""Core data models: the project spec the user edits and the story bible the engine maintains."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


class LengthMode(str, Enum):
    STANDARD = "standard"  # 50-100 pages
    ULTRA = "ultra"  # 200+ pages


class RomanceLevel(str, Enum):
    NONE = "none"
    ROMANTIC = "romantic"  # longing, tension, kisses; intimacy happens off-page
    SENSUAL = "sensual"  # on-page intimacy rendered through emotion and sensation, not anatomy
    EXPLICIT = "explicit"  # frank adult intimacy, written with literary craft


class ViolenceLevel(str, Enum):
    MILD = "mild"  # action without lingering injury detail
    MODERATE = "moderate"  # wounds and consequences are real but not dwelt upon
    GRAPHIC = "graphic"  # visceral, unflinching depiction where the story calls for it


class ContentSettings(BaseModel):
    romance: RomanceLevel = RomanceLevel.ROMANTIC
    violence: ViolenceLevel = ViolenceLevel.MODERATE
    profanity: Literal["none", "light", "heavy"] = "light"
    dark_themes: list[str] = Field(
        default_factory=list,
        description="Opt-in heavier themes, e.g. grief, addiction, war trauma, abuse aftermath.",
    )
    content_notes: str = ""


class ConflictSettings(BaseModel):
    combat_system: str = "auto"  # auto = derived from genre
    action_ratio: float = Field(0.3, ge=0.0, le=1.0, description="Rough share of page time spent on action.")
    stakes_escalation: Literal["slow_burn", "steady", "relentless"] = "steady"
    emphasize_consequences: bool = True


class StyleProfile(BaseModel):
    """Describes HOW the prose should read. Built from influences as trait descriptors, never quotations."""

    influences: list[str] = Field(default_factory=list)
    summary: str = ""
    sentence_structure: str = ""
    vocabulary: str = ""
    pacing: str = ""
    dialogue: str = ""
    imagery: str = ""
    narrative_voice: str = ""
    signature_devices: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    pov: Literal["first", "third_limited", "third_omniscient", "second"] = "third_limited"
    tense: Literal["past", "present"] = "past"


# ---------------------------------------------------------------------------
# Characters, world, plot
# ---------------------------------------------------------------------------


class Relationship(BaseModel):
    target: str  # character name
    kind: str  # rival, sibling, mentor, love interest...
    dynamic: str = ""


class Milestone(BaseModel):
    chapter: int | None = None
    description: str


class Character(BaseModel):
    id: str = Field(default_factory=lambda: new_id("ch_"))
    name: str
    role: Literal["protagonist", "deuteragonist", "antagonist", "supporting", "npc"] = "supporting"
    age: int | None = None
    pronouns: str = ""
    archetype: str = ""
    appearance: str = ""
    cultural_background: str = ""
    backstory: str = ""
    motivation: str = ""
    fear: str = ""
    wound: str = ""  # formative hurt that drives behaviour
    want_vs_need: str = ""
    psychology: str = ""  # temperament, attachment style, coping mechanisms
    voice: str = ""  # speech patterns
    skills: list[str] = Field(default_factory=list)
    flaws: list[str] = Field(default_factory=list)
    arc: str = ""
    relationships: list[Relationship] = Field(default_factory=list)
    milestones: list[Milestone] = Field(default_factory=list)
    is_pov: bool = False

    @field_validator("age")
    @classmethod
    def _age_ok(cls, v):
        if v is not None and (v < 0 or v > 100000):
            raise ValueError("age out of range")
        return v

    @property
    def is_minor(self) -> bool:
        return self.age is not None and self.age < 18


class Location(BaseModel):
    name: str
    description: str = ""
    significance: str = ""


class Faction(BaseModel):
    name: str
    goals: str = ""
    methods: str = ""
    relations: str = ""


class World(BaseModel):
    name: str = ""
    era: str = ""
    genre_blend: list[str] = Field(default_factory=list)
    premise: str = ""
    geography: str = ""
    locations: list[Location] = Field(default_factory=list)
    politics: str = ""
    factions: list[Faction] = Field(default_factory=list)
    economy: str = ""
    mythology: str = ""
    magic_or_tech: str = ""  # power system, technology level, rules and costs
    power_rules: list[str] = Field(default_factory=list)  # hard rules the engine must not break
    cultural_norms: str = ""
    languages: str = ""
    history: str = ""
    sensory_palette: str = ""  # sights, sounds, smells that recur


class ChapterPlan(BaseModel):
    number: int
    title: str = ""
    pov: str = ""
    act: int = 1
    summary: str = ""
    beats: list[str] = Field(default_factory=list)
    subplots: list[str] = Field(default_factory=list)  # subplot ids advanced here
    has_action: bool = False
    milestones: list[str] = Field(default_factory=list)
    target_words: int = 2500


class Subplot(BaseModel):
    id: str = Field(default_factory=lambda: new_id("sp_"))
    name: str
    description: str = ""
    characters: list[str] = Field(default_factory=list)
    resolution: str = ""


class BranchOption(BaseModel):
    label: str
    consequence: str


class BranchPoint(BaseModel):
    after_chapter: int
    question: str
    options: list[BranchOption]
    chosen: int | None = None


class PlotOutline(BaseModel):
    logline: str = ""
    structure: str = ""  # e.g. three-act, kishotenketsu, hero's journey
    themes: list[str] = Field(default_factory=list)
    central_question: str = ""
    twists: list[str] = Field(default_factory=list)
    climax: str = ""
    ending: str = ""
    subplots: list[Subplot] = Field(default_factory=list)
    chapters: list[ChapterPlan] = Field(default_factory=list)
    branch_points: list[BranchPoint] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Continuity state produced while writing
# ---------------------------------------------------------------------------


class CharacterState(BaseModel):
    name: str
    status: str = "alive"  # alive, dead, missing, captured...
    location: str = ""
    condition: str = ""  # injuries, emotional state
    knows: list[str] = Field(default_factory=list)  # secrets/info this character has learned
    possessions: list[str] = Field(default_factory=list)
    relationship_shifts: list[str] = Field(default_factory=list)


class ContinuityIssue(BaseModel):
    chapter: int
    severity: Literal["low", "medium", "high"] = "low"
    description: str
    suggestion: str = ""


class ChapterRecord(BaseModel):
    number: int
    title: str = ""
    pov: str = ""
    text: str = ""
    summary: str = ""
    word_count: int = 0
    new_facts: list[str] = Field(default_factory=list)
    open_threads: list[str] = Field(default_factory=list)
    issues: list[ContinuityIssue] = Field(default_factory=list)
    character_states: list[CharacterState] = Field(default_factory=list)
    threads_resolved: list[str] = Field(default_factory=list)
    milestones_hit: list[str] = Field(default_factory=list)
    revised: bool = False
    created_at: float = Field(default_factory=time.time)


class Ledger(BaseModel):
    """The engine's memory of what has happened: canon facts, per-character state, open threads."""

    facts: list[str] = Field(default_factory=list)
    characters: dict[str, CharacterState] = Field(default_factory=dict)
    open_threads: list[str] = Field(default_factory=list)
    resolved_threads: list[str] = Field(default_factory=list)
    story_so_far: str = ""  # compressed summary of everything older than the recent window
    compressed_through: int = 0  # last chapter folded into story_so_far
    milestones_hit: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


class Project(BaseModel):
    id: str = Field(default_factory=lambda: new_id("prj_"))
    title: str = "Untitled"
    genres: list[str] = Field(default_factory=lambda: ["fantasy"])
    premise: str = ""
    audience_notes: str = ""
    length_mode: LengthMode = LengthMode.STANDARD
    target_pages: int = 75
    words_per_page: int = 275
    content: ContentSettings = Field(default_factory=ContentSettings)
    conflict: ConflictSettings = Field(default_factory=ConflictSettings)
    style: StyleProfile = Field(default_factory=StyleProfile)
    characters: list[Character] = Field(default_factory=list)
    world: World = Field(default_factory=World)
    outline: PlotOutline = Field(default_factory=PlotOutline)
    chapters: list[ChapterRecord] = Field(default_factory=list)
    ledger: Ledger = Field(default_factory=Ledger)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    @property
    def target_words(self) -> int:
        return self.target_pages * self.words_per_page

    @property
    def word_count(self) -> int:
        return sum(c.word_count for c in self.chapters)

    def character(self, name: str) -> Character | None:
        low = name.strip().lower()
        for c in self.characters:
            if c.name.lower() == low:
                return c
        return None
