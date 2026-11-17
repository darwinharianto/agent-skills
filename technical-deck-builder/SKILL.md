---
name: technical-deck-builder
description: Validate workspace/insight_brief.json against slide narrative & visual density rules and render a 16:9 PowerPoint presentation to workspace/output_deck.pptx.
---

# Technical Deck Builder

You are responsible for turning `workspace/insight_brief.json` into a crisp, zero-overflow 16:9 technical presentation (`workspace/output_deck.pptx`) using `scripts/render_pptx.py`.

## Slide Narrative & Visual Density Rules

Before rendering, verify `workspace/insight_brief.json` satisfies every density and layout constraint:

1. **Slide Count:** 7 to 9 slides total (`slides` array).
2. **Word Budget:**
   - Every bullet in `bullets` and every point in `left_column.points` / `right_column.points` MUST be **<= 12 words**.
   - Every `key_takeaway` MUST be **<= 24 words** (one sharp sentence).
   - Every `steps[i].detail` in `mechanism` slides MUST be **<= 18 words**.
3. **Bullet Density:** Max **5 bullets** per slide or column. Never dump paragraphs into slides—move detailed prose to `speaker_notes`.
4. **Layout-Specific Requirements:**
   - `title`: Slide 1, sets the core thesis in `key_takeaway`.
   - `comparison`: Requires `left_column` ("Prior Bottleneck") and `right_column` ("New Insight").
   - `mechanism`: Requires `steps` (2–4 causal steps) translating math into engineering intuition.
   - `figure_takeaway`: Requires `figure_path` pointing to an existing PNG in `workspace/figures/` (e.g., `figures/page_03_vector_fig_01.png`) and a concise `figure_caption`.
   - `evidence`: Highlights ablation deltas proving causality.
   - `tradeoffs`: Highlights assumptions, compute/memory costs, and failure modes.

---

## Execution Workflow

### Step 1: Validate `workspace/insight_brief.json`

Run the deterministic Pydantic validator first:

```bash
python3 .agent/skills/technical-deck-builder/scripts/render_pptx.py --validate-only
```

If validation fails:
- Read the exact field and word-count error reported by Pydantic.
- Edit `workspace/insight_brief.json` to tighten verbose bullets (<= 12 words), fix missing layout fields, or correct `figure_path` references against `workspace/figures/manifest.json`.
- Re-run `--validate-only` until it exits with code `0`.

### Step 2: Render `workspace/output_deck.pptx`

Once validation passes, run the renderer:

```bash
python3 .agent/skills/technical-deck-builder/scripts/render_pptx.py
```

### Step 3: Verify Output

Confirm that `workspace/output_deck.pptx` exists, is non-empty, and report the slide count and output path.
