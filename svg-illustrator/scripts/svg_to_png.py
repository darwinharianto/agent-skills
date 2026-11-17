#!/usr/bin/env python3
"""Convert an SVG file (or directory of SVGs) to high-DPI PNG using PyMuPDF.

Also normalizes `_subscript` tokens into `<tspan dy="4" font-size="75%">...</tspan>`
and converts centered `<text>` elements containing `<tspan>` into `text-anchor="start"`
with an estimated centered `x` so PyMuPDF never overlaps centered `<tspan>` runs.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pymupdf


_SUB_RE = re.compile(r"([A-Za-zθΘαβγσ]+)_([A-Za-z0-9]{1,8})\b")


def _inject_svg_tspans(text_body: str) -> str:
    """Replace `X_sub` inside SVG <text> body with <tspan dy="4" font-size="75%">sub</tspan>."""
    # Only replace outside existing tags
    parts = re.split(r"(<[^>]+>)", text_body)
    out: list[str] = []
    for part in parts:
        if part.startswith("<"):
            out.append(part)
        else:
            out.append(
                _SUB_RE.sub(
                    r'\1<tspan dy="4" font-size="75%">\2</tspan><tspan dy="-4">&#8203;</tspan>',
                    part,
                )
            )
    return "".join(out)


def _estimate_svg_text_width(text_body: str, font_size: float) -> float:
    """Estimate rendered width of an SVG <text> body containing <tspan> subscripts."""
    stripped_sub = re.sub(r'<tspan[^>]*font-size="75%"[^>]*>(.*?)</tspan>', "\x00\\1\x00", text_body)
    plain = html.unescape(re.sub(r"<[^>]+>", "", stripped_sub)).replace("\u200b", "")
    width = 0.0
    in_sub = False
    for ch in plain:
        if ch == "\x00":
            in_sub = not in_sub
            continue
        scale = 0.75 if in_sub else 1.0
        if ch in "ilI.,·()| ":
            width += 0.30 * font_size * scale
        elif ch in "MWmw@":
            width += 0.78 * font_size * scale
        else:
            width += 0.54 * font_size * scale
    return width


def preprocess_svg_for_pymupdf(svg_text: str) -> str:
    """Normalize `_sub` to <tspan> and fix centered <text> with <tspan> for PyMuPDF."""
    text_elem_re = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.DOTALL)

    def _rewrite_text(match: re.Match[str]) -> str:
        attrs, body = match.group(1), match.group(2)
        new_body = _inject_svg_tspans(body)
        if "<tspan" in new_body and 'text-anchor="middle"' in attrs:
            x_m = re.search(r'\bx="([\d.]+)"', attrs)
            fs_m = re.search(r'\bfont-size="([\d.]+)"', attrs)
            if x_m:
                cx = float(x_m.group(1))
                fs = float(fs_m.group(1)) if fs_m else 16.0
                est_w = _estimate_svg_text_width(new_body, fs)
                new_x = max(4.0, cx - est_w / 2.0)
                attrs = attrs.replace('text-anchor="middle"', 'text-anchor="start"')
                attrs = re.sub(r'\bx="[\d.]+"', f'x="{new_x:.1f}"', attrs, count=1)
        return f"<text{attrs}>{new_body}</text>"

    return text_elem_re.sub(_rewrite_text, svg_text)


def convert_svg_to_png(svg_path: Path, png_path: Path, dpi: int = 200) -> Path:
    """Render a single SVG file to a PNG file at the given DPI."""
    raw_svg = svg_path.read_text(encoding="utf-8")
    clean_svg = preprocess_svg_for_pymupdf(raw_svg)
    doc = pymupdf.open(stream=clean_svg.encode("utf-8"), filetype="svg")
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(png_path))
    doc.close()
    return png_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert SVG illustration(s) to PNG.")
    parser.add_argument("input", type=Path, help="Input .svg file or directory of .svg files")
    parser.add_argument("output", type=Path, nargs="?", help="Output .png file (for single input)")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    args = parser.parse_args()

    inp = args.input.resolve()
    if inp.is_dir():
        svgs = sorted(inp.glob("*.svg"))
        if not svgs:
            print(f"No .svg files found in {inp}")
            return 1
        for svg in svgs:
            out = svg.with_suffix(".png")
            convert_svg_to_png(svg, out, dpi=args.dpi)
            print(f"Converted {svg.name} -> {out.name}")
        return 0

    out = args.output.resolve() if args.output else inp.with_suffix(".png")
    convert_svg_to_png(inp, out, dpi=args.dpi)
    print(f"Converted {inp} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
