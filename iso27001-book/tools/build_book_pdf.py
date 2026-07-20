#!/usr/bin/env python3
"""Assemble the Hebrew ISO/IEC 27001 book (iso27001-book/) into one PDF."""
import re
from pathlib import Path

import markdown
from weasyprint import HTML

BOOK_DIR = Path(__file__).resolve().parent.parent
OUT_PDF = BOOK_DIR / "ISO-27001-Summary-Book-HE.pdf"

# (source file relative to BOOK_DIR, anchor slug)
ORDER = [
    ("README.md", "toc"),
    ("01-mavo-umishpachat-tkanim.md", "ch01"),
    ("02-mivne-tekhen-27001.md", "ch02"),
    ("03-nispach-a-bakarot.md", "ch03"),
    ("04-nigzarim-mishpachat-27000.md", "ch04"),
    ("05-tahalich-hasmacha-vebikoret.md", "ch05"),
    ("06-yisum-maasi.md", "ch06"),
    ("07-2013-mul-2022.md", "ch07"),
    ("08-milon-munachim-vecheck-list.md", "ch08"),
    ("09-pentesting-veiso27001.md", "ch09"),
    ("tools/README.md", "appendix-tools"),
]

# Map the exact markdown link targets found in the source files to anchors.
LINK_TARGETS = {
    "01-mavo-umishpachat-tkanim.md": "ch01",
    "02-mivne-tekhen-27001.md": "ch02",
    "03-nispach-a-bakarot.md": "ch03",
    "04-nigzarim-mishpachat-27000.md": "ch04",
    "05-tahalich-hasmacha-vebikoret.md": "ch05",
    "06-yisum-maasi.md": "ch06",
    "07-2013-mul-2022.md": "ch07",
    "08-milon-munachim-vecheck-list.md": "ch08",
    "09-pentesting-veiso27001.md": "ch09",
    "README.md": "toc",
    "tools/README.md": "appendix-tools",
    "../02-mivne-tekhen-27001.md": "ch02",
    "../06-yisum-maasi.md": "ch06",
}


def rewrite_links(text: str) -> str:
    def repl(match):
        target = match.group(1)
        if target in LINK_TARGETS:
            return f"](#{LINK_TARGETS[target]})"
        return match.group(0)

    return re.sub(r"\]\(([^)]*\.md[^)]*)\)", repl, text)


def convert_chapter(rel_path: str, slug: str) -> str:
    path = BOOK_DIR / rel_path
    text = path.read_text(encoding="utf-8")
    text = rewrite_links(text)
    html_body = markdown.markdown(
        text, extensions=["tables", "fenced_code", "sane_lists", "toc"]
    )
    return f'<section class="chapter" id="{slug}">{html_body}</section>'


def build() -> None:
    sections = [convert_chapter(rel, slug) for rel, slug in ORDER]
    body = "\n".join(sections)

    css = """
    @page {
        size: A4;
        margin: 2.2cm 2cm;
        @bottom-center { content: counter(page); font-size: 9pt; color: #555; }
    }
    html { direction: rtl; }
    body {
        direction: rtl;
        font-family: "DejaVu Sans", sans-serif;
        font-size: 11pt;
        line-height: 1.55;
        color: #1a1a1a;
    }
    .chapter { page-break-before: always; }
    .chapter:first-child { page-break-before: avoid; }
    h1 {
        font-size: 21pt;
        border-bottom: 2.5px solid #2b3a55;
        padding-bottom: 8px;
        margin-top: 0;
        color: #1a2540;
    }
    h2 { font-size: 15pt; color: #21315a; margin-top: 26px; border-bottom: 1px solid #ccc; padding-bottom: 3px; }
    h3 { font-size: 12.5pt; color: #2b3a55; margin-top: 18px; }
    p { margin: 8px 0; text-align: justify; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 9.5pt; }
    th, td { border: 1px solid #999; padding: 5px 7px; text-align: right; vertical-align: top; }
    th { background: #e7ebf3; }
    tr:nth-child(even) td { background: #fafafa; }
    pre {
        direction: ltr;
        text-align: left;
        unicode-bidi: embed;
        font-family: "DejaVu Sans Mono", monospace;
        background: #f2f2f2;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 8px 10px;
        font-size: 8.3pt;
        white-space: pre-wrap;
        word-wrap: break-word;
        margin: 10px 0;
    }
    code {
        direction: ltr;
        unicode-bidi: embed;
        font-family: "DejaVu Sans Mono", monospace;
        background: #eee;
        padding: 1px 4px;
        border-radius: 3px;
        font-size: 92%;
    }
    pre code { background: none; padding: 0; }
    blockquote {
        border-right: 4px solid #9aa5c0;
        padding: 4px 12px;
        color: #444;
        margin: 12px 0;
        background: #f7f8fb;
    }
    a { color: #1a4fa0; text-decoration: none; }
    hr { border: none; border-top: 1px solid #ccc; margin: 22px 0; }
    ul, ol { padding-right: 22px; padding-left: 0; margin: 8px 0; }
    li { margin: 3px 0; }
    strong { color: #12203f; }
    """

    html_doc = f"""<!doctype html>
<html lang="he" dir="rtl">
<head><meta charset="utf-8"><title>ISO/IEC 27001 ומשפחת תקני ISO/IEC 27000 — ספר סיכום</title>
<style>{css}</style></head>
<body>{body}</body></html>"""

    tmp_html = BOOK_DIR / "_book_build.html"
    tmp_html.write_text(html_doc, encoding="utf-8")
    HTML(string=html_doc, base_url=str(BOOK_DIR)).write_pdf(str(OUT_PDF))
    tmp_html.unlink()
    print(f"Wrote {OUT_PDF} ({OUT_PDF.stat().st_size} bytes)")


if __name__ == "__main__":
    build()
