"""Content settings -> plain-language writing instructions, plus the hard guard on minors.

These are passed to the model as honest descriptions of what the author wants. They are not
designed to disguise requests or get around any model provider's safety systems; if a backend
declines something, the engine surfaces that to the user instead of rephrasing to evade it.
"""

from __future__ import annotations

from .models import ContentSettings, Project, RomanceLevel, ViolenceLevel


class ContentPolicyError(ValueError):
    pass


ROMANCE_TEXT = {
    RomanceLevel.NONE: "No romantic or sexual content.",
    RomanceLevel.ROMANTIC: (
        "Romance is welcome: attraction, longing, banter, kisses and emotional intimacy. "
        "Any sex happens off the page (cut away or fade to black)."
    ),
    RomanceLevel.SENSUAL: (
        "Sensual content: intimate scenes between consenting adults may appear on the page, conveyed "
        "through emotion, sensation and atmosphere rather than anatomical detail. Keep the scene doing "
        "story work (revealing character, shifting the relationship)."
    ),
    RomanceLevel.EXPLICIT: (
        "Adult content: the author has opted into explicit sex scenes between consenting adults. Write them "
        "with literary craft, keep them in service of character and story, and keep the prose's voice consistent."
    ),
}

VIOLENCE_TEXT = {
    ViolenceLevel.MILD: "Action stays clean: fights and danger without lingering injury detail.",
    ViolenceLevel.MODERATE: "Violence has real wounds and consequences, depicted honestly but not dwelt upon.",
    ViolenceLevel.GRAPHIC: (
        "Graphic violence is permitted where the story calls for it: unflinching, visceral and with weight. "
        "Never gratuitous; every injury has consequences that persist in later chapters."
    ),
}

PROFANITY_TEXT = {
    "none": "No profanity.",
    "light": "Occasional mild profanity where it fits a character's voice.",
    "heavy": "Profanity is fine wherever it fits a character's natural voice.",
}

ALWAYS = (
    "Hard rules regardless of settings: no sexual or sexualised content involving anyone under 18, "
    "including descriptions of minors' bodies in a romantic or sexual light; all intimate content involves "
    "consenting adults. Portray characters of every background as full people, avoiding stereotypes."
)


def content_instructions(c: ContentSettings) -> str:
    parts = [
        "CONTENT SETTINGS (chosen by the author):",
        f"- Romance: {ROMANCE_TEXT[c.romance]}",
        f"- Violence: {VIOLENCE_TEXT[c.violence]}",
        f"- Language: {PROFANITY_TEXT[c.profanity]}",
    ]
    if c.dark_themes:
        parts.append(
            "- Heavier themes the author wants explored with care and emotional truth: " + ", ".join(c.dark_themes)
        )
    if c.content_notes:
        parts.append(f"- Author notes: {c.content_notes}")
    parts.append(f"- {ALWAYS}")
    return "\n".join(parts)


def validate_project_content(p: Project) -> list[str]:
    """Return warnings, raise on hard violations.

    Hard violation: romance above NONE with a minor flagged as a love interest / romantic relationship.
    """
    warnings: list[str] = []
    minors = {c.name for c in p.characters if c.is_minor}
    romantic_words = ("love", "romance", "romantic", "lover", "crush", "partner", "spouse", "girlfriend", "boyfriend")
    for c in p.characters:
        for r in c.relationships:
            kind = (r.kind + " " + r.dynamic).lower()
            if any(w in kind for w in romantic_words) and (c.name in minors or r.target in minors):
                if p.content.romance in (RomanceLevel.SENSUAL, RomanceLevel.EXPLICIT):
                    raise ContentPolicyError(
                        f"'{c.name}' and '{r.target}' have a romantic relationship but one is under 18. "
                        "Sensual/explicit settings require all romantically involved characters to be adults. "
                        "Raise their ages or lower the romance level."
                    )
                warnings.append(
                    f"Romance between '{c.name}' and '{r.target}' involves a minor; it will be kept to "
                    "age-appropriate, non-physical feelings."
                )
    unaged = [c.name for c in p.characters if c.age is None]
    if unaged and p.content.romance in (RomanceLevel.SENSUAL, RomanceLevel.EXPLICIT):
        warnings.append(
            "These characters have no age set and will be treated as adults: " + ", ".join(unaged)
        )
    return warnings


def minor_guard_text(p: Project) -> str:
    minors = [f"{c.name} ({c.age})" for c in p.characters if c.is_minor]
    if not minors:
        return ""
    return (
        "Characters under 18: " + ", ".join(minors) + ". They are never part of any romantic-physical or sexual "
        "content and are never described in a sexualised way."
    )
