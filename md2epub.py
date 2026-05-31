#!/usr/bin/env python3
"""
Standalone Markdown to EPUB converter.
Edit the configuration variables below, then run: python md2epub.py

Dependencies: markdown, ebooklib (already in requirements.txt)
"""

import os
from markdown import markdown
from ebooklib import epub

# ── CONFIGURATION ──────────────────────────────────────────────────
INPUT_MD = "phase0-8.md"        # Path to the source Markdown file
OUTPUT_EPUB = "phase0-8.epub"  # Path for the generated EPUB file
BOOK_TITLE = "Unknown"       # EPUB title metadata
BOOK_AUTHOR = "Unknown"      # EPUB author metadata
LANGUAGE = "en"              # Language code (e.g., "en", "de", "fr")
# ────────────────────────────────────────────────────────────────────

EPUB_CSS = """
body {
    font-family: Georgia, serif;
    line-height: 1.6;
    margin: 0;
    padding: 0 0.5em;
}
h1, h2, h3, h4, h5, h6 {
    margin-top: 1.2em;
    margin-bottom: 0.4em;
}
p {
    margin-top: 0.5em;
    margin-bottom: 0.5em;
}
pre, code {
    font-family: "Courier New", monospace;
    background-color: #f4f4f4;
    padding: 0.2em 0.4em;
    border-radius: 3px;
}
pre {
    padding: 0.8em;
    overflow-x: auto;
}
pre code {
    background: none;
    padding: 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}
th, td {
    border: 1px solid #ccc;
    padding: 0.4em 0.6em;
    text-align: left;
}
img {
    max-width: 100%;
    height: auto;
}
blockquote {
    border-left: 3px solid #ccc;
    margin: 1em 0;
    padding: 0.2em 1em;
    color: #555;
}
"""  # noqa: W293


def md2epub(
    input_path: str = INPUT_MD,
    output_path: str = OUTPUT_EPUB,
    title: str = BOOK_TITLE,
    author: str = BOOK_AUTHOR,
    language: str = LANGUAGE,
) -> None:
    """
    Convert a Markdown file to an EPUB book.

    Args:
        input_path:  Path to the source .md file.
        output_path: Path for the generated .epub file.
        title:       Book title (metadata).
        author:      Book author (metadata).
        language:    Language code.
    """
    # ── 1. Validate input file ────────────────────────────────────
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f"Markdown file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    if not md_text.strip():
        raise ValueError("Input Markdown file is empty.")

    # ── 2. Convert Markdown → HTML ────────────────────────────────
    html_body = markdown(
        md_text,
        extensions=[
            "fenced_code",
            "tables",
            "codehilite",
            "toc",
            "nl2br",
            "sane_lists",
        ],
    )

    # Wrap body content in a minimal HTML page (EbookLib auto-wraps
    # epub.EpubHtml items, but providing a clean <html><body>…</body></html>
    # is well-supported across readers).
    full_html = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="utf-8"/>
    <title>{title}</title>
</head>
<body>
{html_body}
</body>
</html>"""

    # ── 3. Build EPUB ─────────────────────────────────────────────
    book = epub.EpubBook()
    book.set_identifier(f"md2epub-{os.path.basename(input_path)}")
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    # Default CSS
    css_item = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=EPUB_CSS.encode("utf-8"),
    )
    book.add_item(css_item)

    # Main chapter
    chapter = epub.EpubHtml(
        title=title,
        file_name="content.xhtml",
        lang=language,
    )
    chapter.content = full_html.encode("utf-8")
    chapter.add_item(css_item)
    book.add_item(chapter)

    # Spine
    book.spine = ["nav", chapter]

    # Table of Contents
    book.toc = [epub.Link("content.xhtml", title, "main")]

    # Required navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # ── 4. Write EPUB ─────────────────────────────────────────────
    epub.write_epub(output_path, book)
    print(f"EPUB written to: {output_path}")


if __name__ == "__main__":
    md2epub()