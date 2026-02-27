#!/usr/bin/env python3
"""
Convert downloaded Confluence pages (ADF JSON) to clean Markdown files.

Usage:
    python scripts/export_to_markdown.py

Output: docs/{page_id}_{sanitized_title}.md
"""

import json
import re
import sys
from pathlib import Path

PAGES_DIR = Path("data/confluence/pages")
VERSIONS_DIR = Path("data/confluence/versions")
OUTPUT_DIR = Path("docs")


# ---------------------------------------------------------------------------
# ADF → Markdown converter
# ---------------------------------------------------------------------------

def convert(node: dict) -> str:
    t = node.get("type", "")
    children = node.get("content", [])

    if t == "doc":
        return _join(children)

    if t == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return f"{'#' * level} {_inline(node)}"

    if t == "paragraph":
        text = _inline(node)
        return text if text.strip() else ""

    if t == "codeBlock":
        lang = node.get("attrs", {}).get("language", "")
        return f"```{lang}\n{_plain(node)}\n```"

    if t == "bulletList":
        return "\n".join(f"- {_list_item(c)}" for c in children)

    if t == "orderedList":
        return "\n".join(f"{i}. {_list_item(c)}" for i, c in enumerate(children, 1))

    if t == "blockquote":
        inner = _join(children)
        return "\n".join(f"> {line}" for line in inner.splitlines())

    if t == "rule":
        return "---"

    if t == "table":
        return _table(node)

    if t == "hardBreak":
        return "\n"

    if t in ("mediaSingle", "media"):
        alt = node.get("attrs", {}).get("alt", "")
        return f"[image: {alt}]" if alt else ""

    if t in ("inlineCard", "blockCard", "embedCard"):
        url = node.get("attrs", {}).get("url", "")
        return f"[{url}]({url})" if url else ""

    if t == "status":
        return node.get("attrs", {}).get("text", "")

    if t == "emoji":
        return node.get("attrs", {}).get("text", "")

    if t == "mention":
        return f"@{node.get('attrs', {}).get('text', 'user')}"

    if t in ("expand", "nestedExpand"):
        title = node.get("attrs", {}).get("title", "")
        inner = _join(children)
        return f"**{title}**\n\n{inner}" if title else inner

    if t in ("bodiedExtension", "inlineExtension", "extension"):
        # Macros: try to extract nested content if present
        params = node.get("attrs", {}).get("parameters", {})
        nested = params.get("nestedContent")
        if nested:
            return convert(nested)
        return _join(children)

    if t in ("layoutSection", "layoutColumn"):
        return _join(children)

    if t == "placeholder":
        return ""

    # Fallback: recurse
    return _join(children)


def _join(children: list) -> str:
    parts = list(filter(None, (convert(c) for c in children)))
    return "\n\n".join(parts)


def _list_item(node: dict) -> str:
    parts = []
    for child in node.get("content", []):
        if child.get("type") == "paragraph":
            parts.append(_inline(child))
        elif child.get("type") in ("bulletList", "orderedList"):
            nested = convert(child)
            parts.append("\n  " + "\n  ".join(nested.splitlines()))
        else:
            text = convert(child)
            if text:
                parts.append(text)
    return " ".join(filter(None, parts))


def _table(node: dict) -> str:
    rows = []
    header_row_done = False
    for row in node.get("content", []):
        if row.get("type") != "tableRow":
            continue
        cells = []
        is_header = False
        for cell in row.get("content", []):
            if cell.get("type") == "tableHeader":
                is_header = True
            cell_text = _plain(cell).replace("|", "\\|").replace("\n", " ").strip()
            cells.append(cell_text)
        rows.append("| " + " | ".join(cells) + " |")
        if is_header and not header_row_done:
            rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
            header_row_done = True
    return "\n".join(rows)


def _inline(node: dict) -> str:
    """Extract inline content from a node, applying Markdown marks."""
    result = ""
    for child in node.get("content", []):
        t = child.get("type")
        if t == "text":
            text = child.get("text", "").replace("\xa0", " ")
            marks = {m["type"]: m.get("attrs", {}) for m in child.get("marks", [])}
            if "link" in marks:
                href = marks["link"].get("href", "")
                text = f"[{text}]({href})"
            if "code" in marks:
                text = f"`{text}`"
            if "strong" in marks:
                text = f"**{text}**"
            if "em" in marks:
                text = f"*{text}*"
            if "strike" in marks:
                text = f"~~{text}~~"
            result += text
        elif t == "hardBreak":
            result += "\n"
        elif t == "mention":
            result += f"@{child.get('attrs', {}).get('text', 'user')}"
        elif t == "emoji":
            result += child.get("attrs", {}).get("text", "")
        elif t == "inlineCard":
            url = child.get("attrs", {}).get("url", "")
            result += f"[{url}]({url})" if url else ""
        elif t == "status":
            result += child.get("attrs", {}).get("text", "")
        else:
            result += _inline(child)
    return result


def _plain(node: dict) -> str:
    """Extract raw text with no formatting."""
    if node.get("type") == "text":
        return node.get("text", "").replace("\xa0", " ")
    return "".join(_plain(c) for c in node.get("content", []))


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def sanitize(title: str) -> str:
    s = re.sub(r'[^\w\s-]', '', title)
    s = re.sub(r'\s+', '_', s.strip())
    return s[:80]


def convert_page(page_id: str, metadata: dict, version_file: Path) -> bool:
    raw = json.loads(version_file.read_text())
    content_str = raw.get("content", "")
    if not content_str:
        return False

    try:
        adf = json.loads(content_str)
    except json.JSONDecodeError:
        return False

    body = convert(adf)
    body = re.sub(r'\n{3,}', '\n\n', body).strip()
    if not body:
        return False

    title = metadata.get("title", page_id)
    space = metadata.get("space_key", "")
    url = metadata.get("_links", {}).get("base", "") + metadata.get("_links", {}).get("webui", "")

    frontmatter = (
        f"---\n"
        f"title: {title}\n"
        f"space: {space}\n"
        f"page_id: {page_id}\n"
        f"url: {url}\n"
        f"---\n\n"
    )

    output = OUTPUT_DIR / f"{page_id}_{sanitize(title)}.md"
    output.write_text(frontmatter + f"# {title}\n\n{body}\n", encoding="utf-8")
    return True


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    page_files = list(PAGES_DIR.glob("*.json"))
    total = len(page_files)
    done = skipped = errors = 0

    print(f"Converting {total} pages to Markdown in {OUTPUT_DIR}/...")

    for page_file in page_files:
        page_id = page_file.stem
        try:
            metadata = json.loads(page_file.read_text())
            version_id = metadata.get("latest_version_id")
            if not version_id:
                skipped += 1
                continue

            version_file = VERSIONS_DIR / f"{version_id}.json"
            if not version_file.exists():
                skipped += 1
                continue

            if convert_page(page_id, metadata, version_file):
                done += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"  Error {page_id}: {e}", file=sys.stderr)
            errors += 1

        if (done + skipped + errors) % 500 == 0:
            print(f"  {done + skipped + errors}/{total} processed...")

    total_size = sum(f.stat().st_size for f in OUTPUT_DIR.glob("*.md"))
    print(f"\nDone. Converted: {done} | Skipped: {skipped} | Errors: {errors}")
    print(f"Output: {done} files, {total_size / 1_000_000:.1f} MB")


if __name__ == "__main__":
    main()
