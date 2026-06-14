#!/usr/bin/env python3
"""Compile JasperReports .jrxml templates to .jasper.

.jasper files are build artifacts (compiled reports) - they are git-ignored and
regenerated from .jrxml. The main report loads the detail subreport as a compiled
.jasper, so the detail must be compiled before previewing the main report.

This wraps JasperStarter (https://jasperstarter.sourceforge.io/), the standard
command-line JasperReports compiler. It is discovered via:
  1. --jasperstarter <path> argument
  2. JASPERSTARTER environment variable (full path to the executable)
  3. `jasperstarter` on PATH

If JasperStarter is not available, compile inside iReport 5.6.0 / Jaspersoft
Studio instead (right-click the .jrxml -> Compile Report).

Usage:
  .venv\\Scripts\\python.exe scripts/compile_jasper.py
  .venv\\Scripts\\python.exe scripts/compile_jasper.py output\\national_invoice_usage_detail.jrxml
  .venv\\Scripts\\python.exe scripts/compile_jasper.py output\\ --jasperstarter C:\\tools\\jasperstarter\\bin\\jasperstarter.bat
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "output"


def find_jasperstarter(explicit: str | None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() or shutil.which(explicit) else None
    env = os.environ.get("JASPERSTARTER")
    if env and (Path(env).exists() or shutil.which(env)):
        return env
    return shutil.which("jasperstarter")


def collect_jrxml(target: Path) -> list[Path]:
    if target.is_dir():
        return sorted(target.glob("*.jrxml"))
    if target.suffix.lower() == ".jrxml" and target.is_file():
        return [target]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", default=str(DEFAULT_TARGET), help="A .jrxml file or a directory of .jrxml files (default: output/)")
    parser.add_argument("--jasperstarter", help="Path to the jasperstarter executable")
    args = parser.parse_args(argv)

    target = Path(args.target)
    jrxml_files = collect_jrxml(target)
    if not jrxml_files:
        print(f"No .jrxml files found at: {target}", file=sys.stderr)
        return 1

    tool = find_jasperstarter(args.jasperstarter)
    if not tool:
        print(
            "JasperStarter not found. Install it (https://jasperstarter.sourceforge.io/),\n"
            "set the JASPERSTARTER environment variable or pass --jasperstarter <path>,\n"
            "or compile the .jrxml inside iReport 5.6.0 / Jaspersoft Studio.\n"
            f"Files to compile: {', '.join(p.name for p in jrxml_files)}",
            file=sys.stderr,
        )
        return 2

    failures = 0
    for jrxml in jrxml_files:
        out_dir = jrxml.parent
        print(f"Compiling {jrxml.name} -> {jrxml.with_suffix('.jasper').name}")
        result = subprocess.run(
            [tool, "compile", str(jrxml), "-o", str(out_dir / jrxml.stem)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            failures += 1
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)

    if failures:
        print(f"{failures} of {len(jrxml_files)} file(s) failed to compile.", file=sys.stderr)
        return 1

    print(f"Compiled {len(jrxml_files)} file(s) to .jasper.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
