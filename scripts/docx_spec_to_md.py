#!/usr/bin/env python3
"""
Convert a functional spec Word document (.docx) to Markdown (.md) for agents and pipelines.

Preserves document order (paragraphs and tables interleaved), headings, tables,
bullets, bold/italic, and monospace (Consolas) runs.

Usage:
  .venv\\Scripts\\python.exe scripts/docx_spec_to_md.py
  .venv\\Scripts\\python.exe scripts/docx_spec_to_md.py functional_spec/MySpec.docx
  .venv\\Scripts\\python.exe scripts/docx_spec_to_md.py in.docx out.md
  .venv\\Scripts\\python.exe scripts/docx_spec_to_md.py --watch functional_spec/
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Iterator, Union

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "functional_spec" / "Invoice_Functional_Template.docx"

# Word style name -> markdown heading level (0 = #, 1 = ##, ...)
HEADING_STYLES: dict[str, int] = {
    "Title": 0,
    "Heading 1": 0,
    "Heading 2": 1,
    "Heading 3": 2,
    "Heading 4": 3,
    "Heading 5": 4,
    "Heading 6": 5,
}

LIST_STYLES = frozenset(
    {
        "List Bullet",
        "List Paragraph",
        "List Number",
        "List Continue",
        "List Bullet 2",
        "List Bullet 3",
    }
)

MONO_FONTS = frozenset({"consolas", "courier new", "courier", "lucida console"})

GENERATED_FOOTER = re.compile(
    r"^Generated from .+\. Machine-readable source:", re.I
)


def _iter_body_blocks(parent: DocumentObject) -> Iterator[Union[Paragraph, Table]]:
    """Yield paragraphs and tables in document order."""
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _escape_md_cell(text: str) -> str:
    text = text.replace("\n", " ").strip()
    text = text.replace("|", "\\|")
    return text


def _runs_to_md(paragraph: Paragraph) -> str:
    parts: list[str] = []
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        font_name = ""
        if run.font and run.font.name:
            font_name = run.font.name.lower()
        is_mono = font_name in MONO_FONTS
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        if is_mono:
            text = f"`{text}`"
        parts.append(text)
    return "".join(parts).strip()


def _heading_level(paragraph: Paragraph) -> int | None:
    name = paragraph.style.name if paragraph.style else ""
    if name in HEADING_STYLES:
        return HEADING_STYLES[name]
    if name.startswith("Heading "):
        try:
            n = int(name.split()[-1])
            return max(0, min(n - 1, 5))
        except ValueError:
            pass
    return None


def _is_list_item(paragraph: Paragraph) -> bool:
    name = paragraph.style.name if paragraph.style else ""
    if name in LIST_STYLES:
        return True
    # Numbered / bullet via numPr
    p_pr = paragraph._p.pPr
    if p_pr is not None and p_pr.numPr is not None:
        return True
    return False


def _table_to_md(table: Table) -> list[str]:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = [_escape_md_cell(cell.text) for cell in row.cells]
        rows.append(cells)
    if not rows:
        return []
    ncols = max(len(r) for r in rows)
    lines: list[str] = []
    for i, row in enumerate(rows):
        padded = row + [""] * (ncols - len(row))
        lines.append("| " + " | ".join(padded) + " |")
        if i == 0:
            lines.append("| " + " | ".join(["---"] * ncols) + " |")
    return lines


def convert(docx_path: Path, md_path: Path, *, front_matter: bool = True) -> None:
    doc = Document(str(docx_path))
    out: list[str] = []

    if front_matter:
        try:
            rel_docx = docx_path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            rel_docx = docx_path
        out.append(f"<!-- Auto-generated from {docx_path.name}. Edit the .docx and re-run docx_spec_to_md.py -->")
        out.append("")
        out.append(
            f"> **Source:** `{docx_path.name}`  "
            f"**Pipeline format:** Markdown for agents. "
            f"Regenerate: `.venv\\Scripts\\python.exe scripts/docx_spec_to_md.py {rel_docx.as_posix()}`"
        )
        out.append("")

    prev_was_heading = False
    in_list = False

    for block in _iter_body_blocks(doc):
        if isinstance(block, Table):
            if in_list:
                in_list = False
            table_lines = _table_to_md(block)
            if table_lines:
                if out and out[-1] != "":
                    out.append("")
                out.extend(table_lines)
                out.append("")
            continue

        para: Paragraph = block
        text_plain = para.text.strip()
        if not text_plain:
            if in_list:
                in_list = False
            if out and out[-1] != "":
                out.append("")
            continue

        if GENERATED_FOOTER.match(text_plain):
            continue

        md_text = _runs_to_md(para) or text_plain
        style_name = para.style.name if para.style else ""

        level = _heading_level(para)
        if level is not None:
            if in_list:
                in_list = False
            prefix = "#" * (level + 1)
            if out and out[-1] != "" and not prev_was_heading:
                out.append("")
            out.append(f"{prefix} {md_text}")
            out.append("")
            prev_was_heading = True
            continue

        prev_was_heading = False

        if style_name == "Intense Quote" or style_name == "Quote":
            out.append(f"> {md_text}")
            out.append("")
            continue

        if _is_list_item(para):
            out.append(f"- {md_text}")
            in_list = True
            continue

        if in_list:
            in_list = False
            out.append("")

        # Detect checklist-style lines from our docx exporter
        if md_text.startswith("☐ "):
            out.append(f"- [ ] {md_text[2:].strip()}")
            in_list = True
            continue

        out.append(md_text)
        out.append("")

    # Normalize: collapse 3+ blank lines to 2, strip trailing blanks
    normalized: list[str] = []
    blank_run = 0
    for line in out:
        if line == "":
            blank_run += 1
            if blank_run <= 2:
                normalized.append(line)
        else:
            blank_run = 0
            normalized.append(line)
    while normalized and normalized[-1] == "":
        normalized.pop()
    normalized.append("")

    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(normalized), encoding="utf-8", newline="\n")
    print(f"Wrote {md_path} ({len(normalized)} lines)")


def _default_out(docx_path: Path) -> Path:
    return docx_path.with_suffix(".md")


def _find_docx(spec_dir: Path) -> Path | None:
    for pattern in ("*_Functional_Template.docx", "*_Functional_Technical_Spec.docx"):
        candidates = sorted(
            spec_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
    docs = sorted(spec_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
    return docs[0] if docs else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert functional spec .docx to .md for agents/pipelines."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Input .docx (default: Invoice_Functional_Template.docx or latest *_Functional_*.docx in functional_spec/)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output .md (default: same name as input, .md extension)",
    )
    parser.add_argument(
        "--no-front-matter",
        action="store_true",
        help="Omit auto-generated HTML comment and source banner",
    )
    parser.add_argument(
        "--watch",
        type=Path,
        metavar="DIR",
        help="Watch directory for .docx changes and reconvert (poll every 2s)",
    )
    args = parser.parse_args()

    if args.watch:
        watch_dir = args.watch.resolve()
        if not watch_dir.is_dir():
            print(f"Not a directory: {watch_dir}", file=sys.stderr)
            return 1
        print(f"Watching {watch_dir} for .docx changes (Ctrl+C to stop)...")
        mtimes: dict[Path, float] = {}
        while True:
            for docx in watch_dir.glob("*.docx"):
                if docx.name.startswith("~$"):
                    continue
                try:
                    mtime = docx.stat().st_mtime
                except OSError:
                    continue
                if mtimes.get(docx) != mtime:
                    mtimes[docx] = mtime
                    out = _default_out(docx)
                    try:
                        convert(docx, out, front_matter=not args.no_front_matter)
                    except Exception as e:
                        print(f"Error converting {docx}: {e}", file=sys.stderr)
            time.sleep(2)

    docx_in = args.input
    if docx_in is None:
        if DEFAULT_IN.exists():
            docx_in = DEFAULT_IN
        else:
            spec_dir = ROOT / "functional_spec"
            found = _find_docx(spec_dir)
            if found is None:
                print(
                    "No input .docx. Pass a path or add a file under functional_spec/",
                    file=sys.stderr,
                )
                return 1
            docx_in = found

    docx_in = docx_in.resolve()
    if not docx_in.exists():
        print(f"Missing: {docx_in}", file=sys.stderr)
        return 1
    if docx_in.suffix.lower() != ".docx":
        print(f"Expected .docx: {docx_in}", file=sys.stderr)
        return 1

    md_out = (args.output or _default_out(docx_in)).resolve()

    try:
        convert(docx_in, md_out, front_matter=not args.no_front_matter)
    except PermissionError:
        print(
            f"Cannot read {docx_in} — close Word if the file is open, then retry.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
