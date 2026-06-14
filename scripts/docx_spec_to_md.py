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
import zipfile
from pathlib import Path
from typing import Iterator, Union

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from spec_context import find_spec_docx  # noqa: E402

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


def _count_docx_images(docx_path: Path) -> int:
    """Embedded images (logos/branding) are not rendered to Markdown; count them
    so the requirement stays visible to agents and pipelines."""
    try:
        with zipfile.ZipFile(docx_path) as z:
            return sum(1 for n in z.namelist() if n.startswith("word/media/"))
    except (zipfile.BadZipFile, OSError):
        return 0


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


def _run_is_mono(run) -> bool:
    font_name = run.font.name.lower() if (run.font and run.font.name) else ""
    return font_name in MONO_FONTS


def _runs_to_md(paragraph: Paragraph) -> str:
    # Coalesce consecutive runs that share the same formatting so adjacent
    # bold/italic/mono runs do not emit broken markers like **a****b**.
    segments: list[list] = []  # [is_bold, is_italic, is_mono, text]
    for run in paragraph.runs:
        text = run.text
        if not text:
            continue
        is_bold = bool(run.bold)
        is_italic = bool(run.italic)
        is_mono = _run_is_mono(run)
        if segments and segments[-1][:3] == [is_bold, is_italic, is_mono]:
            segments[-1][3] += text
        else:
            segments.append([is_bold, is_italic, is_mono, text])

    parts: list[str] = []
    for is_bold, is_italic, is_mono, text in segments:
        # Keep leading/trailing whitespace outside the markers so emphasis
        # markers always hug the visible text (Markdown requires this).
        leading = text[: len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()) :]
        core = text.strip()
        if core:
            if is_bold and is_italic:
                core = f"***{core}***"
            elif is_bold:
                core = f"**{core}**"
            elif is_italic:
                core = f"*{core}*"
            if is_mono:
                core = f"`{core}`"
        parts.append(f"{leading}{core}{trailing}")
    return "".join(parts).strip()


def _paragraph_is_mono(paragraph: Paragraph) -> bool:
    """True when every non-blank run in the paragraph uses a monospace font."""
    has_text = False
    for run in paragraph.runs:
        if not run.text or not run.text.strip():
            continue
        has_text = True
        if not _run_is_mono(run):
            return False
    return has_text


SQL_START_RE = re.compile(r"^\s*(SELECT|WITH)\b", re.I)
MERMAID_RE = re.compile(
    r"\b(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram"
    r"|erDiagram|gantt|journey|pie|mindmap)\b"
)


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
        image_count = _count_docx_images(docx_path)
        if image_count:
            out.append(
                f"> **Note:** the source `.docx` contains {image_count} embedded image(s) "
                f"(logo / branding / layout mockups) that are not rendered in Markdown. "
                f"Add the branding logo from the house-style convention "
                f"(`P_LOGO`; default asset `sample_template/CSGI.jpg`)."
            )
            out.append("")

    prev_was_heading = False
    in_list = False
    code_buf: list[str] = []  # consecutive monospace paragraphs (e.g. mermaid)
    sql_buf: list[str] = []   # consecutive paragraphs forming a SQL statement
    in_sql = False

    def flush_code() -> None:
        nonlocal code_buf
        if not code_buf:
            return
        lang = "mermaid" if any(MERMAID_RE.search(line) for line in code_buf) else ""
        if out and out[-1] != "":
            out.append("")
        out.append(f"```{lang}")
        out.extend(code_buf)
        out.append("```")
        out.append("")
        code_buf = []

    def flush_sql() -> None:
        nonlocal sql_buf, in_sql
        if sql_buf:
            if out and out[-1] != "":
                out.append("")
            out.append("```sql")
            out.extend(sql_buf)
            out.append("```")
            out.append("")
        sql_buf = []
        in_sql = False

    for block in _iter_body_blocks(doc):
        if isinstance(block, Table):
            flush_code()
            flush_sql()
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
            # Blank line: stays inside an active SQL block, otherwise ends a
            # code block and adds spacing.
            if in_sql:
                continue
            flush_code()
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
            flush_code()
            flush_sql()
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

        # Monospace paragraph (mermaid, ASCII art, code) -> fenced block.
        if _paragraph_is_mono(para):
            flush_sql()
            for raw_line in para.text.split("\n"):
                code_buf.append(raw_line.rstrip())
            continue

        # Any non-mono content ends a code block.
        flush_code()

        if style_name == "Intense Quote" or style_name == "Quote":
            flush_sql()
            out.append(f"> {md_text}")
            out.append("")
            continue

        if _is_list_item(para):
            flush_sql()
            out.append(f"- {md_text}")
            in_list = True
            continue

        # SQL statement: starts at SELECT/WITH and runs until the next
        # structural element (heading, table, list item) flushes it.
        if in_sql:
            sql_buf.append(text_plain)
            continue
        if SQL_START_RE.match(text_plain):
            in_sql = True
            sql_buf.append(text_plain)
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

    flush_code()
    flush_sql()

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert functional spec .docx to .md for agents/pipelines."
    )
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        help="Input .docx (default: auto-discover via functional_spec/spec_format.json)",
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
        spec_dir = ROOT / "functional_spec"
        found = find_spec_docx(spec_dir)
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
