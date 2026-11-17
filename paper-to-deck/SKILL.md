---
name: paper-to-deck
description: Use this skill when turning an academic paper (PDF, markdown, or arXiv ID) into a polished technical PowerPoint (.pptx) presentation end-to-end.
---

# Paper-to-Deck Orchestrator

Follow this 4-skill pipeline in exact order when converting a paper into a technical PowerPoint deck. Each stage has its own `SKILL.md` in the same skills directory.

## Pipeline Stages

1. **Stage 1 — Deep Analysis (`paper-insight-analyst`)**
   - Read the paper text (`paper_text.md` or user-provided paper) and any `metadata.json` / `figures/manifest.json`.
   - Produce `insight_brief.json` using the first-principles rubric (bottleneck, motivation, mechanism, ablation proof, trade-offs, and 7–9 slide storyboard).

2. **Stage 2 — Quantitative Visuals (`svg-illustrator`)**
   - For slides needing quantitative charts, curves, or ablation plots, generate clean SVGs and rasterize them to PNGs.
   - Leave box-and-arrow schematics and comparison diagrams to Stage 3's native PowerPoint shapes.

3. **Stage 3 — Deck Rendering (`technical-deck-builder`)**
   - Validate `insight_brief.json` against slide density rules (`--validate-only`).
   - Render the 16:9 presentation to `output_deck.pptx`.

4. **Stage 4 — Visual QA (`deck-reviewer`)**
   - Run the SVG word-density audit and rasterize every slide of `output_deck.pptx` to PNGs.
   - Inspect every rendered slide image; if any slide has clipping, overlap, or density issues, fix `insight_brief.json` or the SVG and re-run Stages 3–4 until clean.
