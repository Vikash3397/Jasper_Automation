#!/usr/bin/env python3
"""Sync functional spec .docx → .md and print resolved pipeline context.

Run after editing the Word template so all downstream scripts see the current
format.  Parsers read functional_spec/spec_format.json for section/table markers
instead of hardcoded invoice-specific shapes.

Usage:
  .venv\\Scripts\\python.exe scripts/sync_spec.py
  .venv\\Scripts\\python.exe scripts/sync_spec.py functional_spec/MySpec.docx
  .venv\\Scripts\\python.exe scripts/sync_spec.py --force
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from parse_spec_formatting import derive_formatting  # noqa: E402
from parse_spec_outputs import derive_outputs  # noqa: E402
from spec_context import load_format_config, resolve_active_spec  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default=None,
        help="Path to .docx or .md (default: auto-discover under functional_spec/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate .md from .docx even when .md is newer",
    )
    parser.add_argument(
        "--format-config",
        type=Path,
        default=None,
        help="Override path to spec_format.json",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not regenerate .md from .docx even when stale",
    )
    args = parser.parse_args(argv)

    try:
        active = resolve_active_spec(
            args.spec,
            sync=not args.no_sync,
            force_sync=args.force,
            format_config_path=args.format_config,
        )
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    fmt = load_format_config(args.format_config)
    text = active.md.read_text(encoding="utf-8")

    result = {
        "docx": str(active.docx) if active.docx else None,
        "md": str(active.md),
        "synced_from_docx": active.synced,
        "format_config": str(args.format_config or (ROOT / "functional_spec" / "spec_format.json")),
        "outputs": derive_outputs(active.md, text=text, format_config=fmt),
        "formatting": derive_formatting(active.md, text=text, format_config=fmt),
    }

    print(json.dumps(result, indent=2))

    if not result["formatting"].get("found"):
        print(
            "Warning: formatting rules not found — check "
            "formatting_section.heading_patterns in spec_format.json",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
