#!/usr/bin/env python3
"""Extract formatting rules from a functional spec (.md) General Instructions section.

Agents must not hardcode spec-specific formatting checklists. Run this script (or
apply the same extraction logic) so the architect's formatting checklist tracks
the active spec after docx -> md conversion.

Section boundaries and heading patterns are driven by functional_spec/spec_format.json
so Word template structure changes rarely require Python edits.

Usage:
  .venv\\Scripts\\python.exe scripts/parse_spec_formatting.py
  .venv\\Scripts\\python.exe scripts/parse_spec_formatting.py functional_spec/MySpec.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from spec_context import (  # noqa: E402
    compile_patterns,
    load_format_config,
    resolve_active_spec,
    table_row_cells,
)

BULLET_LINE = re.compile(r"^-\s+(.*)$")
MARKDOWN_HEADING = re.compile(r"^#{1,3}\s+(.+)$")
BOLD_BULLET_SECTION = re.compile(r"^\*\*(.+?)\*\*:?\s*$")


def _clean_rule(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip().rstrip(":")


def _section_config(format_config: dict) -> dict:
    return format_config.get("formatting_section") or {}


def _heading_patterns(format_config: dict) -> list[re.Pattern[str]]:
    cfg = _section_config(format_config)
    raw = cfg.get("heading_patterns") or [r"(?i)general\s+instruction"]
    return compile_patterns(raw)


def _table_stop_patterns(format_config: dict) -> list[re.Pattern[str]]:
    cfg = _section_config(format_config)
    raw = cfg.get("stop_table_first_cell_patterns") or []
    return compile_patterns(raw)


def _matches_any(patterns: list[re.Pattern[str]], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def _is_general_instruction_heading(line: str, heading_patterns: list[re.Pattern[str]]) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    m = MARKDOWN_HEADING.match(stripped)
    if m and _matches_any(heading_patterns, m.group(1)):
        return True
    m = BULLET_LINE.match(stripped)
    if m and _matches_any(heading_patterns, m.group(1)):
        return True
    return False


def _heading_text(line: str) -> str:
    stripped = line.strip()
    m = MARKDOWN_HEADING.match(stripped)
    if m:
        return _clean_rule(m.group(1))
    m = BULLET_LINE.match(stripped)
    if m:
        return _clean_rule(m.group(1))
    return stripped


def _is_table_boundary(line: str, table_stop_patterns: list[re.Pattern[str]]) -> bool:
    cells = table_row_cells(line)
    if not cells:
        return False
    first = cells[0].strip()
    return _matches_any(table_stop_patterns, first)


def _is_section_end(
    line: str,
    *,
    after_rules: bool,
    format_config: dict,
    heading_patterns: list[re.Pattern[str]],
    table_stop_patterns: list[re.Pattern[str]],
) -> bool:
    """True when a line begins the next major spec section after General Instructions."""
    cfg = _section_config(format_config)
    stripped = line.strip()
    if not stripped:
        return False

    if cfg.get("stop_on_markdown_heading", True) and MARKDOWN_HEADING.match(stripped):
        return True

    if _is_table_boundary(stripped, table_stop_patterns):
        return True

    m = BULLET_LINE.match(stripped)
    if not m:
        return False

    body = m.group(1).strip()
    if _matches_any(heading_patterns, body):
        return False

    if cfg.get("stop_on_bold_bullet_section", True):
        bold = BOLD_BULLET_SECTION.match(body)
        if bold:
            return True

    return False


def _rule_from_bullet(line: str, heading_patterns: list[re.Pattern[str]]) -> str | None:
    m = BULLET_LINE.match(line.strip())
    if not m:
        return None
    rule = _clean_rule(m.group(1))
    if not rule or _matches_any(heading_patterns, rule):
        return None
    return rule


def extract_formatting_rules(text: str, format_config: dict | None = None) -> dict:
    fmt = format_config or load_format_config()
    heading_patterns = _heading_patterns(fmt)
    table_stop_patterns = _table_stop_patterns(fmt)

    lines = text.splitlines()
    start: int | None = None

    for i, line in enumerate(lines):
        if _is_general_instruction_heading(line, heading_patterns):
            start = i
            break

    if start is None:
        return {
            "section_heading": None,
            "rules": [],
            "found": False,
            "message": (
                "No General Instruction(s) section found. "
                "Add a matching heading to the spec or extend "
                "formatting_section.heading_patterns in functional_spec/spec_format.json."
            ),
        }

    section_heading = _heading_text(lines[start])
    rules: list[str] = []
    after_rules = False

    for line in lines[start + 1 :]:
        if _is_section_end(
            line,
            after_rules=after_rules,
            format_config=fmt,
            heading_patterns=heading_patterns,
            table_stop_patterns=table_stop_patterns,
        ):
            break

        rule = _rule_from_bullet(line, heading_patterns)
        if rule:
            rules.append(rule)
            after_rules = True

    return {
        "section_heading": section_heading,
        "rules": rules,
        "found": True,
        "message": None if rules else "General Instructions heading found but no bullet rules followed it.",
    }


def derive_formatting(
    spec_path: Path,
    text: str | None = None,
    format_config: dict | None = None,
) -> dict:
    content = text if text is not None else spec_path.read_text(encoding="utf-8")
    fmt = format_config or load_format_config()
    extracted = extract_formatting_rules(content, fmt)
    return {"spec": str(spec_path), **extracted}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default=None,
        help="Path to functional spec .md or .docx (default: auto-discover under functional_spec/)",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not regenerate .md from .docx even when stale",
    )
    parser.add_argument(
        "--format-config",
        type=Path,
        default=None,
        help="Override path to spec_format.json",
    )
    args = parser.parse_args(argv)

    try:
        active = resolve_active_spec(
            args.spec,
            sync=not args.no_sync,
            format_config_path=args.format_config,
        )
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    fmt = load_format_config(args.format_config)
    result = derive_formatting(active.md, format_config=fmt)
    if active.synced:
        result["synced_from_docx"] = str(active.docx)
    print(json.dumps(result, indent=2))
    return 0 if result.get("found") else 1


if __name__ == "__main__":
    sys.exit(main())
