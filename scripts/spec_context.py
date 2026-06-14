#!/usr/bin/env python3
"""Shared spec discovery, docx→md sync, and format-config loading.

Scripts must not hardcode a single spec filename or invoice-specific table
shapes.  Load ``functional_spec/spec_format.json`` (or pass a custom path) and
use ``resolve_active_spec()`` so edits to the Word template structure are
handled by config + generic parsers rather than code changes.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "functional_spec"
DEFAULT_FORMAT_CONFIG = SPEC_DIR / "spec_format.json"

# Built-in defaults if spec_format.json is missing or partial.
_BUILTIN_FORMAT: dict[str, Any] = {
    "version": 1,
    "docx_discovery": {
        "prefer_patterns": [
            "*_Functional_Template.docx",
            "*_Functional_Technical_Spec.docx",
        ],
    },
    "formatting_section": {
        "heading_patterns": [r"(?i)general\s+instruction"],
        "stop_on_markdown_heading": True,
        "stop_on_bold_bullet_section": True,
        "stop_table_first_cell_patterns": [
            r"(?i)^report\s*$",
            r"(?i)^page\s*$",
        ],
    },
    "outputs": {
        "template_title_patterns": [
            r"\*\*([^*]+Template)\*\*",
            r"^#\s+(.+Template)\s*$",
        ],
        "spec_stem_suffixes": [
            "_Functional_Template",
            "_Functional",
            "_Template",
        ],
        "page_table": {
            "first_column_headers": ["page"],
            "min_columns": 2,
        },
        "explicit_output_table": {
            "file_column_headers": ["file"],
            "name_column_headers": ["jasper", "name"],
            "role_column_headers": ["role"],
            "table_must_contain": ["jasper", "role"],
            "file_extension": ".jrxml",
        },
        "page_role_suffix": {
            "cover page": "main",
            "cover": "main",
            "detail page": "detail",
            "detail": "detail",
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_format_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load format markers; falls back to built-in defaults."""
    path = config_path or DEFAULT_FORMAT_CONFIG
    fmt = dict(_BUILTIN_FORMAT)
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                fmt = _deep_merge(fmt, raw)
        except (json.JSONDecodeError, OSError):
            pass
    return fmt


def find_spec_docx(
    spec_dir: Path | None = None,
    *,
    name: str | None = None,
    format_config: dict[str, Any] | None = None,
) -> Path | None:
    """Return a .docx under functional_spec/ (explicit name or discovery)."""
    directory = (spec_dir or SPEC_DIR).resolve()
    if not directory.is_dir():
        return None

    if name:
        candidate = directory / name
        if candidate.suffix.lower() != ".docx":
            candidate = candidate.with_suffix(".docx")
        return candidate if candidate.is_file() else None

    fmt = format_config or load_format_config()
    patterns = fmt.get("docx_discovery", {}).get("prefer_patterns") or []
    for pattern in patterns:
        matches = sorted(
            directory.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]

    docs = sorted(
        (p for p in directory.glob("*.docx") if not p.name.startswith("~$")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return docs[0] if docs else None


def paired_md_path(docx_path: Path) -> Path:
    return docx_path.with_suffix(".md")


def find_spec_md(
    spec_dir: Path | None = None,
    *,
    docx_path: Path | None = None,
    name: str | None = None,
) -> Path | None:
    """Return the .md paired with a docx, or the newest .md in the folder."""
    directory = (spec_dir or SPEC_DIR).resolve()
    if docx_path is not None:
        md = paired_md_path(docx_path)
        return md if md.is_file() else None
    if name:
        candidate = directory / name
        if candidate.suffix.lower() != ".md":
            candidate = candidate.with_suffix(".md")
        return candidate if candidate.is_file() else None
    docs = sorted(
        directory.glob("*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return docs[0] if docs else None


def md_is_stale(docx_path: Path, md_path: Path) -> bool:
    if not md_path.is_file():
        return True
    try:
        return docx_path.stat().st_mtime > md_path.stat().st_mtime
    except OSError:
        return True


def ensure_spec_md(
    docx_path: Path,
    md_path: Path | None = None,
    *,
    force: bool = False,
) -> Path:
    """Convert docx→md when missing or stale. Returns the .md path."""
    out = md_path or paired_md_path(docx_path)
    if force or md_is_stale(docx_path, out):
        if str(ROOT / "scripts") not in sys.path:
            sys.path.insert(0, str(ROOT / "scripts"))
        from docx_spec_to_md import convert  # noqa: WPS433

        convert(docx_path, out, front_matter=True)
    return out


@dataclass
class ActiveSpec:
    docx: Path | None
    md: Path
    format_config: dict[str, Any]
    synced: bool


def resolve_active_spec(
    spec: str | Path | None = None,
    *,
    sync: bool = True,
    force_sync: bool = False,
    format_config_path: Path | None = None,
) -> ActiveSpec:
    """Resolve the active spec for pipeline scripts.

    * ``spec`` may be a .docx, .md, or bare stem/name under functional_spec/.
    * When a .docx is resolved and ``sync`` is true, regenerates stale .md.
    * When only .md exists, returns it without sync.
    """
    fmt = load_format_config(format_config_path)
    synced = False
    docx: Path | None = None
    md: Path | None = None

    if spec is not None:
        path = Path(spec)
        if not path.is_absolute():
            for base in (SPEC_DIR, ROOT):
                candidate = base / path
                if candidate.exists():
                    path = candidate
                    break
        path = path.resolve()
        if path.suffix.lower() == ".docx":
            docx = path
            md = paired_md_path(docx)
        elif path.suffix.lower() == ".md":
            md = path
            sibling = path.with_suffix(".docx")
            docx = sibling if sibling.is_file() else None
        else:
            docx = find_spec_docx(name=path.name, format_config=fmt)
            md = find_spec_md(docx_path=docx) if docx else find_spec_md(name=f"{path.name}.md")
    else:
        docx = find_spec_docx(format_config=fmt)
        if docx:
            md = paired_md_path(docx)
        else:
            md = find_spec_md()

    if md is None and docx is not None:
        md = paired_md_path(docx)

    if md is None:
        raise FileNotFoundError(
            "No functional spec found. Add a .docx or .md under functional_spec/ "
            "or pass an explicit path."
        )

    if sync and docx is not None and docx.is_file():
        if force_sync or md_is_stale(docx, md):
            ensure_spec_md(docx, md, force=force_sync)
            synced = True

    if not md.is_file():
        raise FileNotFoundError(
            f"Markdown spec missing: {md}. "
            f"Run: .venv\\Scripts\\python.exe scripts/sync_spec.py"
        )

    return ActiveSpec(docx=docx, md=md, format_config=fmt, synced=synced)


def compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for raw in patterns:
        try:
            compiled.append(re.compile(raw))
        except re.error:
            continue
    return compiled


def header_matches(cell: str, headers: list[str]) -> bool:
    """True when a table header cell matches any configured keyword."""
    key = cell.strip().lower()
    return any(h in key for h in headers)


def table_row_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    if re.match(r"^\|\s*---", stripped):
        return None
    return [c.strip() for c in stripped.strip("|").split("|")]
