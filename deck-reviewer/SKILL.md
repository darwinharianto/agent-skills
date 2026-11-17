---
name: deck-reviewer
description: Use this skill after rendering output_deck.pptx to rasterize every slide into PNGs and run an automated 5-point visual QA inspection loop before finalizing the presentation.
---

# Deck Reviewer (Automated Visual QA)

You are a meticulous presentation QA engineer. Your job is to convert the rendered `.pptx` deck into slide PNGs using [rasterize_deck.py](./scripts/rasterize_deck.py), visually inspect **every** slide image, and flag any layout, typography, cropping, or theme defects before delivery.

## Step 1: Run Automated SVG Density Audit & Rasterize the `.pptx`

First, run the SVG word-count density audit (`<= 35` total words per SVG, `<= 5` words per `<text>` node, zero `•` bullets):

```bash
python3 .agent/skills/deck-reviewer/scripts/svg_word_audit.py workspace/figures/
```

If any SVG fails, simplify it into visual primitives/charts before proceeding. Then run the slide rasterizer:

```bash
python3 .agent/skills/deck-reviewer/scripts/rasterize_deck.py \
  --input workspace/output_deck.pptx \
  --output-dir workspace/review_slides
```

This converts `output_deck.pptx` via LibreOffice (`soffice --headless --convert-to pdf`) and renders each page to `slide_01.png`, `slide_02.png`, ... at 150 DPI using `pymupdf`.

## Step 2: Inspect Every Slide Against the 5-Point Pass/Fail Checklist

View each `workspace/review_slides/slide_*.png` image and verify **all 5 criteria**:

1. **No Text / Curve / Line Overlaps & Plateau Clearance:**
   - Inside SVGs and plots, curve lines, arrows, and region boundaries must never intersect text labels (`>= 16px` buffer, and `>= 22px` below flat horizontal plateaus).
2. **Modular Multi-SVGs & Unstretched Aspect Ratios:**
   - Multi-panel slides use modular `figure_paths` SVGs sized to their slot aspect ratio (`no squashing`), and extracted PDF figures preserve native proportions.
3. **No Text Clipping, Overflow, or >3-Line Card Wrapping:**
   - All titles, key takeaways, bullets, bottom-strip cards, and word-boundary footer titles fit cleanly without mid-word truncation or >3-line wrapping.
4. **Consistent Light-Mode Pastel Contrast & Unclipped Multi-Panel Crops:**
   - All text and chart labels use high-contrast dark ink (`#1E293B`, `#475569`, or dark semantic shades `#0369A1`/`#15803D`/`#BE123C`/`#B45309`/`#7E22CE`) against `#FAF9F6` / `#FFFFFF` / pastel fills—never light pastel text on light backgrounds.
   - Zero dark-inverted or black-box PDF figure artifacts (native PDF figures have transparent white backgrounds blending onto `#FAF9F6`/`#FFFFFF`), no raw `"Figure X:"` paragraphs, and **no sub-figure grid row or label (e.g., `(d) ETD`, `(g) REM (ours)`) is clipped at the bottom edge**.
6. **SVG Visual Density, Series-Color Consistency & Projection Readability:**
   - Every generated SVG represents **1 core visual concept**, has **<= 35 total words**, **<= 5 words per `<text>` node**, **zero `•` bullets**, and **`>= 16px` minimum font size** for all sub-labels and axis ticks.
   - Bottom takeaway boxes use **`>= 14pt`** font size and **2–3 bullets of `<= 8 words` each**.
   - Slide 2 includes a **Key Notation & Metric Strip** (`notation_primer`), and the final slide ends with a **Paradigm-Shift Closing Banner** (`closing_takeaway`) rather than limitations alone.
   - In grouped bar charts, every series bar must match its exact legend swatch color across **all** x-axis categories.
7. **Visual Complexity Gate, Causal Connectors & Hero Metric Callout:**
   - Fail any slide that combines a taxonomy/problem-space diagram with `> 3` baseline comparison panels without splitting across 2 consecutive slides.
   - Multi-step mechanism slides must display explicit causal `→` links between consecutive steps.
   - The `results` slide must feature a high-visibility **Hero Metric Callout** (`28–36pt` value + delta vs. prior SOTA) alongside the chart.
8. **Full-Bleed Charts, Y-Axis Labels, Font Floor (`>= 20px`) & Zero Redundancy (CRITICAL):**
   - **No Double-Card Framing:** Fail any chart slide that wraps an SVG inside a padded outer border card.
   - **SVG Font Floor (`>= 20px`) & Explicit Y-Axis Title:** Fail any chart SVG that lacks a rotated Y-axis metric+unit title (e.g., `Grounding Accuracy (%)`) or contains text smaller than `20px` equivalent.
   - **Accurate Curve Labels:** Fail if a negative delta (`-84%`) is attached to a flat high-accuracy line rather than the collapsing curve.
   - **Zero Blank Vertical Bands & No Dual-Panel Bottom Strips:** Fail any slide where a short landscape SVG leaves blank vertical bands inside a tall slot (use `600 × 480` / `1200 × 540`), or where a dual-panel visual slide renders a redundant bottom 3-card/bullet strip.
   - **Strict Visual Routing Audit (Native Box Diagrams vs. SVG Data Charts):** Fail any generated `.pptx` where a box-and-text schematic (composed of rounded rectangles, nested containers, text callouts, or connecting arrows with no plot axes or data curves) is embedded as an image/SVG instead of native editable grouped PowerPoint shapes (`add_group_shape()`).
   - **Cross-Slide Number Audit & Anti-Placeholder Gate:** Cross-check identical metric keys across all slides for numeric drift (e.g., `LLaVA-NeXT-8B Random (k=20)` must match identically on Slides 7 and 8), verify self-masking numbers are never reused as cross-masking numbers, verify subset charts state `(X of Y shown)`, and verify delta/drop charts display the starting unmasked baseline next to each bar (`−41.3 pts (from 78.2%)`).
   - **Projection Font Floor (`>= 14pt` Native Text) & Zero Dead Bands:** Fail any native text element below `14pt` (except Slide 2's `11pt` notation footnote and the slide footer), including Slide 7's headline pill (`>= 16pt`), Slide 4's step sub-captions (`>= 14pt`), and Slide 1's summary card body (`>= 15pt`). Fail any dual-panel visual slide with a dead band above the footer (`600 × 520` fills `5.42"`).
   - **Balanced Slide 1 & Slide 2 Footnote:** Fail if Slide 1 leaves the bottom half empty, or if Slide 2's `11pt` notation footnote wraps onto two lines or collides with diagrams.
   - **Numeric & Semantic Consistency:** Fail if `~` is used (`~84%` instead of `≈84%`), if negative parentheticals break across lines (`(-` / `41.3)`), or if warning icons (`⚠`) accompany future directions.

## Step 3: Patch & Re-Verify (Up to 2 Iterations)

- If **all slides pass** all 5 checks: report `QA PASS` and finish.
- If **any slide fails**:
  1. Report the exact slide number(s) and failed check(s).
  2. Patch the offending SVG, `insight_brief.json` copy, or `render_pptx.py` layout.
  3. Re-render `output_deck.pptx`, re-run `rasterize_deck.py`, and re-inspect the patched slides (up to 2 QA iterations).
