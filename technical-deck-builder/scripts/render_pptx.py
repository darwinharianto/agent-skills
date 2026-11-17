#!/usr/bin/env python3
"""Deterministic python-pptx deck builder with Pydantic schema & density validation."""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from pptx.util import Inches, Pt


# ---------------------------------------------------------------------------
# Theme Constants (Soft Pastel Editorial Theme — Distill / Anthropic Style)
# ---------------------------------------------------------------------------
SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5
FONT_FAMILY = "Arial"

BG_DARK = RGBColor(250, 249, 246)     # #FAF9F6 Warm Alabaster
SURFACE = RGBColor(255, 255, 255)     # #FFFFFF Pure White Card
SURFACE_ALT = RGBColor(241, 245, 249) # #F1F5F9 Soft Slate
BORDER = RGBColor(203, 213, 225)      # #CBD5E1 Subtle Slate Border
TEXT_PRIMARY = RGBColor(30, 41, 59)   # #1E293B Deep Charcoal Ink
TEXT_MUTED = RGBColor(71, 85, 105)    # #475569 Muted Slate Ink
ACCENT_CYAN = RGBColor(2, 132, 199)   # #0284C7 Saturated Blue
ACCENT_EMERALD = RGBColor(22, 163, 74)# #16A34A Saturated Green
ACCENT_AMBER = RGBColor(217, 119, 6)  # #D97706 Saturated Amber
ACCENT_CORAL = RGBColor(225, 29, 72)  # #E11D48 Saturated Rose/Coral


# ---------------------------------------------------------------------------
# Pydantic Schema & Slide Density Rules
# ---------------------------------------------------------------------------
class PaperMetadata(BaseModel):
    title: str
    authors: list[str]
    year: int | None = None
    arxiv_id: str
    url: str = ""


class ColumnBlock(BaseModel):
    heading: str
    points: list[str] = Field(min_length=1, max_length=5)

    @field_validator("points")
    @classmethod
    def check_point_word_count(cls, points: list[str]) -> list[str]:
        for pt_text in points:
            words = pt_text.split()
            if len(words) > 12:
                raise ValueError(
                    f"Comparison point exceeds 12 words ({len(words)} words): '{pt_text}'"
                )
        return points


class MechanismStep(BaseModel):
    label: str
    detail: str

    @field_validator("detail")
    @classmethod
    def check_detail_word_count(cls, val: str) -> str:
        words = val.split()
        if len(words) > 18:
            raise ValueError(
                f"Mechanism step detail exceeds 18 words ({len(words)} words): '{val}'"
            )
        return val


class SlideSpec(BaseModel):
    slide_number: int = Field(ge=1)
    layout: Literal[
        "title",
        "task_domain",
        "overview",
        "comparison",
        "mechanism",
        "figure_takeaway",
        "results",
        "evidence",
        "tradeoffs",
    ]
    title: str
    key_takeaway: str = ""
    bullets: list[str] = Field(default_factory=list, max_length=5)
    left_column: ColumnBlock | None = None
    right_column: ColumnBlock | None = None
    steps: list[MechanismStep] = Field(default_factory=list)
    figure_path: str | None = None
    figure_paths: list[str] = Field(default_factory=list)
    figure_caption: str | None = None
    notation_primer: list[str] = Field(default_factory=list)
    hero_metric: dict | None = None
    closing_takeaway: str | None = None
    highlights: list[dict] = Field(default_factory=list)
    native_table: dict | None = None
    native_flow: list[dict] = Field(default_factory=list)
    native_columns: list[dict] = Field(default_factory=list)
    panels: list[dict] = Field(default_factory=list)
    visual_suggestion: str = ""
    speaker_notes: str = ""

    @field_validator("bullets")
    @classmethod
    def check_bullet_word_count(cls, bullets: list[str]) -> list[str]:
        for bullet in bullets:
            words = bullet.split()
            if len(words) > 12:
                raise ValueError(
                    f"Bullet exceeds 12-word limit ({len(words)} words): '{bullet}'"
                )
        return bullets

    @field_validator("key_takeaway")
    @classmethod
    def check_takeaway_length(cls, val: str) -> str:
        words = val.split()
        if len(words) > 24:
            raise ValueError(
                f"key_takeaway is too long ({len(words)} words, max 24): '{val}'"
            )
        return val

    @model_validator(mode="after")
    def validate_layout_fields(self) -> "SlideSpec":
        if self.layout == "comparison" and (not self.left_column or not self.right_column):
            raise ValueError(
                f"Slide {self.slide_number} ('comparison') requires left_column and right_column."
            )
        if self.layout == "mechanism" and len(self.steps) < 2 and not self.figure_paths and not self.panels:
            raise ValueError(
                f"Slide {self.slide_number} ('mechanism') requires at least 2 steps, figure_paths, or panels."
            )
        if self.layout == "figure_takeaway" and not any([
            self.figure_path, self.figure_paths, self.panels, self.native_table, self.native_flow, self.native_columns
        ]):
            raise ValueError(
                f"Slide {self.slide_number} ('figure_takeaway') requires figure_path, figure_paths, panels, or native_* layout."
            )
        return self


class InsightBrief(BaseModel):
    paper_metadata: PaperMetadata
    task_domain: dict = Field(default_factory=dict)
    paper_overview: dict = Field(default_factory=dict)
    end_to_end_pipeline: dict = Field(default_factory=dict)
    component_deep_dives: list[dict] = Field(default_factory=list)
    results_and_demos: dict = Field(default_factory=dict)
    ablations: dict = Field(default_factory=dict)
    core_bottleneck: dict = Field(default_factory=dict)
    author_motivation_and_insight: dict = Field(default_factory=dict)
    mechanism_of_action: dict = Field(default_factory=dict)
    evidence_and_ablation: dict = Field(default_factory=dict)
    tradeoffs_and_failure_modes: dict = Field(default_factory=dict)
    slides: list[SlideSpec] = Field(min_length=7, max_length=12)


# ---------------------------------------------------------------------------
# Global Unicode Math Normalizer
# ---------------------------------------------------------------------------
_MATH_SUBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"1\s*/\s*sqrt\(\s*d_k\s*\)", re.I), "1/√dₖ"),
    (re.compile(r"sqrt\(\s*d_k\s*\)", re.I), "√dₖ"),
    (re.compile(r"Q\s*K\^T"), "QKᵀ"),
    (re.compile(r"K\^T"), "Kᵀ"),
    (re.compile(r"W\^O"), "Wᴼ"),
    (re.compile(r"O\(\s*n\^2\s*\*?\s*d\s*\)"), "O(n²·d)"),
    (re.compile(r"O\(\s*n\s*\*?\s*d\^2\s*\)"), "O(n·d²)"),
    (re.compile(r"O\(\s*r\s*\*?\s*n\s*\*?\s*d\s*\)"), "O(r·n·d)"),
    (re.compile(r"PE_\{([^}]+)\}"), r"PE(\1)"),
    (re.compile(r"h_\{t-1\}"), "hₜ₋₁"),
    (re.compile(r"\bh_t\b"), "hₜ"),
    (re.compile(r"\bd_k\b"), "dₖ"),
    (re.compile(r"\bd_v\b"), "dᵥ"),
    (re.compile(r"2\s*\*\s*pi\b", re.I), "2π"),
    (re.compile(r"10000\s*\*\s*2π"), "10000·2π"),
    (re.compile(r"\^2\b"), "²"),
]


def normalize_unicode_math(text: str) -> str:
    """Normalize ASCII math expressions into clean Unicode symbols across all slide text."""
    for pattern, repl in _MATH_SUBS:
        text = pattern.sub(repl, text)
    text = re.sub(r"\(-(\d+(?:\.\d+)?)", "(\u2060\u2212\\1", text)
    text = re.sub(r"~(\d)", "\u2248\\1", text)
    return text


def normalize_brief_math(brief: InsightBrief) -> InsightBrief:
    """Apply Unicode math normalization across all slide fields."""
    for slide in brief.slides:
        slide.title = normalize_unicode_math(slide.title)
        slide.key_takeaway = normalize_unicode_math(slide.key_takeaway)
        slide.bullets = [normalize_unicode_math(b) for b in slide.bullets]
        if slide.left_column:
            slide.left_column.heading = normalize_unicode_math(slide.left_column.heading)
            slide.left_column.points = [normalize_unicode_math(p) for p in slide.left_column.points]
        if slide.right_column:
            slide.right_column.heading = normalize_unicode_math(slide.right_column.heading)
            slide.right_column.points = [normalize_unicode_math(p) for p in slide.right_column.points]
        for step in slide.steps:
            step.label = normalize_unicode_math(step.label)
            step.detail = normalize_unicode_math(step.detail)
        if slide.figure_caption:
            slide.figure_caption = normalize_unicode_math(slide.figure_caption)
        slide.notation_primer = [normalize_unicode_math(n) for n in slide.notation_primer]
        if slide.hero_metric:
            slide.hero_metric = {
                k: normalize_unicode_math(str(v)) for k, v in slide.hero_metric.items()
            }
        if slide.closing_takeaway:
            slide.closing_takeaway = normalize_unicode_math(slide.closing_takeaway)
        if slide.speaker_notes:
            slide.speaker_notes = normalize_unicode_math(slide.speaker_notes)
    return brief


# ---------------------------------------------------------------------------
# Typography & Geometry Helpers
# ---------------------------------------------------------------------------
def fit_font_size(
    lines: list[str],
    box_w_in: float,
    box_h_in: float,
    base_pt: int = 15,
    min_pt: int = 10,
) -> int:
    """Compute largest font size (pt) that fits all lines inside the box without overflow."""
    usable_w = max(box_w_in - 0.2, 0.5)
    usable_h = max(box_h_in - 0.15, 0.4)

    for pt in range(base_pt, min_pt - 1, -1):
        char_w_in = (pt * 0.54) / 72.0
        line_h_in = (pt * 1.42) / 72.0
        chars_per_line = max(int(usable_w / char_w_in), 10)
        total_lines = 0
        for line in lines:
            total_lines += max(1, math.ceil(max(len(line), 1) / chars_per_line))
        if total_lines * line_h_in <= usable_h:
            return pt
    return min_pt


def get_image_dimensions(path: Path) -> tuple[int, int]:
    """Read width and height from a PNG or JPEG file header without external image libs."""
    with path.open("rb") as fh:
        header = fh.read(24)
        if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", header[16:24])
            return w, h
        if len(header) >= 2 and header[:2] == b"\xff\xd8":
            fh.seek(2)
            while True:
                marker_bytes = fh.read(2)
                if len(marker_bytes) < 2:
                    break
                while marker_bytes[0] != 0xFF:
                    marker_bytes = marker_bytes[1:] + fh.read(1)
                    if len(marker_bytes) < 2:
                        break
                marker = marker_bytes[1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    data = fh.read(7)
                    if len(data) == 7:
                        h, w = struct.unpack(">HH", data[3:7])
                        return w, h
                    break
                if marker in (0xD8, 0xD9, 0x00) or (0xD0 <= marker <= 0xD7):
                    continue
                seg_len_bytes = fh.read(2)
                if len(seg_len_bytes) < 2:
                    break
                seg_len = struct.unpack(">H", seg_len_bytes)[0]
                fh.seek(max(seg_len - 2, 0), 1)
    return (1600, 900)


def resolve_raster_image(img_path: Path) -> Path:
    """If img_path is an SVG, rasterize it to a sibling 200-DPI PNG; otherwise adapt light PDF figures."""
    if img_path.suffix.lower() != ".svg":
        return adapt_image_for_light_theme(img_path)
    png_path = img_path.with_suffix(".png")
    if not png_path.exists() or img_path.stat().st_mtime > png_path.stat().st_mtime:
        import pymupdf

        doc = pymupdf.open(str(img_path))
        pix = doc[0].get_pixmap(dpi=200, alpha=False)
        pix.save(str(png_path))
        doc.close()
    return png_path


def adapt_image_for_light_theme(img_path: Path) -> Path:
    """Trim outer white margins and make pure-white PDF backgrounds transparent (no inversion)."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return img_path

    img = Image.open(img_path).convert("RGBA")
    w, h = img.size
    corners = [
        img.getpixel((0, 0))[:3],
        img.getpixel((max(w - 1, 0), 0))[:3],
        img.getpixel((0, max(h - 1, 0)))[:3],
        img.getpixel((max(w - 1, 0), max(h - 1, 0)))[:3],
    ]
    avg_corner_luma = sum((r + g + b) / 3.0 for r, g, b in corners) / 4.0
    if avg_corner_luma < 225:
        return img_path

    cache_dir = img_path.parent / ".light_cache"
    cache_path = cache_dir / f"{img_path.stem}_transparent.png"
    if cache_path.exists() and cache_path.stat().st_mtime >= img_path.stat().st_mtime:
        return cache_path

    # 1. Trim outer white margin with a 12px breathing pad
    rgb = img.convert("RGB")
    bg = Image.new("RGB", (w, h), (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    bbox = diff.getbbox()
    if bbox:
        pad = 12
        crop_box = (
            max(bbox[0] - pad, 0),
            max(bbox[1] - pad, 0),
            min(bbox[2] + pad, w),
            min(bbox[3] + pad, h),
        )
        img = img.crop(crop_box)

    # 2. Convert pure-white background pixels (RGB > 245) to transparent alpha=0
    pixels = img.getdata()
    new_pixels = [
        (r, g, b, 0) if (r > 245 and g > 245 and b > 245) else (r, g, b, a)
        for (r, g, b, a) in pixels
    ]
    img.putdata(new_pixels)

    cache_dir.mkdir(parents=True, exist_ok=True)
    img.save(cache_path)
    return cache_path


def add_figure_box(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    img_path: Path,
    caption: str | None = None,
    border_color: RGBColor = BORDER,
    framed: bool = False,
) -> None:
    """Render an aspect-ratio-preserving image directly on canvas (borderless by default)."""
    if framed:
        add_card(slide, x, y, w, h, fill_color=SURFACE_ALT, border_color=border_color)
    if img_path.exists():
        raster_path = resolve_raster_image(img_path)
        img_w, img_h = get_image_dimensions(raster_path)
        pad = 0.14 if framed else 0.0
        avail_w = w - 2 * pad
        avail_h = h - (0.42 if caption else 2 * pad)
        scale = min(avail_w / max(img_w, 1), avail_h / max(img_h, 1))
        draw_w = img_w * scale
        draw_h = img_h * scale
        draw_x = x + (w - draw_w) / 2.0
        draw_y = y + pad + (avail_h - draw_h) / 2.0
        # Lock native aspect ratio by passing only width (python-pptx computes exact height)
        slide.shapes.add_picture(str(raster_path), Inches(draw_x), Inches(draw_y), width=Inches(draw_w))

    if caption:
        add_textbox(
            slide,
            x + 0.14,
            y + h - 0.40,
            w - 0.28,
            0.34,
            caption,
            font_size=10,
            color=TEXT_MUTED,
            align=PP_ALIGN.CENTER,
        )


def set_slide_background(slide, color: RGBColor = BG_DARK) -> None:
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    fill_color: RGBColor = SURFACE,
    border_color: RGBColor = BORDER,
    radius: bool = True,
):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(
        shape_type, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    if radius and len(shape.adjustments) > 0:
        shape.adjustments[0] = 0.04
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.0)
    return shape


def add_accent_bar(
    slide, left: float, top: float, width: float, height: float, color: RGBColor
) -> None:
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()


_RICH_TOKEN_RE = re.compile(
    r"<sub>(?P<sub_html>.*?)</sub>"
    r"|<sup>(?P<sup_html>.*?)</sup>"
    r"|(?P<base>[A-Za-zθΘαβγσ]+)_\{(?P<sub_br>[^}]+)\}"
    r"|(?P<base2>[A-Za-zθΘαβγσ]+)_(?P<sub_plain>[A-Za-z0-9]{1,8})\b"
    r"|(?P<sbase>[A-Za-z0-9\)]+)\^\{(?P<sup_br>[^}]+)\}"
    r"|(?P<sbase2>[A-Za-z0-9\)]+)\^(?P<sup_plain>[A-Za-z0-9]{1,4})\b"
)


def parse_rich_math_segments(text: str) -> list[tuple[str, str]]:
    """Split text into (segment, 'normal'|'sub'|'sup') tuples for native PPTX subscripts/superscripts."""
    segments: list[tuple[str, str]] = []
    pos = 0
    for m in _RICH_TOKEN_RE.finditer(text):
        if m.start() > pos:
            segments.append((text[pos : m.start()], "normal"))
        if m.group("sub_html") is not None:
            segments.append((m.group("sub_html"), "sub"))
        elif m.group("sup_html") is not None:
            segments.append((m.group("sup_html"), "sup"))
        elif m.group("base") is not None:
            segments.append((m.group("base"), "normal"))
            segments.append((m.group("sub_br"), "sub"))
        elif m.group("base2") is not None:
            segments.append((m.group("base2"), "normal"))
            segments.append((m.group("sub_plain"), "sub"))
        elif m.group("sbase") is not None:
            segments.append((m.group("sbase"), "normal"))
            segments.append((m.group("sup_br"), "sup"))
        elif m.group("sbase2") is not None:
            segments.append((m.group("sbase2"), "normal"))
            segments.append((m.group("sup_plain"), "sup"))
        pos = m.end()
    if pos < len(text):
        segments.append((text[pos:], "normal"))
    return segments or [(text, "normal")]


def add_formatted_runs(
    paragraph,
    text: str,
    font_size_pt: int,
    color: RGBColor,
    bold: bool = False,
) -> None:
    """Append runs to a paragraph with native OOXML baseline subscripts and superscripts."""
    for seg_text, kind in parse_rich_math_segments(text):
        run = paragraph.add_run()
        run.text = seg_text
        run.font.name = FONT_FAMILY
        run.font.size = Pt(font_size_pt)
        run.font.bold = bold
        run.font.color.rgb = color
        if kind == "sub":
            run.font._element.set("baseline", "-25000")
        elif kind == "sup":
            run.font._element.set("baseline", "30000")


def format_footer_title(title: str, max_len: int = 60) -> str:
    """Truncate long paper titles cleanly at a colon or word boundary."""
    if len(title) <= max_len:
        return title
    if ":" in title:
        prefix = title[: title.index(":")].strip()
        if 12 <= len(prefix) <= max_len:
            return prefix
    clipped = title[: max_len - 1]
    if " " in clipped:
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(",;:- ") + "…"


def add_textbox(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: int = 15,
    color: RGBColor = TEXT_PRIMARY,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.TOP,
    auto_fit: bool = True,
):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(0.08)
    tf.margin_right = Inches(0.08)
    tf.margin_top = Inches(0.05)
    tf.margin_bottom = Inches(0.05)

    chosen_pt = fit_font_size([text], width, height, base_pt=font_size) if auto_fit else font_size
    p = tf.paragraphs[0]
    p.alignment = align
    add_formatted_runs(p, text, chosen_pt, color, bold=bold)
    return tb


def add_bullet_list(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[str],
    base_pt: int = 15,
    min_pt: int = 11,
    color: RGBColor = TEXT_PRIMARY,
    bullet_prefix: str = "•  ",
) -> None:
    if not items:
        return
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.1)
    tf.margin_right = Inches(0.1)
    tf.margin_top = Inches(0.06)
    tf.margin_bottom = Inches(0.06)

    prefixed = [f"{bullet_prefix}{item}" for item in items]
    chosen_pt = fit_font_size(prefixed, width, height, base_pt=base_pt, min_pt=min_pt)

    for idx, line_text in enumerate(prefixed):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        add_formatted_runs(p, line_text, chosen_pt, color, bold=False)


def add_chrome(
    slide,
    spec: SlideSpec,
    total_slides: int,
    meta: PaperMetadata,
    tag_label: str,
    tag_color: RGBColor = ACCENT_CYAN,
) -> float:
    """Render header pill, assertion slide title, and footer. Returns content top Y."""
    set_slide_background(slide)

    # Category pill
    pill = add_card(slide, 0.35, 0.28, 2.65, 0.30, fill_color=SURFACE_ALT, border_color=tag_color)
    tf = pill.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = tag_label.upper()
    r.font.name = FONT_FAMILY
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = tag_color

    # Assertion Slide Title (22-24pt bold, max 2 lines — replaces separate Key Takeaway banner)
    add_textbox(
        slide,
        left=0.35,
        top=0.64,
        width=12.63,
        height=0.82,
        text=spec.title,
        font_size=23,
        color=TEXT_PRIMARY,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
    )

    # Footer (omit arXiv footer if Slide 2 notation footnote owns the bottom edge)
    footer_y = 6.95 if spec.notation_primer else 7.10
    if not spec.notation_primer:
        footer_text = f"{format_footer_title(meta.title)}  |  arXiv:{meta.arxiv_id}"
        add_textbox(
            slide, 0.35, footer_y, 9.5, 0.28, footer_text, font_size=10, color=TEXT_MUTED, auto_fit=False
        )
    add_textbox(
        slide,
        11.5,
        footer_y,
        1.48,
        0.28,
        f"{spec.slide_number} / {total_slides}",
        font_size=10,
        color=TEXT_MUTED,
        align=PP_ALIGN.RIGHT,
        auto_fit=False,
    )

    if spec.speaker_notes:
        slide.notes_slide.notes_text_frame.text = spec.speaker_notes

    return 1.56


# ---------------------------------------------------------------------------
# Dedicated Layout Renderers
# ---------------------------------------------------------------------------
def render_title_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    set_slide_background(slide)
    add_accent_bar(slide, 0.0, 0.0, 0.18, SLIDE_HEIGHT_IN, ACCENT_CYAN)

    has_fig = bool(spec.figure_path)
    has_highlights = bool(spec.highlights)
    content_w = 7.15 if has_fig else 11.63

    badge = f"FIRST-PRINCIPLES TECHNICAL BRIEF  •  arXiv:{meta.arxiv_id}"
    if meta.year:
        badge += f" ({meta.year})"
    badge_y = 0.58 if has_highlights else 1.05
    add_textbox(slide, 0.85, badge_y, content_w, 0.36, badge, font_size=12, color=ACCENT_CYAN, bold=True)

    title_y = 1.02 if has_highlights else 1.55
    title_h = 1.35 if has_highlights else 1.65
    add_textbox(
        slide,
        left=0.85,
        top=title_y,
        width=content_w,
        height=title_h,
        text=meta.title,
        font_size=32 if has_highlights else (34 if has_fig else 36),
        color=TEXT_PRIMARY,
        bold=True,
    )

    authors_str = ", ".join(meta.authors[:6])
    if len(meta.authors) > 6:
        authors_str += f" + {len(meta.authors) - 6} more"
    authors_y = 2.44 if has_highlights else 3.30
    add_textbox(slide, 0.85, authors_y, content_w, 0.42, authors_str, font_size=14, color=TEXT_MUTED)

    thesis_y = 2.98 if has_highlights else 4.05
    thesis_h = 1.04 if has_highlights else 1.30
    add_card(slide, 0.85, thesis_y, content_w, thesis_h, fill_color=SURFACE, border_color=ACCENT_CYAN)
    add_textbox(
        slide,
        left=1.1,
        top=thesis_y + 0.10,
        width=content_w - 0.5,
        height=thesis_h - 0.20,
        text=spec.key_takeaway or spec.title,
        font_size=16 if has_fig else 17,
        color=TEXT_PRIMARY,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
    )

    if has_highlights:
        cards = spec.highlights[:3]
        gap = 0.24
        card_w = (content_w - gap * (len(cards) - 1)) / len(cards)
        card_y = 4.20
        card_h = 2.48
        color_map = {
            "blue": (RGBColor(224, 242, 254), ACCENT_CYAN, RGBColor(3, 105, 161)),
            "green": (RGBColor(220, 252, 231), ACCENT_EMERALD, RGBColor(21, 128, 61)),
            "purple": (RGBColor(243, 232, 255), RGBColor(147, 51, 234), RGBColor(126, 34, 206)),
            "amber": (RGBColor(254, 243, 199), ACCENT_AMBER, RGBColor(180, 83, 9)),
        }
        for idx, item in enumerate(cards):
            cx = 0.85 + idx * (card_w + gap)
            fill_c, stroke_c, ink_c = color_map.get(
                str(item.get("color", "blue")).lower(),
                color_map["blue"],
            )
            add_card(slide, cx, card_y, card_w, card_h, fill_color=SURFACE, border_color=stroke_c)
            add_accent_bar(slide, cx, card_y, card_w, 0.08, stroke_c)
            # Label pill
            add_card(slide, cx + 0.22, card_y + 0.24, card_w - 0.44, 0.34, fill_color=fill_c, border_color=stroke_c)
            add_textbox(
                slide, cx + 0.24, card_y + 0.25, card_w - 0.48, 0.32,
                str(item.get("label", "")).upper(), font_size=11, color=ink_c, bold=True,
                align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
            )
            add_textbox(
                slide, cx + 0.22, card_y + 0.72, card_w - 0.44, 0.62,
                str(item.get("headline", "")), font_size=21, color=TEXT_PRIMARY, bold=True,
                valign=MSO_ANCHOR.MIDDLE,
            )
            add_textbox(
                slide, cx + 0.22, card_y + 1.40, card_w - 0.44, 0.94,
                str(item.get("detail", "")), font_size=15, color=TEXT_MUTED,
                valign=MSO_ANCHOR.TOP, auto_fit=False,
            )
    elif spec.bullets:
        add_bullet_list(
            slide, 0.85, 5.55, content_w, 1.35, spec.bullets, base_pt=13, color=TEXT_MUTED
        )

    if has_fig:
        img_path = (workspace_dir / spec.figure_path).resolve()
        add_figure_box(
            slide,
            x=8.25,
            y=1.05,
            w=4.43,
            h=5.75,
            img_path=img_path,
            caption=spec.figure_caption,
            border_color=BORDER,
        )

    add_textbox(
        slide,
        11.2,
        7.05,
        1.48,
        0.3,
        f"1 / {total_slides}",
        font_size=10,
        color=TEXT_MUTED,
        align=PP_ALIGN.RIGHT,
        auto_fit=False,
    )
    if spec.speaker_notes:
        slide.notes_slide.notes_text_frame.text = spec.speaker_notes


def _render_native_diagram_panel(
    slide, px: float, py: float, pw: float, ph: float, panel_spec: dict
) -> None:
    """Render an editable grouped box-and-arrow schematic using native python-pptx shapes."""
    ref_w = float(panel_spec.get("ref_w", 600.0))
    ref_h = float(panel_spec.get("ref_h", 520.0))
    sx = pw / ref_w
    sy = ph / ref_h

    grp = slide.shapes.add_group_shape()

    # Outer panel card matching SVG chart border style (#FFFFFF, 1.5pt #CBD5E1)
    outer = grp.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(px), Inches(py), Inches(pw), Inches(ph)
    )
    outer.adjustments[0] = 0.03
    outer.fill.solid()
    outer.fill.fore_color.rgb = SURFACE
    outer.line.color.rgb = BORDER
    outer.line.width = Pt(1.5)

    title_text = panel_spec.get("title", "")
    if title_text:
        tb = grp.shapes.add_textbox(
            Inches(px + 0.14), Inches(py + 0.14), Inches(pw - 0.28), Inches(0.46)
        )
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        add_formatted_runs(p, normalize_unicode_math(str(title_text)), 19, TEXT_PRIMARY, bold=True)

    palette_ext = {
        **_NATIVE_PALETTE,
        "white": (SURFACE, ACCENT_CYAN, TEXT_PRIMARY),
        "gray": (RGBColor(226, 232, 240), RGBColor(148, 163, 184), TEXT_MUTED),
    }

    for node in panel_spec.get("nodes", []):
        nx = px + float(node["x"]) * sx
        ny = py + float(node["y"]) * sy
        nw = float(node["w"]) * sx
        nh = float(node["h"]) * sy
        color_key = str(node.get("color", "blue")).lower()
        fill_c, stroke_c, ink_c = palette_ext.get(color_key, palette_ext["blue"])
        if node.get("border_color"):
            bc_key = str(node["border_color"]).lower()
            _, stroke_c, _ = palette_ext.get(bc_key, (fill_c, stroke_c, ink_c))
        if node.get("text_color"):
            tc_key = str(node["text_color"]).lower()
            _, _, ink_c = palette_ext.get(tc_key, (fill_c, stroke_c, ink_c))

        shp = grp.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(nx), Inches(ny), Inches(nw), Inches(nh)
        )
        shp.adjustments[0] = 0.08
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill_c
        shp.line.color.rgb = stroke_c
        shp.line.width = Pt(float(node.get("border_pt", 1.5)))

        tf = shp.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.06)
        tf.margin_right = Inches(0.06)
        tf.margin_top = Inches(0.04)
        tf.margin_bottom = Inches(0.04)
        valign_str = str(node.get("valign", "middle")).lower()
        tf.vertical_anchor = MSO_ANCHOR.TOP if valign_str == "top" else MSO_ANCHOR.MIDDLE

        align_str = str(node.get("align", "center")).lower()
        p_align = PP_ALIGN.LEFT if align_str == "left" else PP_ALIGN.CENTER
        f_size = int(node.get("font_size", 16))
        is_bold = bool(node.get("bold", True))

        text = str(node.get("text", ""))
        if text:
            p = tf.paragraphs[0]
            p.alignment = p_align
            add_formatted_runs(p, normalize_unicode_math(text), f_size, ink_c, bold=is_bold)

        subtext = node.get("subtext")
        if subtext:
            p2 = tf.add_paragraph()
            p2.alignment = p_align
            p2.space_before = Pt(4)
            sub_size = int(node.get("sub_font_size", max(14, f_size - 1)))
            sub_color = ink_c
            if node.get("sub_color"):
                _, _, sub_color = palette_ext.get(str(node["sub_color"]).lower(), (fill_c, stroke_c, ink_c))
            add_formatted_runs(p2, normalize_unicode_math(str(subtext)), sub_size, sub_color, bold=bool(node.get("sub_bold", False)))

    for conn_spec in panel_spec.get("connectors", []):
        cx1 = px + float(conn_spec["x1"]) * sx
        cy1 = py + float(conn_spec["y1"]) * sy
        cx2 = px + float(conn_spec["x2"]) * sx
        cy2 = py + float(conn_spec["y2"]) * sy
        conn = grp.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT, Inches(cx1), Inches(cy1), Inches(cx2), Inches(cy2)
        )
        conn_color_key = str(conn_spec.get("color", "slate")).lower()
        _, c_stroke, _ = palette_ext.get(conn_color_key, (SURFACE_ALT, TEXT_MUTED, TEXT_MUTED))
        if conn_color_key == "slate":
            c_stroke = TEXT_MUTED
        conn.line.color.rgb = c_stroke
        conn.line.width = Pt(2.0)
        if conn_spec.get("arrow", True):
            ln = conn.line._get_or_add_ln()
            ln.append(parse_xml(f'<a:tailEnd {nsdecls("a")} type="triangle" w="med" len="med"/>'))


def add_visual_slot(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    spec: SlideSpec,
    workspace_dir: Path,
    border_color: RGBColor = BORDER,
) -> None:
    """Render a figure_path, modular figure_paths, or mixed native-diagram + SVG-chart panels."""
    if spec.panels:
        num = len(spec.panels)
        gap = 0.22
        panel_w = (w - gap * (num - 1)) / num
        for idx, panel in enumerate(spec.panels):
            px = x + idx * (panel_w + gap)
            if panel.get("type") == "diagram":
                _render_native_diagram_panel(slide, px, y, panel_w, h, panel)
            elif panel.get("type") == "image" and panel.get("path"):
                img_path = (workspace_dir / panel["path"]).resolve()
                add_figure_box(slide, px, y, panel_w, h, img_path, caption=None, border_color=border_color)
        return

    if spec.figure_paths:
        paths = [(workspace_dir / p).resolve() for p in spec.figure_paths]
        num = len(paths)
        gap = 0.22
        panel_w = (w - gap * (num - 1)) / num
        has_cap = bool(spec.figure_caption)
        box_h = h - (0.34 if has_cap else 0.0)
        for idx, p in enumerate(paths):
            px = x + idx * (panel_w + gap)
            add_figure_box(slide, px, y, panel_w, box_h, p, caption=None, border_color=border_color)
        if has_cap:
            add_textbox(
                slide, x + 0.14, y + h - 0.34, w - 0.28, 0.30,
                spec.figure_caption, font_size=10, color=TEXT_MUTED, align=PP_ALIGN.CENTER,
            )
        return

    if spec.figure_path:
        img_path = (workspace_dir / spec.figure_path).resolve()
        add_figure_box(slide, x, y, w, h, img_path, caption=spec.figure_caption, border_color=border_color)


def get_visual_aspect_ratio(workspace_dir: Path, spec: SlideSpec) -> float | None:
    """Return width/height aspect ratio of the resolved figure(s), or None if absent."""
    if spec.figure_paths or spec.panels:
        return 2.5  # Modular multi-panel grids always use widescreen Top-Down layout
    if not spec.figure_path:
        return None
    img_path = (workspace_dir / spec.figure_path).resolve()
    if not img_path.exists():
        return None
    raster_path = resolve_raster_image(img_path)
    w, h = get_image_dimensions(raster_path)
    return w / max(h, 1)


def _render_horizontal_takeaway_strip(
    slide,
    y: float,
    h: float,
    items: list[str],
    accent: RGBColor,
    bullet_prefix: str = "•  ",
) -> None:
    """Render up to 3 concise takeaways as a horizontal strip with >= 14pt projection font."""
    total_w = 12.03
    add_card(slide, 0.65, y, total_w, h, fill_color=SURFACE, border_color=accent)
    add_accent_bar(slide, 0.65, y, total_w, 0.05, accent)
    if not items:
        return

    capped_items = items[:3]
    num_cols = min(3, len(capped_items))
    col_w = (total_w - 0.36) / num_cols

    for col_idx, item in enumerate(capped_items):
        col_x = 0.80 + col_idx * (col_w + 0.08)
        add_bullet_list(
            slide,
            col_x,
            y + 0.12,
            col_w,
            h - 0.18,
            [item],
            base_pt=15,
            min_pt=14,
            color=TEXT_PRIMARY,
            bullet_prefix=bullet_prefix,
        )


def _render_notation_primer_bar(slide, y: float, items: list[str]) -> float:
    """Render Slide 2's Notation Key as a single-line 11pt muted footnote directly below the visual."""
    joined = "Notation:  " + "  |  ".join(items[:5])
    add_textbox(
        slide, 0.35, 6.95, 11.40, 0.28,
        joined, font_size=11, color=TEXT_MUTED, bold=False, valign=MSO_ANCHOR.MIDDLE, auto_fit=False,
    )
    return 0.28


def _render_closing_banner(slide, y: float, text: str) -> None:
    """Render a high-contrast Paradigm-Shift Closing Banner at the bottom of the final slide."""
    banner_h = 0.68
    banner = add_card(slide, 0.65, y, 12.03, banner_h, fill_color=RGBColor(224, 242, 254), border_color=ACCENT_CYAN)
    banner.line.width = Pt(1.75)
    add_accent_bar(slide, 0.65, y, 0.10, banner_h, ACCENT_CYAN)
    add_textbox(
        slide, 0.88, y + 0.06, 11.65, banner_h - 0.12,
        f"Paradigm Shift: {text}",
        font_size=14, color=RGBColor(3, 105, 161), bold=True, valign=MSO_ANCHOR.MIDDLE,
    )


def render_comparison_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Bottleneck vs. Insight", ACCENT_CYAN)
    ar = get_visual_aspect_ratio(workspace_dir, spec)

    if spec.figure_paths or spec.panels:
        # Ban bottom 3-card strip on dual-panel visual slides; expand visuals to full remaining height
        add_visual_slot(slide, 0.35, top_y, 12.63, 5.42, spec, workspace_dir, border_color=BORDER)
        return

    if (spec.figure_path or spec.figure_paths) and ar is not None and ar >= 1.2:
        # Top-Down Layout: Wide Visual Top (~65% height) + 2-Column Horizontal Strip Bottom
        fig_h = 3.05
        add_visual_slot(slide, 0.65, top_y, 12.03, fig_h, spec, workspace_dir, border_color=BORDER)
        strip_y = top_y + fig_h + 0.14
        strip_h = 6.90 - strip_y
        col_w = 5.90
        add_card(slide, 0.65, strip_y, col_w, strip_h, fill_color=SURFACE, border_color=ACCENT_CORAL)
        add_accent_bar(slide, 0.65, strip_y, col_w, 0.05, ACCENT_CORAL)
        add_bullet_list(
            slide, 0.82, strip_y + 0.10, col_w - 0.34, strip_h - 0.16,
            spec.left_column.points, base_pt=12, color=TEXT_PRIMARY,
        )
        right_x = 0.65 + col_w + 0.23
        add_card(slide, right_x, strip_y, col_w, strip_h, fill_color=SURFACE, border_color=ACCENT_EMERALD)
        add_accent_bar(slide, right_x, strip_y, col_w, 0.05, ACCENT_EMERALD)
        add_bullet_list(
            slide, right_x + 0.17, strip_y + 0.10, col_w - 0.34, strip_h - 0.16,
            spec.right_column.points, base_pt=12, color=TEXT_PRIMARY,
        )
        return

    if spec.figure_path:
        # Portrait / narrow visual: 50/50 side-by-side
        left_w = 6.35
        card_h = 2.18
        gap_y = 0.19

        add_card(slide, 0.65, top_y, left_w, card_h, fill_color=SURFACE, border_color=ACCENT_CORAL)
        add_accent_bar(slide, 0.65, top_y, left_w, 0.06, ACCENT_CORAL)
        add_textbox(
            slide, 0.85, top_y + 0.14, left_w - 0.4, 0.38, spec.left_column.heading,
            font_size=16, color=ACCENT_CORAL, bold=True,
        )
        add_bullet_list(
            slide, 0.85, top_y + 0.56, left_w - 0.4, card_h - 0.68,
            spec.left_column.points, base_pt=13, color=TEXT_PRIMARY,
        )

        bot_y = top_y + card_h + gap_y
        add_card(slide, 0.65, bot_y, left_w, card_h, fill_color=SURFACE, border_color=ACCENT_EMERALD)
        add_accent_bar(slide, 0.65, bot_y, left_w, 0.06, ACCENT_EMERALD)
        add_textbox(
            slide, 0.85, bot_y + 0.14, left_w - 0.4, 0.38, spec.right_column.heading,
            font_size=16, color=ACCENT_EMERALD, bold=True,
        )
        add_bullet_list(
            slide, 0.85, bot_y + 0.56, left_w - 0.4, card_h - 0.68,
            spec.right_column.points, base_pt=13, color=TEXT_PRIMARY,
        )

        img_path = (workspace_dir / spec.figure_path).resolve()
        add_figure_box(
            slide, 7.25, top_y, 5.43, 4.55, img_path, caption=spec.figure_caption, border_color=BORDER
        )
        return

    col_h = 4.55
    col_w = 5.82

    # Left Column: Prior Bottleneck
    add_card(slide, 0.65, top_y, col_w, col_h, fill_color=SURFACE, border_color=ACCENT_CORAL)
    add_accent_bar(slide, 0.65, top_y, col_w, 0.07, ACCENT_CORAL)
    add_textbox(
        slide,
        0.85,
        top_y + 0.18,
        col_w - 0.4,
        0.45,
        spec.left_column.heading,
        font_size=18,
        color=ACCENT_CORAL,
        bold=True,
    )
    add_bullet_list(
        slide,
        0.85,
        top_y + 0.72,
        col_w - 0.4,
        col_h - 0.9,
        spec.left_column.points,
        base_pt=15,
        color=TEXT_PRIMARY,
    )

    # Right Column: New Insight
    right_x = 0.65 + col_w + 0.39
    add_card(slide, right_x, top_y, col_w, col_h, fill_color=SURFACE, border_color=ACCENT_EMERALD)
    add_accent_bar(slide, right_x, top_y, col_w, 0.07, ACCENT_EMERALD)
    add_textbox(
        slide,
        right_x + 0.2,
        top_y + 0.18,
        col_w - 0.4,
        0.45,
        spec.right_column.heading,
        font_size=18,
        color=ACCENT_EMERALD,
        bold=True,
    )
    add_bullet_list(
        slide,
        right_x + 0.2,
        top_y + 0.72,
        col_w - 0.4,
        col_h - 0.9,
        spec.right_column.points,
        base_pt=15,
        color=TEXT_PRIMARY,
    )


def render_mechanism_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Mechanism of Action", ACCENT_CYAN)
    steps = spec.steps[:4]
    num_steps = len(steps)
    ar = get_visual_aspect_ratio(workspace_dir, spec)

    if spec.figure_paths or spec.panels:
        # Ban bottom 3-card strip on dual-panel visual slides; expand visuals to full remaining height
        add_visual_slot(slide, 0.35, top_y, 12.63, 5.42, spec, workspace_dir, border_color=BORDER)
        return

    if (spec.figure_path or spec.figure_paths) and ar is not None and ar >= 1.2:
        # Top-Down Layout: Full-Bleed Wide Visual Top + Causal Chain Step Strip Bottom
        fig_h = 3.92
        add_visual_slot(slide, 0.35, top_y, 12.63, fig_h, spec, workspace_dir, border_color=BORDER)
        strip_y = top_y + fig_h + 0.14
        strip_h = 6.96 - strip_y
        gap = 0.28
        total_w = 12.63
        card_w = (total_w - gap * (num_steps - 1)) / num_steps
        for idx, step in enumerate(steps):
            x = 0.35 + idx * (card_w + gap)
            add_card(slide, x, strip_y, card_w, strip_h, fill_color=SURFACE, border_color=BORDER)
            add_accent_bar(slide, x, strip_y, card_w, 0.05, ACCENT_CYAN)
            add_textbox(
                slide, x + 0.12, strip_y + 0.10, card_w - 0.24, 0.34,
                step.label, font_size=14, color=ACCENT_CYAN, bold=True,
            )
            add_textbox(
                slide, x + 0.12, strip_y + 0.44, card_w - 0.24, strip_h - 0.52,
                step.detail, font_size=13, color=TEXT_PRIMARY,
            )
            # Explicit causal connector arrow between consecutive step cards
            if idx < num_steps - 1:
                add_textbox(
                    slide, x + card_w + 0.01, strip_y + strip_h * 0.32, gap - 0.02, 0.42,
                    "→", font_size=18, color=ACCENT_CYAN, bold=True,
                    align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE, auto_fit=False,
                )
        return

    if spec.figure_path:
        # Stacked causal steps on the left + visual diagram on the right
        left_w = 6.35
        steps_area_h = 3.55 if spec.bullets else 4.55
        step_gap = 0.12
        step_h = (steps_area_h - step_gap * (num_steps - 1)) / num_steps

        for idx, step in enumerate(steps):
            y = top_y + idx * (step_h + step_gap)
            add_card(slide, 0.65, y, left_w, step_h, fill_color=SURFACE, border_color=BORDER)
            add_accent_bar(slide, 0.65, y, 0.07, step_h, ACCENT_CYAN)
            add_textbox(
                slide, 0.85, y + 0.08, left_w - 0.35, 0.34, step.label,
                font_size=14, color=ACCENT_CYAN, bold=True,
            )
            add_textbox(
                slide, 0.85, y + 0.42, left_w - 0.35, step_h - 0.50, step.detail,
                font_size=13, color=TEXT_PRIMARY,
            )

        if spec.bullets:
            bullets_y = top_y + steps_area_h + 0.14
            bullets_h = 6.80 - bullets_y
            add_card(slide, 0.65, bullets_y, left_w, bullets_h, fill_color=SURFACE_ALT, border_color=BORDER)
            add_bullet_list(
                slide, 0.8, bullets_y + 0.06, left_w - 0.3, bullets_h - 0.12, spec.bullets[:2], base_pt=12
            )

        img_path = (workspace_dir / spec.figure_path).resolve()
        add_figure_box(
            slide, 7.25, top_y, 5.43, 4.55, img_path, caption=spec.figure_caption, border_color=BORDER
        )
        return

    gap = 0.22
    total_w = 12.03
    card_w = (total_w - gap * (num_steps - 1)) / num_steps
    card_h = 2.65 if spec.bullets else 4.45

    for idx, step in enumerate(steps):
        x = 0.65 + idx * (card_w + gap)
        add_card(slide, x, top_y, card_w, card_h, fill_color=SURFACE, border_color=BORDER)
        add_accent_bar(slide, x, top_y, card_w, 0.06, ACCENT_CYAN)
        add_textbox(
            slide,
            x + 0.15,
            top_y + 0.18,
            card_w - 0.3,
            0.55,
            step.label,
            font_size=15,
            color=ACCENT_CYAN,
            bold=True,
        )
        add_textbox(
            slide,
            x + 0.15,
            top_y + 0.78,
            card_w - 0.3,
            card_h - 0.95,
            step.detail,
            font_size=14,
            color=TEXT_PRIMARY,
        )

    if spec.bullets:
        bullets_y = top_y + card_h + 0.22
        bullets_h = 6.85 - bullets_y
        add_card(slide, 0.65, bullets_y, total_w, bullets_h, fill_color=SURFACE_ALT, border_color=BORDER)
        add_bullet_list(
            slide, 0.85, bullets_y + 0.1, total_w - 0.4, bullets_h - 0.2, spec.bullets, base_pt=14
        )


_NATIVE_PALETTE = {
    "blue": (RGBColor(224, 242, 254), ACCENT_CYAN, RGBColor(3, 105, 161)),
    "green": (RGBColor(220, 252, 231), ACCENT_EMERALD, RGBColor(21, 128, 61)),
    "rose": (RGBColor(255, 228, 230), ACCENT_CORAL, RGBColor(190, 18, 60)),
    "amber": (RGBColor(254, 243, 199), ACCENT_AMBER, RGBColor(180, 83, 9)),
    "purple": (RGBColor(243, 232, 255), RGBColor(147, 51, 234), RGBColor(126, 34, 206)),
    "slate": (SURFACE_ALT, BORDER, TEXT_PRIMARY),
}


def _render_native_table(slide, x: float, y: float, w: float, h: float, table_spec: dict) -> None:
    """Render an editable native PowerPoint table with Soft Pastel Editorial styling."""
    headers = table_spec.get("headers", [])
    rows = table_spec.get("rows", [])
    highlight_last = bool(table_spec.get("highlight_last_row", True))
    if not headers or not rows:
        return

    n_rows = 1 + len(rows)
    n_cols = len(headers)
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(w), Inches(h))
    tbl = shape.table
    col_w = int(Inches(w) / n_cols)
    for c in range(n_cols):
        tbl.columns[c].width = col_w

    def _style_cell(cell, text: str, fill: RGBColor, fg: RGBColor, bold: bool = False, size: int = 15):
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.clear()
        add_formatted_runs(p, normalize_unicode_math(str(text)), size, fg, bold=bold)

    for c_idx, h_text in enumerate(headers):
        _style_cell(tbl.cell(0, c_idx), h_text, SURFACE_ALT, TEXT_PRIMARY, bold=True, size=16)

    for r_idx, row in enumerate(rows):
        is_last = highlight_last and (r_idx == len(rows) - 1)
        row_fill = RGBColor(224, 242, 254) if is_last else (SURFACE if r_idx % 2 == 0 else BG_DARK)
        row_fg = RGBColor(3, 105, 161) if is_last else TEXT_PRIMARY
        for c_idx in range(n_cols):
            val = row[c_idx] if c_idx < len(row) else ""
            cell_fg = row_fg
            if "✗" in str(val):
                cell_fg = RGBColor(190, 18, 60)
            elif "✓" in str(val):
                cell_fg = RGBColor(21, 128, 61)
            _style_cell(tbl.cell(r_idx + 1, c_idx), val, row_fill, cell_fg, bold=is_last or ("✓" in str(val)) or ("✗" in str(val)), size=15)


def _render_native_flow(slide, x: float, y: float, w: float, h: float, stages: list[dict]) -> None:
    """Render a compact horizontal linear multi-stage process flow (~55% slide height) with 1-line definitions."""
    n = len(stages)
    if n == 0:
        return
    compact_h = min(h, 4.15)
    flow_y = y + max(0.0, (h - compact_h) / 2.0)
    arrow_gap = 0.34
    card_w = (w - arrow_gap * (n - 1)) / n

    for idx, st in enumerate(stages):
        cx = x + idx * (card_w + arrow_gap)
        fill_c, stroke_c, ink_c = _NATIVE_PALETTE.get(
            str(st.get("color", "blue")).lower(), _NATIVE_PALETTE["blue"]
        )
        add_card(slide, cx, flow_y, card_w, compact_h, fill_color=fill_c, border_color=stroke_c)
        add_accent_bar(slide, cx, flow_y, card_w, 0.08, stroke_c)
        add_textbox(
            slide, cx + 0.12, flow_y + 0.18, card_w - 0.24, 0.48,
            str(st.get("title", "")), font_size=17, color=ink_c, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
        )
        items = st.get("items", [])
        has_cap = bool(st.get("caption"))
        body_bottom = compact_h - (0.72 if has_cap else 0.18)
        if items:
            sub_gap = 0.14
            sub_top = flow_y + 0.78
            sub_h = min(1.05, (body_bottom - 0.78 - sub_gap * (len(items) - 1)) / max(1, len(items)))
            for j, item_text in enumerate(items):
                sy = sub_top + j * (sub_h + sub_gap)
                add_card(slide, cx + 0.16, sy, card_w - 0.32, sub_h, fill_color=SURFACE, border_color=stroke_c)
                add_textbox(
                    slide, cx + 0.22, sy + 0.04, card_w - 0.44, sub_h - 0.08,
                    str(item_text), font_size=15, color=TEXT_PRIMARY, bold=True,
                    align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
                )
        if has_cap:
            add_textbox(
                slide, cx + 0.14, flow_y + compact_h - 0.70, card_w - 0.28, 0.58,
                str(st["caption"]), font_size=14, color=ink_c, bold=True,
                align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
            )
        if idx < n - 1:
            add_textbox(
                slide, cx + card_w + 0.01, flow_y + compact_h * 0.44, arrow_gap - 0.02, 0.5,
                "→", font_size=22, color=TEXT_MUTED, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE, auto_fit=False,
            )


def _render_native_columns(slide, x: float, y: float, w: float, h: float, columns: list[dict]) -> None:
    """Render a 2-column native PPTX card matrix (e.g. Limitations vs. Open Directions)."""
    n = len(columns)
    if n == 0:
        return
    gap = 0.34
    col_w = (w - gap * (n - 1)) / n

    for idx, col in enumerate(columns):
        cx = x + idx * (col_w + gap)
        fill_c, stroke_c, ink_c = _NATIVE_PALETTE.get(
            str(col.get("color", "blue")).lower(), _NATIVE_PALETTE["blue"]
        )
        add_card(slide, cx, y, col_w, h, fill_color=fill_c, border_color=stroke_c)
        add_accent_bar(slide, cx, y, col_w, 0.08, stroke_c)
        add_textbox(
            slide, cx + 0.22, y + 0.20, col_w - 0.44, 0.48,
            str(col.get("heading", "")), font_size=19, color=ink_c, bold=True, align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
        )
        cards = col.get("cards", [])
        if cards:
            c_gap = 0.22
            c_top = y + 0.84
            c_h = (h - 1.04 - c_gap * (len(cards) - 1)) / len(cards)
            for j, c_item in enumerate(cards):
                cy = c_top + j * (c_h + c_gap)
                add_card(slide, cx + 0.24, cy, col_w - 0.48, c_h, fill_color=SURFACE, border_color=stroke_c)
                add_textbox(
                    slide, cx + 0.38, cy + 0.16, col_w - 0.76, 0.44,
                    str(c_item.get("title", "")), font_size=16, color=TEXT_PRIMARY, bold=True, valign=MSO_ANCHOR.MIDDLE,
                )
                add_textbox(
                    slide, cx + 0.38, cy + 0.64, col_w - 0.76, c_h - 0.78,
                    str(c_item.get("detail", "")), font_size=14, color=TEXT_MUTED, valign=MSO_ANCHOR.TOP,
                )


def render_figure_takeaway_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Architecture & Visual", ACCENT_CYAN)

    if spec.native_table or spec.native_flow or spec.native_columns:
        has_bullets = bool(spec.bullets)
        vis_h = 4.25 if has_bullets else 5.36
        if spec.native_table:
            _render_native_table(slide, 0.35, top_y, 12.63, vis_h, spec.native_table)
        elif spec.native_flow:
            _render_native_flow(slide, 0.35, top_y, 12.63, vis_h, spec.native_flow)
        elif spec.native_columns:
            _render_native_columns(slide, 0.35, top_y, 12.63, vis_h, spec.native_columns)
        if has_bullets:
            strip_y = top_y + vis_h + 0.14
            _render_horizontal_takeaway_strip(
                slide, strip_y, 6.96 - strip_y, spec.bullets, ACCENT_CYAN, bullet_prefix="•  "
            )
        return

    ar = get_visual_aspect_ratio(workspace_dir, spec)

    if ar is not None and ar >= 1.2:
        if not spec.bullets:
            add_visual_slot(slide, 0.35, top_y, 12.63, 5.36, spec, workspace_dir, border_color=BORDER)
            return
        fig_h = 4.20
        add_visual_slot(slide, 0.35, top_y, 12.63, fig_h, spec, workspace_dir, border_color=BORDER)
        strip_y = top_y + fig_h + 0.14
        _render_horizontal_takeaway_strip(
            slide, strip_y, 6.96 - strip_y, spec.bullets, ACCENT_CYAN, bullet_prefix="•  "
        )
        return

    img_path = (workspace_dir / spec.figure_path).resolve()

    fig_box_x = 0.65
    fig_box_y = top_y
    fig_box_w = 6.35
    fig_box_h = 4.55

    add_figure_box(
        slide, fig_box_x, fig_box_y, fig_box_w, fig_box_h, img_path, caption=spec.figure_caption
    )

    # Right column: Key analytical bullets
    right_x = fig_box_x + fig_box_w + 0.33
    right_w = 12.68 - right_x
    add_card(slide, right_x, top_y, right_w, fig_box_h, fill_color=SURFACE, border_color=BORDER)
    add_textbox(
        slide,
        right_x + 0.2,
        top_y + 0.18,
        right_w - 0.4,
        0.4,
        "Engineering Takeaways",
        font_size=16,
        color=ACCENT_CYAN,
        bold=True,
    )
    add_bullet_list(
        slide,
        right_x + 0.2,
        top_y + 0.68,
        right_w - 0.4,
        fig_box_h - 0.85,
        spec.bullets,
        base_pt=14,
    )


def render_evidence_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    _render_visual_or_full_card(
        slide, spec, total_slides, meta, workspace_dir,
        tag_label="Evidence & Ablations",
        card_heading="Causal Proof from Ablations",
        accent=ACCENT_EMERALD,
        bullet_prefix="✓  ",
        figure_on_left=True,
    )


def render_tradeoffs_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    _render_visual_or_full_card(
        slide, spec, total_slides, meta, workspace_dir,
        tag_label="Trade-offs & Future Work",
        card_heading="Limitations & Open Directions",
        accent=ACCENT_AMBER,
        bullet_prefix="•  ",
        figure_on_left=False,
    )


def _render_visual_or_full_card(
    slide,
    spec: SlideSpec,
    total_slides: int,
    meta: PaperMetadata,
    workspace_dir: Path,
    tag_label: str,
    card_heading: str,
    accent: RGBColor,
    bullet_prefix: str = "•  ",
    figure_on_left: bool = False,
) -> None:
    """Shared renderer for aspect-ratio-aware visual-split, native grids, or full-width slides."""
    top_y = add_chrome(slide, spec, total_slides, meta, tag_label, accent)
    card_h = 5.26
    has_primer = bool(spec.notation_primer)
    has_closing = bool(spec.closing_takeaway)

    if spec.native_table or spec.native_flow or spec.native_columns:
        if not spec.bullets and not has_closing:
            vis_h = 5.36
        elif not spec.bullets and has_closing:
            vis_h = 4.44
        else:
            vis_h = 3.65 if has_closing else 4.20

        if spec.native_table:
            _render_native_table(slide, 0.35, top_y, 12.63, vis_h, spec.native_table)
        elif spec.native_flow:
            _render_native_flow(slide, 0.35, top_y, 12.63, vis_h, spec.native_flow)
        elif spec.native_columns:
            _render_native_columns(slide, 0.35, top_y, 12.63, vis_h, spec.native_columns)

        if has_primer:
            _render_notation_primer_bar(slide, 7.10, spec.notation_primer)
        cur_y = top_y + vis_h + 0.16
        bottom_limit = 6.12 if has_closing else 6.96
        if spec.bullets:
            _render_horizontal_takeaway_strip(
                slide, cur_y, bottom_limit - cur_y, spec.bullets, accent, bullet_prefix=bullet_prefix
            )
        if has_closing:
            _render_closing_banner(slide, 6.20, spec.closing_takeaway)
        return

    if spec.figure_path or spec.figure_paths or spec.panels:
        ar = get_visual_aspect_ratio(workspace_dir, spec)
        if ar is not None and ar >= 1.2:
            # Top-Down Layout: Full-Bleed Borderless Visual
            if not spec.bullets and not has_closing:
                fig_h = 5.36
                add_visual_slot(slide, 0.35, top_y, 12.63, fig_h, spec, workspace_dir, border_color=accent)
                if has_primer:
                    _render_notation_primer_bar(slide, 7.10, spec.notation_primer)
                return

            fig_h = 4.44 if (not spec.bullets and has_closing) else (3.65 if has_closing else 4.20)
            add_visual_slot(slide, 0.35, top_y, 12.63, fig_h, spec, workspace_dir, border_color=accent)
            if has_primer:
                _render_notation_primer_bar(slide, 7.10, spec.notation_primer)

            cur_y = top_y + fig_h + 0.16
            bottom_limit = 6.12 if has_closing else 6.96
            if spec.bullets:
                _render_horizontal_takeaway_strip(
                    slide, cur_y, bottom_limit - cur_y, spec.bullets, accent, bullet_prefix=bullet_prefix
                )
            if has_closing:
                _render_closing_banner(slide, 6.20, spec.closing_takeaway)
            return

        img_path = (workspace_dir / spec.figure_path).resolve()

        # Portrait / narrow visual: 50/50 side-by-side
        if figure_on_left:
            fig_x, card_x = 0.65, 6.80
            fig_w, card_w = 5.90, 5.88
        else:
            card_x, fig_x = 0.65, 6.78
            card_w, fig_w = 5.88, 5.90

        add_figure_box(slide, fig_x, top_y, fig_w, card_h, img_path, caption=spec.figure_caption, border_color=accent)
        add_card(slide, card_x, top_y, card_w, card_h, fill_color=SURFACE, border_color=accent)
        add_accent_bar(slide, card_x, top_y, card_w, 0.07, accent)
        add_textbox(
            slide, card_x + 0.2, top_y + 0.2, card_w - 0.4, 0.42,
            card_heading, font_size=17, color=accent, bold=True,
        )
        add_bullet_list(
            slide, card_x + 0.2, top_y + 0.72, card_w - 0.4, card_h - 0.9,
            spec.bullets, base_pt=14, bullet_prefix=bullet_prefix,
        )
        return

    add_card(slide, 0.65, top_y, 12.03, card_h, fill_color=SURFACE, border_color=accent)
    add_accent_bar(slide, 0.65, top_y, 12.03, 0.07, accent)
    add_textbox(slide, 0.9, top_y + 0.22, 11.5, 0.42, card_heading, font_size=18, color=accent, bold=True)
    add_bullet_list(
        slide, 0.9, top_y + 0.78, 11.5, card_h - 0.95,
        spec.bullets, base_pt=16, bullet_prefix=bullet_prefix,
    )


def render_task_domain_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    _render_visual_or_full_card(
        slide, spec, total_slides, meta, workspace_dir,
        tag_label="Task Domain & Example",
        card_heading="Problem Domain & Concrete Example",
        accent=ACCENT_CYAN,
        bullet_prefix="▸  ",
        figure_on_left=False,
    )


def render_overview_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    if spec.left_column and spec.right_column:
        render_comparison_slide(slide, spec, total_slides, meta, workspace_dir)
        return
    _render_visual_or_full_card(
        slide, spec, total_slides, meta, workspace_dir,
        tag_label="Paper Overview",
        card_heading="Problem, Solution & Contributions",
        accent=ACCENT_CYAN,
        bullet_prefix="•  ",
        figure_on_left=False,
    )


def render_results_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    if spec.hero_metric and (spec.figure_path or spec.figure_paths):
        top_y = add_chrome(slide, spec, total_slides, meta, "Results & Demos", ACCENT_EMERALD)
        # Compact top-right corner badge (16pt bold) so chart spans 100% of content width
        val_str = str(spec.hero_metric.get("value", ""))
        sub_badge = spec.hero_metric.get("delta") or spec.hero_metric.get("baseline") or ""
        badge_text = f"HEADLINE: {val_str}" + (f"  ({sub_badge})" if sub_badge else "")
        badge_w = 7.40
        badge_x = 12.98 - badge_w
        badge_card = add_card(
            slide, badge_x, 0.18, badge_w, 0.44,
            fill_color=RGBColor(220, 252, 231), border_color=ACCENT_EMERALD,
        )
        badge_card.line.width = Pt(1.5)
        add_textbox(
            slide, badge_x + 0.10, 0.20, badge_w - 0.20, 0.40,
            badge_text, font_size=16, color=RGBColor(21, 128, 61), bold=True,
            align=PP_ALIGN.CENTER, valign=MSO_ANCHOR.MIDDLE,
        )

        # Full-width (100%) chart
        fig_h = 4.20 if spec.bullets else 5.42
        add_visual_slot(slide, 0.35, top_y, 12.63, fig_h, spec, workspace_dir, border_color=ACCENT_EMERALD)

        if spec.bullets:
            strip_y = top_y + fig_h + 0.14
            _render_horizontal_takeaway_strip(
                slide, strip_y, 6.96 - strip_y, spec.bullets, ACCENT_EMERALD, bullet_prefix="★  "
            )
        return

    _render_visual_or_full_card(
        slide, spec, total_slides, meta, workspace_dir,
        tag_label="Results & Demos",
        card_heading="Benchmarks & Qualitative Demos",
        accent=ACCENT_EMERALD,
        bullet_prefix="★  ",
        figure_on_left=True,
    )


# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def load_and_validate(input_path: Path, workspace_dir: Path) -> InsightBrief:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    brief = InsightBrief.model_validate(raw)

    for slide in brief.slides:
        for rel_path in ([slide.figure_path] if slide.figure_path else []) + slide.figure_paths:
            fig_file = (workspace_dir / rel_path).resolve()
            if not fig_file.exists():
                raise FileNotFoundError(
                    f"Slide {slide.slide_number} references missing figure: {fig_file}"
                )
    return normalize_brief_math(brief)


def build_deck(brief: InsightBrief, output_path: Path, workspace_dir: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_WIDTH_IN)
    prs.slide_height = Inches(SLIDE_HEIGHT_IN)
    blank_layout = prs.slide_layouts[6]

    total = len(brief.slides)
    meta = brief.paper_metadata

    for spec in brief.slides:
        slide = prs.slides.add_slide(blank_layout)
        if spec.layout == "title":
            render_title_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "task_domain":
            render_task_domain_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "overview":
            render_overview_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "comparison":
            render_comparison_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "mechanism":
            render_mechanism_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "figure_takeaway":
            render_figure_takeaway_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "results":
            render_results_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "evidence":
            render_evidence_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "tradeoffs":
            render_tradeoffs_slide(slide, spec, total, meta, workspace_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))


def parse_args() -> argparse.Namespace:
    default_ws = Path.cwd() / "workspace"
    parser = argparse.ArgumentParser(description="Validate insight_brief.json and render PPTX.")
    parser.add_argument(
        "--input",
        type=Path,
        default=default_ws / "insight_brief.json",
        help="Path to insight_brief.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_ws / "output_deck.pptx",
        help="Output .pptx path",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=default_ws,
        help="Workspace directory containing figures/",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate insight_brief.json against schema and density rules without rendering.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace_dir = args.workspace.resolve()

    try:
        brief = load_and_validate(args.input.resolve(), workspace_dir)
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(brief.slides)} slides for '{brief.paper_metadata.title}'.")
    if args.validate_only:
        return 0

    build_deck(brief, args.output.resolve(), workspace_dir)
    print(f"Rendered presentation: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
