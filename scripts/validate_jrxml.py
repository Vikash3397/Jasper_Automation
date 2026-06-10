#!/usr/bin/env python3
"""Validate generated JRXML before iReport load. Exit 1 on failure."""
from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# JasperReports / iReport inject these; declaring them causes duplicate-parameter errors.
BUILTIN_PARAMETERS = frozenset(
    {
        "REPORT_CONNECTION",
        "REPORT_DATA_SOURCE",
        "REPORT_SCRIPTLET",
        "REPORT_LOCALE",
        "REPORT_RESOURCE_BUNDLE",
        "REPORT_TIME_ZONE",
        "REPORT_VIRTUALIZER",
        "REPORT_CLASS_LOADER",
        "REPORT_URL_HANDLER_FACTORY",
        "REPORT_FILE_RESOLVER",
        "REPORT_FORMAT_FACTORY",
        "REPORT_MAX_COUNT",
        "IS_IGNORE_PAGINATION",
    }
)

# Elements that must not carry layout attrs directly (iReport 5.6.0 schema).
LAYOUT_PARENT_TAGS = ("textField", "staticText", "image", "line", "rectangle", "subreport")
LAYOUT_ATTRS = ("x", "y", "width", "height", "uuid", "style", "key", "positionType")

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

# iReport 5.6 / JasperReports schema: band sections must appear in this order (after <group> blocks).
BAND_ORDER = (
    "background",
    "title",
    "pageHeader",
    "columnHeader",
    "detail",
    "columnFooter",
    "pageFooter",
    "lastPageFooter",
    "summary",
    "noData",
)
BAND_INDEX = {name: i for i, name in enumerate(BAND_ORDER)}
BAND_TAG_RE = re.compile(
    r"<(" + "|".join(BAND_ORDER) + r")(?:\s|>)"
)


def _find_duplicates(names: list[str]) -> list[str]:
    return [n for n, c in Counter(names).items() if c > 1]


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")

    try:
        ET.parse(path)
    except ET.ParseError as e:
        errors.append(f"{path}: XML parse error: {e}")
        return errors

    for kind, pattern in (
        ("parameter", r'<parameter\s+name="([^"]+)"'),
        ("field", r'<field\s+name="([^"]+)"'),
        ("variable", r'<variable\s+name="([^"]+)"'),
        ("group", r'<group\s+name="([^"]+)"'),
    ):
        names = re.findall(pattern, text)
        dup = _find_duplicates(names)
        if dup:
            errors.append(f"{path}: duplicate {kind}(s): {', '.join(dup)}")

    for pname in re.findall(r'<parameter\s+name="([^"]+)"', text):
        if pname in BUILTIN_PARAMETERS:
            errors.append(
                f"{path}: do not declare built-in parameter '{pname}' "
                f"(use $P{{{pname}}} only; engine provides it)"
            )

    for tag in LAYOUT_PARENT_TAGS:
        for m in re.finditer(rf"<{tag}\b([^>/]*)/?>", text):
            attrs = m.group(1)
            for attr in LAYOUT_ATTRS:
                if re.search(rf'\b{attr}\s*=', attrs):
                    errors.append(
                        f"{path}: attribute '{attr}' on <{tag}> — move to <reportElement>"
                    )
                    break

    # printWhenExpression must be inside <reportElement>, not a sibling after self-closing tag
    if re.search(r"<reportElement\b[^>]*/>\s*<printWhenExpression", text):
        errors.append(
            f"{path}: <printWhenExpression> must be nested inside <reportElement>, "
            "not as a sibling after a self-closing <reportElement/>"
        )

    for uid in re.findall(r'uuid="([^"]+)"', text):
        if not UUID_RE.match(uid):
            errors.append(f"{path}: invalid uuid '{uid}'")

    if re.search(r"\$[FVP]\{\{", text):
        errors.append(
            f"{path}: double-brace expression (e.g. $F{{{{FIELD}}}}) — "
            "use single braces: $F{FIELD}"
        )

    last_band_idx = -1
    for band in BAND_TAG_RE.findall(text):
        idx = BAND_INDEX[band]
        if idx < last_band_idx:
            errors.append(
                f"{path}: band <{band}> is out of schema order — "
                f"expected order: {', '.join(BAND_ORDER)}"
            )
        last_band_idx = idx

    for section in BAND_ORDER:
        for m in re.finditer(rf"<{section}\b[^>]*>(.*?)</{section}>", text, re.DOTALL):
            band_count = len(re.findall(r"<band\b", m.group(1)))
            if band_count > 1:
                errors.append(
                    f"{path}: <{section}> has {band_count} <band> elements — "
                    "schema allows only one; merge into a single band"
                )

    return errors


def main(argv: list[str]) -> int:
    targets = [Path(p) for p in argv[1:]] if len(argv) > 1 else list(Path("output").glob("*.jrxml"))
    if not targets:
        print("No JRXML files to validate.", file=sys.stderr)
        return 1

    files: list[Path] = []
    for path in targets:
        if path.is_dir():
            files.extend(sorted(path.glob("*.jrxml")))
        else:
            files.append(path)

    all_errors: list[str] = []
    for f in files:
        all_errors.extend(validate_file(f))

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    print(f"OK: {len(files)} file(s) validated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
