#!/usr/bin/env python3
"""Extract formatting rules from a functional spec (.md) General Instructions section.

Agents must not hardcode spec-specific formatting checklists. Run this script (or
apply the same extraction logic) so the architect's formatting checklist tracks
the active spec after docx -> md conversion.

Usage:
  .venv\\Scripts\\python.exe scripts/parse_spec_formatting.py functional_spec/Invoice_Functional_Template.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "functional_spec" / "Invoice_Functional_Template.md"

GENERAL_INSTRUCTION_HEADING = re.compile(
    r"(?i)general\s+instruction",
)
BULLET_LINE = re.compile(r"^-\s+(.*)$")
MARKDOWN_HEADING = re.compile(r"^#{1,3}\s+(.+)$")
BOLD_BULLET_SECTION = re.compile(r"^\*\*(.+?)\*\*:?\s*$")


def _clean_rule(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text.strip().rstrip(":")


def _is_general_instruction_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    m = MARKDOWN_HEADING.match(stripped)
    if m and GENERAL_INSTRUCTION_HEADING.search(m.group(1)):
        return True
    m = BULLET_LINE.match(stripped)
    if m and GENERAL_INSTRUCTION_HEADING.search(m.group(1)):
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


def _is_section_end(line: str, *, after_rules: bool) -> bool:
    """True when a line begins the next major spec section after General Instructions."""
    stripped = line.strip()
    if not stripped:
        return False

    if MARKDOWN_HEADING.match(stripped):
        return True

    if re.match(r"^\| REPORT\s*\|", stripped, re.I):
        return True

    if after_rules and re.match(r"^\| Page\s*\|", stripped, re.I):
        return True

    m = BULLET_LINE.match(stripped)
    if not m:
        return False

    body = m.group(1).strip()
    if GENERAL_INSTRUCTION_HEADING.search(body):
        return False

    bold = BOLD_BULLET_SECTION.match(body)
    if bold:
        return True

    return False


def _rule_from_bullet(line: str) -> str | None:
    m = BULLET_LINE.match(line.strip())
    if not m:
        return None
    rule = _clean_rule(m.group(1))
    if not rule or GENERAL_INSTRUCTION_HEADING.search(rule):
        return None
    return rule


def extract_formatting_rules(text: str) -> dict:
    lines = text.splitlines()
    start: int | None = None

    for i, line in enumerate(lines):
        if _is_general_instruction_heading(line):
            start = i
            break

    if start is None:
        return {
            "section_heading": None,
            "rules": [],
            "found": False,
            "message": (
                "No General Instruction(s) section found. "
                "Add a 'General Instruction' heading to the spec or scan the full .md manually."
            ),
        }

    section_heading = _heading_text(lines[start])
    rules: list[str] = []
    after_rules = False

    for line in lines[start + 1 :]:
        if _is_section_end(line, after_rules=after_rules):
            break

        rule = _rule_from_bullet(line)
        if rule:
            rules.append(rule)
            after_rules = True

    return {
        "section_heading": section_heading,
        "rules": rules,
        "found": True,
        "message": None if rules else "General Instructions heading found but no bullet rules followed it.",
    }


def derive_formatting(spec_path: Path, text: str | None = None) -> dict:
    content = text if text is not None else spec_path.read_text(encoding="utf-8")
    extracted = extract_formatting_rules(content)
    return {"spec": str(spec_path), **extracted}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default=str(DEFAULT_SPEC),
        help="Path to functional spec .md (default: Invoice_Functional_Template.md)",
    )
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    result = derive_formatting(spec_path)
    print(json.dumps(result, indent=2))
    return 0 if result.get("found") else 1


if __name__ == "__main__":
    sys.exit(main())
