"""Character archetype library.

Each archetype carries a surface pattern plus the psychology underneath it, so the engine writes
people rather than tropes. "Subversions" give the writer ways to keep a familiar type fresh.
"""

from __future__ import annotations

ARCHETYPES: dict[str, dict] = {
    # --- Manga / anime-rooted personality types ---------------------------------
    "tsundere": {
        "family": "manga",
        "surface": "Prickly, dismissive, quick to deny affection; flustered when caught caring.",
        "core": "Vulnerability is experienced as danger. Harshness is armour built after care was once mocked or withheld.",
        "arc": "From defensive denial to letting care be seen without the armour; the payoff is a moment of plain, unguarded honesty.",
        "pitfalls": "Avoid making cruelty cute or using hitting as comedy; the harshness should cost them something.",
        "subversions": ["The armour is about competence, not romance", "They drop the act early and must learn to keep boundaries anyway"],
    },
    "yandere": {
        "family": "manga",
        "surface": "Devoted and sweet on the outside; possessive to the point of danger.",
        "core": "Identity fused to one attachment; abandonment terror reframed as love. Often a horror or tragedy engine.",
        "arc": "Either a tragic descent the story treats seriously, or a reckoning where they confront the fear behind the fixation.",
        "pitfalls": "Never frame controlling or violent behaviour as romantic goals; show its harm on others.",
        "subversions": ["Their obsession is with an ideal or cause, not a person", "The narrative is from the target's increasingly lucid POV"],
    },
    "kuudere": {
        "family": "manga",
        "surface": "Calm, flat affect, economical speech.",
        "core": "Emotion is felt fully but processed privately; often hyper-observant.",
        "arc": "Learns that expressing feeling is a gift to others, not a loss of control.",
        "pitfalls": "Flat is not empty; give them a rich interior life on the page.",
        "subversions": ["Their calm is a trained professional discipline", "Their composure breaks at an unexpected trigger"],
    },
    "dandere": {
        "family": "manga",
        "surface": "Shy and quiet until trust is earned, then warm and talkative.",
        "core": "Social anxiety or past humiliation; deep loyalty once safe.",
        "arc": "Finds their voice in a moment that matters, at real social cost.",
        "pitfalls": "Shyness is not a puzzle for another character to solve.",
        "subversions": ["Quiet because they are always calculating", "Outspoken online or in a second persona"],
    },
    "deredere": {
        "family": "manga",
        "surface": "Openly cheerful, affectionate and energetic.",
        "core": "Sunshine as a choice; often hides grief or carries others' moods.",
        "arc": "Allowed to be sad; learns joy that ignores pain is brittle.",
        "pitfalls": "Give them opinions and wants, not just pep.",
        "subversions": ["Relentless optimism is a survival strategy from hard circumstances"],
    },
    "shonen_hero": {
        "family": "manga",
        "surface": "Determined, loud, never gives up; grows through training and rivalry.",
        "core": "Seeks recognition or to protect a found family; defined by a promise.",
        "arc": "Power grows, but the real arc is understanding what strength is for.",
        "pitfalls": "Victories must be earned; losses should leave marks.",
        "subversions": ["Their dream is revealed to be someone else's", "They must choose to stop fighting"],
    },
    "stoic_rival": {
        "family": "manga",
        "surface": "Cool, superior, the measuring stick for the hero.",
        "core": "Carries a family burden or vow; respect is their love language.",
        "arc": "Rival to ally, or a rival whose path diverges tragically.",
        "pitfalls": "Give the rival their own goals beyond the hero.",
        "subversions": ["The rival is right and the hero is wrong"],
    },
    "trickster_mentor": {
        "family": "universal",
        "surface": "Lazy or eccentric front hiding immense skill.",
        "core": "Guilt over a past failure; teaches to prevent its repeat.",
        "arc": "Their past catches up; the student may have to save them.",
        "pitfalls": "Avoid wise-elder-of-colour tokenism; give them a full life.",
        "subversions": ["The mentor is younger than the student"],
    },
    # --- Western / literary archetypes ------------------------------------------
    "reluctant_hero": {
        "family": "universal",
        "surface": "Ordinary person pulled into extraordinary stakes.",
        "core": "Wants safety or normalcy; carries a quiet competence they underestimate.",
        "arc": "Chooses the call rather than being dragged by it.",
        "pitfalls": "Reluctance must have a reason that matters.",
        "subversions": ["They refuse the call and someone else answers it"],
    },
    "antihero": {
        "family": "universal",
        "surface": "Morally grey, effective, self-interested.",
        "core": "A code of their own; past betrayal shaped distrust of institutions.",
        "arc": "Either finds something worth more than self, or confirms the cost of never doing so.",
        "pitfalls": "Cool is not the same as compelling; show the cost.",
        "subversions": ["Their code is stricter than the heroes'"],
    },
    "fallen_idealist_villain": {
        "family": "universal",
        "surface": "Charismatic antagonist with a cause.",
        "core": "Saw a real injustice; concluded that any means are justified.",
        "arc": "Mirrors the hero; their defeat should feel like a warning, not a relief.",
        "pitfalls": "Their argument must be strong enough that readers feel its pull.",
        "subversions": ["They win a partial victory that changes the world"],
    },
    "chosen_one": {
        "family": "fantasy",
        "surface": "Destined for greatness by prophecy or bloodline.",
        "core": "Struggle between destiny and self-authored identity.",
        "arc": "Redefines or rejects the destiny.",
        "pitfalls": "Avoid passive protagonists carried by fate.",
        "subversions": ["The prophecy was propaganda", "They are the second choice"],
    },
    "street_strategist": {
        "family": "urban",
        "surface": "Reads people and blocks like a chessboard; loyal to their crew.",
        "core": "Responsibility came early; trust is currency.",
        "arc": "Chooses between the game and a life beyond it, or reshapes the game.",
        "pitfalls": "Give them a full interior life, ambitions and humour; avoid crime-as-identity shortcuts.",
        "subversions": ["Their talent is used to build something legitimate and the old world resists"],
    },
    "hustler_dreamer": {
        "family": "urban",
        "surface": "Ambitious, charming, always working an angle toward a bigger life.",
        "core": "Wants security for people they love; fear of ending up where they started.",
        "arc": "Learns what they are willing to trade, and what they are not.",
        "pitfalls": "Avoid poverty-as-aesthetic; ground hardship in specific detail.",
        "subversions": ["The dream succeeds and the cost is the story"],
    },
    "noir_detective": {
        "family": "noir",
        "surface": "Cynical investigator in a corrupt city.",
        "core": "A bruised moralist who still believes truth matters.",
        "arc": "Uncovers a truth that costs them something they cannot get back.",
        "pitfalls": "Avoid femme-fatale cliches; give every character an agenda.",
        "subversions": ["The detective is the cause of the crime they investigate"],
    },
    "found_family_anchor": {
        "family": "universal",
        "surface": "The one who keeps the group together.",
        "core": "Fear of abandonment turned into caretaking.",
        "arc": "Learns to let others care for them.",
        "pitfalls": "Don't sacrifice them just for pathos.",
        "subversions": ["They are secretly the one holding the group back"],
    },
}


def archetype_brief(key: str) -> str:
    a = ARCHETYPES.get(key)
    if not a:
        return key
    return (
        f"{key.replace('_', ' ')}: surface - {a['surface']} Underneath - {a['core']} "
        f"Arc shape - {a['arc']} Watch for - {a['pitfalls']}"
    )


def list_archetypes() -> list[dict]:
    return [{"key": k, **v} for k, v in ARCHETYPES.items()]
