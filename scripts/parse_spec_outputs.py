#!/usr/bin/env python3
"""Derive JasperReports output file names from a functional spec (.md).

Agents and generators must not hardcode .jrxml names. Run this script or apply
the same rules documented in .cursor/rules/jasper-rules.md §6.

Usage:
  .venv\\Scripts\\python.exe scripts/parse_spec_outputs.py functional_spec/Invoice_Functional_Template.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "functional_spec" / "Invoice_Functional_Template.md"

PAGE_ROLE_SUFFIX: dict[str, str] = {
    "cover page": "main",
    "cover": "main",
    "detail page": "detail",
    "detail": "detail",
}


def to_snake(text: str) -> str:
    text = re.sub(r"\s+Template\s*$", "", text.strip(), flags=re.I)
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def stem_from_spec_path(spec_path: Path) -> str:
    stem = spec_path.stem
    for suffix in ("_Functional_Template", "_Functional", "_Template"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return to_snake(stem)


def parse_template_title(text: str) -> str | None:
    m = re.search(r"\*\*([^*]+Template)\*\*", text, re.I)
    if m:
        return to_snake(m.group(1))
    m = re.search(r"^#\s+(.+Template)\s*$", text, re.M | re.I)
    if m:
        return to_snake(m.group(1))
    return None


def parse_page_table(text: str) -> list[tuple[str, str]]:
    pages: list[tuple[str, str]] = []
    in_table = False
    for line in text.splitlines():
        if re.match(r"\|\s*Page\s*\|", line, re.I):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.strip().startswith("|"):
            break
        if re.match(r"\|\s*---", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].lower() != "page":
            pages.append((cells[0], cells[1]))
    return pages


def page_to_suffix(page_name: str) -> str:
    key = page_name.strip().lower()
    if key in PAGE_ROLE_SUFFIX:
        return PAGE_ROLE_SUFFIX[key]
    return to_snake(page_name.replace(" page", ""))


def parse_explicit_output_table(text: str) -> list[dict[str, str]] | None:
    """Return outputs if spec contains a table listing .jrxml files."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    file_col = name_col = role_col = None

    for line in text.splitlines():
        if ".jrxml" not in line.lower() and header is None:
            if re.search(r"\|\s*File\s*\|", line, re.I) and re.search(
                r"Jasper|Role", line, re.I
            ):
                header = [c.strip().lower() for c in line.strip().strip("|").split("|")]
                for i, col in enumerate(header):
                    if "file" in col:
                        file_col = i
                    elif "jasper" in col or "name" in col:
                        name_col = i
                    elif "role" in col:
                        role_col = i
            continue

        if header is None:
            continue
        if not line.strip().startswith("|"):
            break
        if re.match(r"\|\s*---", line):
            continue

        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if file_col is None or file_col >= len(cells):
            continue
        raw_file = cells[file_col].strip("` ")
        if not raw_file.lower().endswith(".jrxml"):
            continue

        jasper_name = Path(raw_file).stem
        if name_col is not None and name_col < len(cells):
            raw_name = cells[name_col].strip("` ")
            if raw_name:
                jasper_name = raw_name

        role = ""
        if role_col is not None and role_col < len(cells):
            role = cells[role_col]

        rows.append(
            {
                "file": raw_file,
                "jasper_name": jasper_name,
                "role": role,
            }
        )

    return rows or None


def derive_outputs(spec_path: Path, text: str | None = None) -> dict:
    content = text if text is not None else spec_path.read_text(encoding="utf-8")

    explicit = parse_explicit_output_table(content)
    if explicit:
        base = Path(explicit[0]["file"]).stem
        if base.endswith("_main"):
            base = base[: -len("_main")]
        elif base.endswith("_detail"):
            base = base[: -len("_detail")]
        return {"spec": str(spec_path), "base": base, "outputs": explicit}

    base = parse_template_title(content) or stem_from_spec_path(spec_path)
    pages = parse_page_table(content)

    if not pages:
        return {
            "spec": str(spec_path),
            "base": base,
            "outputs": [
                {
                    "file": f"{base}.jrxml",
                    "jasper_name": base,
                    "role": "Single report",
                }
            ],
        }

    outputs: list[dict[str, str]] = []
    for page_name, description in pages:
        suffix = page_to_suffix(page_name)
        jasper_name = f"{base}_{suffix}"
        outputs.append(
            {
                "file": f"{jasper_name}.jrxml",
                "jasper_name": jasper_name,
                "role": description or page_name,
            }
        )

    return {"spec": str(spec_path), "base": base, "outputs": outputs}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default=str(DEFAULT_SPEC),
        help="Path to functional spec .md (default: Invoice_Functional_Template.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON (default when stdout is not a TTY)",
    )
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    result = derive_outputs(spec_path)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
