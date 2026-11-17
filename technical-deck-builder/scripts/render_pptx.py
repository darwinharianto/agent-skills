#!/usr/bin/env python3
"""Deterministic python-pptx deck builder with Pydantic schema & density validation."""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


# ---------------------------------------------------------------------------
# Theme Constants (Modern Dark-Slate Technical Theme)
# ---------------------------------------------------------------------------
SLIDE_WIDTH_IN = 13.333
SLIDE_HEIGHT_IN = 7.5
FONT_FAMILY = "Arial"

BG_DARK = RGBColor(15, 23, 42)        # #0F172A
SURFACE = RGBColor(30, 41, 59)        # #1E293B
SURFACE_ALT = RGBColor(23, 33, 52)    # #172134
BORDER = RGBColor(51, 65, 85)         # #334155
TEXT_PRIMARY = RGBColor(248, 250, 252)  # #F8FAFC
TEXT_MUTED = RGBColor(148, 163, 184)    # #94A3B8
ACCENT_CYAN = RGBColor(56, 189, 248)    # #38BDF8
ACCENT_EMERALD = RGBColor(16, 185, 129) # #10B981
ACCENT_AMBER = RGBColor(245, 158, 11)   # #F59E0B
ACCENT_CORAL = RGBColor(244, 63, 94)    # #F43F5E


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
        "comparison",
        "mechanism",
        "figure_takeaway",
        "evidence",
        "tradeoffs",
    ]
    title: str
    key_takeaway: str
    bullets: list[str] = Field(default_factory=list, max_length=5)
    left_column: ColumnBlock | None = None
    right_column: ColumnBlock | None = None
    steps: list[MechanismStep] = Field(default_factory=list)
    figure_path: str | None = None
    figure_caption: str | None = None
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
        if self.layout == "mechanism" and len(self.steps) < 2:
            raise ValueError(
                f"Slide {self.slide_number} ('mechanism') requires at least 2 steps."
            )
        if self.layout == "figure_takeaway" and not self.figure_path:
            raise ValueError(
                f"Slide {self.slide_number} ('figure_takeaway') requires figure_path."
            )
        return self


class InsightBrief(BaseModel):
    paper_metadata: PaperMetadata
    core_bottleneck: dict
    author_motivation_and_insight: dict
    mechanism_of_action: dict
    evidence_and_ablation: dict
    tradeoffs_and_failure_modes: dict
    slides: list[SlideSpec] = Field(min_length=7, max_length=9)


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


def get_png_dimensions(path: Path) -> tuple[int, int]:
    """Read width and height from a PNG file header without external image libs."""
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", header[16:24])
        return w, h
    return (1600, 900)


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
    run = p.add_run()
    run.text = text
    run.font.name = FONT_FAMILY
    run.font.size = Pt(chosen_pt)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb


def add_bullet_list(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    items: list[str],
    base_pt: int = 15,
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
    chosen_pt = fit_font_size(prefixed, width, height, base_pt=base_pt, min_pt=11)

    for idx, line_text in enumerate(prefixed):
        p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        run = p.add_run()
        run.text = line_text
        run.font.name = FONT_FAMILY
        run.font.size = Pt(chosen_pt)
        run.font.color.rgb = color


def add_chrome(
    slide,
    spec: SlideSpec,
    total_slides: int,
    meta: PaperMetadata,
    tag_label: str,
    tag_color: RGBColor = ACCENT_CYAN,
) -> float:
    """Render consistent header, takeaway banner, and footer. Returns content top Y."""
    set_slide_background(slide)

    # Category pill
    pill = add_card(slide, 0.65, 0.35, 2.2, 0.32, fill_color=SURFACE_ALT, border_color=tag_color)
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

    # Slide title
    add_textbox(
        slide,
        left=0.65,
        top=0.72,
        width=12.0,
        height=0.62,
        text=spec.title,
        font_size=26,
        color=TEXT_PRIMARY,
        bold=True,
    )

    # Key takeaway banner
    add_card(slide, 0.65, 1.38, 12.03, 0.68, fill_color=SURFACE, border_color=BORDER)
    add_accent_bar(slide, 0.65, 1.38, 0.08, 0.68, tag_color)
    add_textbox(
        slide,
        left=0.85,
        top=1.42,
        width=11.7,
        height=0.60,
        text=f"Key Takeaway: {spec.key_takeaway}",
        font_size=14,
        color=ACCENT_CYAN if tag_color != ACCENT_AMBER else ACCENT_AMBER,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
    )

    # Footer
    footer_text = f"{meta.title[:65]}  |  arXiv:{meta.arxiv_id}"
    add_textbox(
        slide, 0.65, 7.05, 9.5, 0.3, footer_text, font_size=10, color=TEXT_MUTED, auto_fit=False
    )
    add_textbox(
        slide,
        11.2,
        7.05,
        1.48,
        0.3,
        f"{spec.slide_number} / {total_slides}",
        font_size=10,
        color=TEXT_MUTED,
        align=PP_ALIGN.RIGHT,
        auto_fit=False,
    )

    if spec.speaker_notes:
        slide.notes_slide.notes_text_frame.text = spec.speaker_notes

    return 2.25


# ---------------------------------------------------------------------------
# Dedicated Layout Renderers
# ---------------------------------------------------------------------------
def render_title_slide(slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata) -> None:
    set_slide_background(slide)
    add_accent_bar(slide, 0.0, 0.0, 0.18, SLIDE_HEIGHT_IN, ACCENT_CYAN)

    badge = f"FIRST-PRINCIPLES TECHNICAL BRIEF  •  arXiv:{meta.arxiv_id}"
    if meta.year:
        badge += f" ({meta.year})"
    add_textbox(slide, 0.9, 1.15, 11.5, 0.4, badge, font_size=12, color=ACCENT_CYAN, bold=True)

    add_textbox(
        slide,
        left=0.9,
        top=1.65,
        width=11.5,
        height=1.65,
        text=meta.title,
        font_size=36,
        color=TEXT_PRIMARY,
        bold=True,
    )

    authors_str = ", ".join(meta.authors[:6])
    if len(meta.authors) > 6:
        authors_str += f" + {len(meta.authors) - 6} more"
    add_textbox(slide, 0.9, 3.4, 11.5, 0.5, authors_str, font_size=14, color=TEXT_MUTED)

    add_card(slide, 0.9, 4.15, 11.5, 1.3, fill_color=SURFACE, border_color=ACCENT_CYAN)
    add_textbox(
        slide,
        left=1.15,
        top=4.3,
        width=11.0,
        height=1.0,
        text=spec.key_takeaway,
        font_size=18,
        color=TEXT_PRIMARY,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
    )

    if spec.bullets:
        add_bullet_list(
            slide, 0.9, 5.65, 11.5, 1.25, spec.bullets, base_pt=13, color=TEXT_MUTED
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


def render_comparison_slide(slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Bottleneck vs. Insight", ACCENT_CYAN)
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


def render_mechanism_slide(slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Mechanism of Action", ACCENT_CYAN)
    steps = spec.steps[:4]
    num_steps = len(steps)
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


def render_figure_takeaway_slide(
    slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata, workspace_dir: Path
) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Architecture & Visual", ACCENT_CYAN)
    fig_box_x = 0.65
    fig_box_y = top_y
    fig_box_w = 6.95
    fig_box_h = 4.55

    add_card(slide, fig_box_x, fig_box_y, fig_box_w, fig_box_h, fill_color=SURFACE_ALT, border_color=BORDER)

    img_path = (workspace_dir / spec.figure_path).resolve()
    if img_path.exists():
        img_w, img_h = get_png_dimensions(img_path)
        pad = 0.18
        avail_w = fig_box_w - 2 * pad
        avail_h = fig_box_h - (0.55 if spec.figure_caption else 2 * pad)
        scale = min(avail_w / max(img_w, 1), avail_h / max(img_h, 1))
        draw_w = img_w * scale
        draw_h = img_h * scale
        draw_x = fig_box_x + (fig_box_w - draw_w) / 2.0
        draw_y = fig_box_y + pad + (avail_h - draw_h) / 2.0
        slide.shapes.add_picture(str(img_path), Inches(draw_x), Inches(draw_y), Inches(draw_w), Inches(draw_h))

    if spec.figure_caption:
        add_textbox(
            slide,
            fig_box_x + 0.15,
            fig_box_y + fig_box_h - 0.42,
            fig_box_w - 0.3,
            0.35,
            spec.figure_caption,
            font_size=10,
            color=TEXT_MUTED,
            align=PP_ALIGN.CENTER,
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


def render_evidence_slide(slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Evidence & Ablations", ACCENT_EMERALD)
    card_h = 4.55
    add_card(slide, 0.65, top_y, 12.03, card_h, fill_color=SURFACE, border_color=ACCENT_EMERALD)
    add_accent_bar(slide, 0.65, top_y, 12.03, 0.07, ACCENT_EMERALD)
    add_textbox(
        slide,
        0.9,
        top_y + 0.22,
        11.5,
        0.42,
        "Causal Proof from Ablations & Experiments",
        font_size=18,
        color=ACCENT_EMERALD,
        bold=True,
    )
    add_bullet_list(
        slide,
        0.9,
        top_y + 0.78,
        11.5,
        card_h - 0.95,
        spec.bullets,
        base_pt=16,
        bullet_prefix="✓  ",
    )


def render_tradeoffs_slide(slide, spec: SlideSpec, total_slides: int, meta: PaperMetadata) -> None:
    top_y = add_chrome(slide, spec, total_slides, meta, "Trade-offs & Failure Modes", ACCENT_AMBER)
    card_h = 4.55
    add_card(slide, 0.65, top_y, 12.03, card_h, fill_color=SURFACE, border_color=ACCENT_AMBER)
    add_accent_bar(slide, 0.65, top_y, 12.03, 0.07, ACCENT_AMBER)
    add_textbox(
        slide,
        0.9,
        top_y + 0.22,
        11.5,
        0.42,
        "Assumptions, Costs & Where It Breaks",
        font_size=18,
        color=ACCENT_AMBER,
        bold=True,
    )
    add_bullet_list(
        slide,
        0.9,
        top_y + 0.78,
        11.5,
        card_h - 0.95,
        spec.bullets,
        base_pt=16,
        bullet_prefix="⚠  ",
    )


# ---------------------------------------------------------------------------
# Main Entrypoint
# ---------------------------------------------------------------------------
def load_and_validate(input_path: Path, workspace_dir: Path) -> InsightBrief:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    brief = InsightBrief.model_validate(raw)

    for slide in brief.slides:
        if slide.figure_path:
            fig_file = (workspace_dir / slide.figure_path).resolve()
            if not fig_file.exists():
                raise FileNotFoundError(
                    f"Slide {slide.slide_number} references missing figure: {fig_file}"
                )
    return brief


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
            render_title_slide(slide, spec, total, meta)
        elif spec.layout == "comparison":
            render_comparison_slide(slide, spec, total, meta)
        elif spec.layout == "mechanism":
            render_mechanism_slide(slide, spec, total, meta)
        elif spec.layout == "figure_takeaway":
            render_figure_takeaway_slide(slide, spec, total, meta, workspace_dir)
        elif spec.layout == "evidence":
            render_evidence_slide(slide, spec, total, meta)
        elif spec.layout == "tradeoffs":
            render_tradeoffs_slide(slide, spec, total, meta)

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
