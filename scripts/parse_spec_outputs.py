#!/usr/bin/env python3
"""Derive JasperReports output file names from a functional spec (.md).

Agents and generators must not hardcode .jrxml names. Run this script or apply
the same rules documented in .cursor/rules/jasper-rules.md §6.

Table shapes, page-role mapping, and title patterns are driven by
functional_spec/spec_format.json so Word template structure changes rarely
require Python edits.

Usage:
  .venv\\Scripts\\python.exe scripts/parse_spec_outputs.py
  .venv\\Scripts\\python.exe scripts/parse_spec_outputs.py functional_spec/MySpec.md
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
    header_matches,
    load_format_config,
    resolve_active_spec,
    table_row_cells,
)


def to_snake(text: str) -> str:
    text = re.sub(r"\s+Template\s*$", "", text.strip(), flags=re.I)
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text


def _outputs_config(format_config: dict) -> dict:
    return format_config.get("outputs") or {}


def stem_from_spec_path(spec_path: Path, format_config: dict | None = None) -> str:
    cfg = _outputs_config(format_config or load_format_config())
    stem = spec_path.stem
    for suffix in cfg.get("spec_stem_suffixes") or []:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return to_snake(stem)


def parse_template_title(text: str, format_config: dict | None = None) -> str | None:
    cfg = _outputs_config(format_config or load_format_config())
    for raw in cfg.get("template_title_patterns") or []:
        flags = re.I | (re.M if raw.startswith("^") else 0)
        m = re.search(raw, text, flags)
        if m:
            return to_snake(m.group(1))
    return None


def parse_page_table(text: str, format_config: dict | None = None) -> list[tuple[str, str]]:
    cfg = _outputs_config(format_config or load_format_config())
    page_cfg = cfg.get("page_table") or {}
    page_headers = [h.lower() for h in page_cfg.get("first_column_headers") or ["page"]]
    min_cols = int(page_cfg.get("min_columns") or 2)

    pages: list[tuple[str, str]] = []
    in_table = False
    header_seen = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if in_table:
                break
            continue
        if re.match(r"^\|\s*---", stripped):
            continue

        cells = table_row_cells(line)
        if cells is None:
            continue

        if not header_seen:
            if header_matches(cells[0], page_headers):
                in_table = True
                header_seen = True
            continue

        if len(cells) >= min_cols and cells[0].lower() not in page_headers:
            pages.append((cells[0], cells[1]))

    return pages


def page_to_suffix(page_name: str, format_config: dict | None = None) -> str:
    cfg = _outputs_config(format_config or load_format_config())
    role_map = {k.lower(): v for k, v in (cfg.get("page_role_suffix") or {}).items()}
    key = page_name.strip().lower()
    if key in role_map:
        return role_map[key]
    return to_snake(page_name.replace(" page", ""))


def _column_index(headers: list[str], keywords: list[str]) -> int | None:
    for i, col in enumerate(headers):
        if header_matches(col, keywords):
            return i
    return None


def parse_explicit_output_table(
    text: str, format_config: dict | None = None
) -> list[dict[str, str]] | None:
    """Return outputs if spec contains a table listing .jrxml files."""
    cfg = _outputs_config(format_config or load_format_config())
    table_cfg = cfg.get("explicit_output_table") or {}
    ext = (table_cfg.get("file_extension") or ".jrxml").lower()
    must_contain = [s.lower() for s in table_cfg.get("table_must_contain") or []]

    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    file_col = name_col = role_col = None

    for line in text.splitlines():
        cells = table_row_cells(line)
        if cells is None:
            if header is not None:
                break
            continue

        if header is None:
            row_lower = " ".join(c.lower() for c in cells)
            has_file = header_matches(cells[0], table_cfg.get("file_column_headers") or ["file"])
            if not has_file and "file" not in row_lower:
                continue
            if must_contain and not all(token in row_lower for token in must_contain):
                continue
            header = [c.strip().lower() for c in cells]
            file_col = _column_index(header, table_cfg.get("file_column_headers") or ["file"])
            name_col = _column_index(header, table_cfg.get("name_column_headers") or ["jasper", "name"])
            role_col = _column_index(header, table_cfg.get("role_column_headers") or ["role"])
            continue

        if file_col is None or file_col >= len(cells):
            continue
        raw_file = cells[file_col].strip("` ")
        if not raw_file.lower().endswith(ext):
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


def derive_outputs(
    spec_path: Path,
    text: str | None = None,
    format_config: dict | None = None,
) -> dict:
    fmt = format_config or load_format_config()
    content = text if text is not None else spec_path.read_text(encoding="utf-8")

    explicit = parse_explicit_output_table(content, fmt)
    if explicit:
        base = Path(explicit[0]["file"]).stem
        if base.endswith("_main"):
            base = base[: -len("_main")]
        elif base.endswith("_detail"):
            base = base[: -len("_detail")]
        return {"spec": str(spec_path), "base": base, "outputs": explicit}

    base = parse_template_title(content, fmt) or stem_from_spec_path(spec_path, fmt)
    pages = parse_page_table(content, fmt)

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
        suffix = page_to_suffix(page_name, fmt)
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
    result = derive_outputs(active.md, format_config=fmt)
    if active.synced:
        result["synced_from_docx"] = str(active.docx)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
