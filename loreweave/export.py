"""Manuscript export: Markdown, plain text, standalone HTML and EPUB 3."""

from __future__ import annotations

import html
import io
import uuid
import zipfile

from .models import Project


def _chapters(p: Project):
    return sorted((c for c in p.chapters if c.text), key=lambda c: c.number)


def to_markdown(p: Project) -> str:
    parts = [f"# {p.title}\n"]
    if p.outline.logline:
        parts.append(f"*{p.outline.logline}*\n")
    for c in _chapters(p):
        parts.append(f"\n## Chapter {c.number}: {c.title}\n\n{c.text}\n")
    return "\n".join(parts)


def to_text(p: Project) -> str:
    parts = [p.title.upper(), ""]
    for c in _chapters(p):
        parts += ["", f"CHAPTER {c.number}: {c.title}", "", c.text, ""]
    return "\n".join(parts)


def _paras(text: str) -> str:
    return "\n".join(f"<p>{html.escape(par.strip())}</p>" for par in text.split("\n\n") if par.strip())


def to_html(p: Project) -> str:
    body = "".join(f"<section><h2>Chapter {c.number}: {html.escape(c.title)}</h2>{_paras(c.text)}</section>" for c in _chapters(p))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(p.title)}</title>
<style>body{{max-width:38em;margin:3em auto;font:1.1em/1.6 Georgia,serif;padding:0 1em}}h2{{page-break-before:always;margin-top:3em}}p{{text-indent:1.5em;margin:0}}</style>
</head><body><h1>{html.escape(p.title)}</h1>{body}</body></html>"""


def to_epub(p: Project) -> bytes:
    chapters = _chapters(p)
    book_id = f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, p.id)}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", """<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>""")
        manifest, spine, nav = [], [], []
        for c in chapters:
            fid = f"ch{c.number}"
            title = html.escape(f"Chapter {c.number}: {c.title}")
            z.writestr(f"OEBPS/{fid}.xhtml", f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml"><head><title>{title}</title></head><body><h2>{title}</h2>{_paras(c.text)}</body></html>""")
            manifest.append(f'<item id="{fid}" href="{fid}.xhtml" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="{fid}"/>')
            nav.append(f'<li><a href="{fid}.xhtml">{title}</a></li>')
        z.writestr("OEBPS/nav.xhtml", f"""<?xml version="1.0" encoding="utf-8"?><!DOCTYPE html><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><head><title>Contents</title></head><body><nav epub:type="toc"><ol>{''.join(nav)}</ol></nav></body></html>""")
        z.writestr("OEBPS/content.opf", f"""<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="bid">{book_id}</dc:identifier><dc:title>{html.escape(p.title)}</dc:title><dc:language>en</dc:language><meta property="dcterms:modified">2026-01-01T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>{''.join(manifest)}</manifest><spine>{''.join(spine)}</spine></package>""")
    return buf.getvalue()
