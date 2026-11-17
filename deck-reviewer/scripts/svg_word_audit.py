#!/usr/bin/env python3
"""Audit SVG diagrams for visual density: <= 35 total words, <= 5 words per <text>, no bullets."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path


TEXT_NODE_RE = re.compile(r"<text\b[^>]*>(.*?)</text>", re.DOTALL)


def audit_svg(svg_path: Path, max_total: int = 35, max_node: int = 5) -> list[str]:
    """Return a list of violation strings for a single SVG file."""
    content = svg_path.read_text(encoding="utf-8")
    violations: list[str] = []
    total_words = 0

    for idx, match in enumerate(TEXT_NODE_RE.finditer(content), start=1):
        raw_inner = match.group(1)
        plain = html.unescape(re.sub(r"<[^>]+>", "", raw_inner)).replace("\u200b", "").strip()
        if not plain:
            continue
        if "•" in plain:
            violations.append(f"{svg_path.name} node#{idx}: banned bullet '•' in '{plain}'")
        words = plain.split()
        total_words += len(words)
        if len(words) > max_node:
            violations.append(
                f"{svg_path.name} node#{idx}: {len(words)} words (max {max_node}): '{plain}'"
            )

    if total_words > max_total:
        violations.append(
            f"{svg_path.name}: {total_words} total words (max {max_total})"
        )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit SVG files for word-count visual density.")
    parser.add_argument("target", type=Path, help="SVG file or directory of SVGs")
    parser.add_argument("--max-total", type=int, default=35)
    parser.add_argument("--max-node", type=int, default=5)
    args = parser.parse_args()

    target = args.target.resolve()
    files = sorted(target.glob("*.svg")) if target.is_dir() else [target]
    if not files:
        print(f"No SVG files found in {target}")
        return 0

    all_violations: list[str] = []
    for f in files:
        v = audit_svg(f, max_total=args.max_total, max_node=args.max_node)
        all_violations.extend(v)

    if all_violations:
        for line in all_violations:
            print(f"FAIL: {line}", file=sys.stderr)
        return 1

    print(f"SVG Word Audit PASS: {len(files)} file(s) <= {args.max_total} total words and <= {args.max_node} words/node.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
