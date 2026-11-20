"""Command line: `loreweave serve` for the dashboard, `loreweave write spec.json` for headless runs."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from .backends import make_backend
from .engine.core import LoreWeaveEngine
from .export import to_markdown
from .models import Project
from .storage import Store


def main(argv=None):
    ap = argparse.ArgumentParser(prog="loreweave")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the web dashboard")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.add_argument("--backend", choices=["claude", "hf", "mock"])
    w = sub.add_parser("write", help="build and write a whole manuscript from a project JSON file")
    w.add_argument("spec")
    w.add_argument("--backend", choices=["claude", "hf", "mock"])
    w.add_argument("--out", default="manuscript.md")
    w.add_argument("--chapters", type=int, help="only write the first N chapters")
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        import uvicorn

        from .server import create_app

        uvicorn.run(create_app(backend=args.backend), host=args.host, port=args.port)
        return

    p = Project.model_validate_json(open(args.spec, encoding="utf-8").read())
    engine = LoreWeaveEngine(make_backend(args.backend))
    store = Store()

    async def run():
        if not p.characters:
            print("Generating cast...", file=sys.stderr)
            p.characters = await engine.generate_characters(p, 4)
        if not p.world.name:
            print("Building world...", file=sys.stderr)
            p.world = await engine.generate_world(p)
        if p.style.influences and not p.style.summary:
            p.style = await engine.analyze_style(p, p.style.influences)
        if not p.outline.chapters:
            print("Architecting plot...", file=sys.stderr)
            p.outline = await engine.generate_outline(p)
        async for ev in engine.write(p, 1, args.chapters, on_save=store.save):
            if ev["type"] == "delta":
                sys.stdout.write(ev["text"])
                sys.stdout.flush()
            elif ev["type"] != "delta":
                print(f"\n[{ev['type']}] " + json.dumps({k: v for k, v in ev.items() if k not in ('type', 'text')})[:300], file=sys.stderr)

    asyncio.run(run())
    store.save(p)
    open(args.out, "w", encoding="utf-8").write(to_markdown(p))
    print(f"\nWrote {p.word_count:,} words to {args.out} (project {p.id})", file=sys.stderr)


if __name__ == "__main__":
    main()
