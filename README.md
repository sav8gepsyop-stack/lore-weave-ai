# Lore Weave AI

A long-form fiction studio that builds a story bible with you, then writes a manuscript that holds together from start to finish: **50-100 pages in Standard mode, 200+ pages in Ultra mode**. It is tuned for manga-style stories, urban fiction and fantasy, and you can blend any genres you like (sci-fi noir, urban fantasy, cyberpunk romance and so on).

By default it writes with the Claude API (`claude-opus-5-5`). You can plug in a local Hugging Face Transformers model instead, or use an offline demo engine to try the whole pipeline with no API key.

## Features

| Module | What it does |
|---|---|
| **Character Builder** | Layered characters: wound, want vs need, fear, psychology, voice, cultural background, relationships and arc milestones. Includes an archetype library (tsundere, yandere, kuudere, dandere, shonen hero, stoic rival, noir detective, street strategist and more). Each archetype comes with the psychology underneath it, ways to subvert it, and stereotypes to avoid. |
| **Worldcrafting** | Geography, politics, factions, economy, mythology, magic/tech systems with costs, cultural norms, history and a sensory palette. **Hard rules** you set are enforced by the continuity checker. |
| **Plot Architect** | Picks a structure (three-act, kishotenketsu, hero's journey, five-act, romance beats) and plans every chapter with POV, beats, subplots and milestones. **Branch points** let you choose a fork, and the chapters after it are re-planned. |
| **Style Infusion ("Copy Author")** | Name your influences and the engine builds a style profile of their techniques (syntax, vocabulary, pacing, dialogue, imagery, devices). You can also start from presets such as mythic epic, light novel, street-lit voice, hardboiled noir, minimalist or lush romantic, or calibrate against a sample of your own writing. It describes technique only and never reproduces anyone's text. |
| **Content settings** | Separate controls for romance (none, romantic, sensual, explicit), violence (mild, moderate, graphic), language, and opt-in heavier themes. |
| **Violence & Conflict** | Combat conventions for each genre: magical duels with costs and counters in fantasy, named techniques in manga, grounded fights with real fallout in urban fiction, tech tactics in sci-fi. You can also set the action ratio, how fast stakes escalate, and whether injuries carry over between chapters. |
| **Ultra Mode** | Plans in two levels (acts first, then the chapters inside each act), rotates multiple POVs, braids at least three subplots, and places character milestones across the whole book. |
| **Live preview** | Chapters stream into the dashboard as they are written. "Preview scene" lets you test voice and settings before you write the full book. |
| **Export** | Markdown, plain text, print-ready HTML (use your browser's print dialog to save a PDF), and EPUB 3. |

## How it keeps long manuscripts coherent

1. **Story bible as the cached system prompt.** Characters, world, style, content settings and the outline go into every call. Because they don't change during a writing run, prompt caching makes later chapters cheaper.
2. **Writing chapter by chapter.** Each chapter is written from its plan, the continuity ledger, and the last ~2,500 characters of the previous chapter, so scenes pick up where the last one stopped. If a chapter comes out short, the engine extends it automatically.
3. **Continuity ledger.** After each chapter, an extraction pass records a summary, canon facts, each character's state (alive or dead, location, injuries, what they know, what they carry), open and resolved threads, and milestones reached.
4. **Consistency checks.** Fast rule-based checks catch things like name drift, a dead character speaking, a missing POV character, or a chapter that is too short. A model-based continuity editor then compares the chapter with the bible and the ledger. Problems rated high severity trigger an automatic revision.
5. **Rolling summaries.** The three most recent chapter summaries are kept word for word. Older ones are compressed into a "story so far" recap, so the context stays a manageable size even at 200+ pages.
6. **Rewrites rebuild the ledger.** If you rewrite from chapter *k*, the ledger is rebuilt from chapters before *k*, so facts from discarded chapters don't carry over.

## Quick start

```bash
git clone https://github.com/sav8gepsyop-stack/lore-weave-ai && cd lore-weave-ai
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export ANTHROPIC_API_KEY=sk-ant-...      # for the default Claude engine
loreweave serve                           # open http://127.0.0.1:8000
```

No API key? Run `loreweave serve --backend mock` to try every screen with the offline demo engine. Its prose is placeholder text.

**Suggested workflow:** Story setup → Character Builder → Worldcrafting → Style Infusion → Content & Conflict (preview a scene) → Plot Architect (choose branches) → Write → Export.

### Headless runs

```bash
cat > spec.json <<'EOF'
{"title": "Ashes of the Lantern City", "genres": ["fantasy", "noir"], "length_mode": "standard",
 "target_pages": 80, "premise": "A disgraced pact-broker must solve the murder of the river goddess's last priest.",
 "style": {"influences": ["Raymond Chandler", "N. K. Jemisin"]}}
EOF
loreweave write spec.json --out ashes.md            # builds the cast, world, style and plot, then writes the book
loreweave write spec.json --chapters 2 --backend mock
```

### Local models (Hugging Face Transformers)

```bash
pip install -e ".[local]"
LOREWEAVE_BACKEND=hf LOREWEAVE_HF_MODEL=Qwen/Qwen2.5-7B-Instruct loreweave serve
```

Any chat or instruct causal LM works. Smaller models keep less of a long book straight, so the ledger and the consistency checks matter even more with them.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `LOREWEAVE_BACKEND` | `claude` | `claude`, `hf` or `mock` (you can also switch in the dashboard header) |
| `LOREWEAVE_CLAUDE_MODEL` | `claude-opus-5-5` | Claude model ID |
| `LOREWEAVE_EFFORT` | per task | Sets one effort level for every call. Without it, prose and planning use `high` and bookkeeping uses `low`. |
| `LOREWEAVE_FALLBACKS` | `1` | Server-side refusal fallbacks (`0` to disable) |
| `LOREWEAVE_HF_MODEL` | `Qwen/Qwen2.5-7B-Instruct` | Local model ID |
| `LOREWEAVE_HF_CONTEXT` | `32768` | Context budget for local models |
| `LOREWEAVE_DATA` | `./data` | Where project JSON files are stored |

## Cost and time (Claude, rough estimates)

A 75-page Standard book is about 8 chapters. Each chapter takes about 4 calls (write, extract, check, and sometimes revise), and the cached bible keeps the input cost down. Expect roughly 5-15 minutes and a few dollars at Opus 5.5 rates. A 220-page Ultra book is about 3x that. These are estimates, not measured numbers [confidence: med].

## Content policy

The content settings are sent to the model as plain, honest descriptions of what the author wants. Nothing tries to disguise a request or get around a model provider's safety systems. If a model declines something, the dashboard tells you instead of quietly rephrasing it. Hard rules apply at every setting: no sexual or sexualised content involving anyone under 18. A project that pairs a minor with sensual or explicit romance is blocked before writing starts. Prompts throughout ask for diverse, non-stereotyped casts.

## Architecture

```
loreweave/
  models.py         Project, Character, World, PlotOutline, StyleProfile, Ledger (pydantic)
  archetypes.py     archetype library with psychology, arcs and subversions
  genres.py         genre conventions, combat systems, structures, blending
  style.py          style presets and style instructions
  content.py        content-level instructions and the minor-protection guard
  backends/         claude.py (default), hf.py (Transformers), mock.py (offline)
  engine/core.py    builders, outline (standard and two-level ultra), branch re-planning, writing loop
  engine/prompts.py story bible and per-task prompts
  engine/continuity.py  ledger merge and rebuild, rule-based checks
  server.py         FastAPI REST + Server-Sent Events for live writing
  web/              dashboard (vanilla JS, no build step)
  export.py         md / txt / html / epub
```

## Open-source lineage

Lore Weave AI is written from scratch. AI Dungeon's engine is not open source, so none of its code is used here. The ideas behind the coherence system (a persistent memory or "lorebook", running summaries, injecting world info at generation time) are common practice across open-source interactive-fiction tools. If you want to add code from community projects, check that their licenses are compatible with MIT first.

## Development

```bash
pip install -e ".[dev]"
pytest                    # engine, content guard, Ultra outline, branching, server + SSE flow (mock backend)
```

## License

MIT
