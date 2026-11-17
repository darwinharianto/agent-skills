---
name: technical-deck-builder
description: Use this skill when validating an insight_brief.json storyboard against slide visual density rules and rendering a 16:9 technical PowerPoint (.pptx) presentation.
---

# Technical Deck Builder

You are responsible for turning a structured `insight_brief.json` storyboard into a crisp, zero-overflow 16:9 technical presentation (`.pptx`) using [render_pptx.py](./scripts/render_pptx.py).

By default, `render_pptx.py` reads `workspace/insight_brief.json`, resolves `figures/` relative to `workspace/`, and writes `workspace/output_deck.pptx`. In any project with a different layout, pass `--input`, `--output`, and `--workspace` explicitly.

## Slide Narrative & Visual Density Rules

Before rendering, verify `insight_brief.json` satisfies every density and layout constraint:

1. **Slide Count:** 7 to 12 slides total (`slides` array).
2. **Word Budget:**
   - Every bullet in `bullets` and every point in `left_column.points` / `right_column.points` MUST be **<= 12 words** (prefer **<= 10 words** on visual slides).
   - Every `key_takeaway` MUST be **<= 24 words** (one sharp sentence).
   - Every `steps[i].detail` in `mechanism` slides MUST be **<= 18 words** (prefer **<= 14 words**).
3. **Bullet Density & Visual Balance:** Max **5 bullets** per slide or column (prefer **3–4 bullets** when paired with a visual). Never dump paragraphs into slides—move detailed prose to `speaker_notes`.
4. **Layout-Specific Requirements:**
   - `title`: Slide 1, sets the core thesis in `key_takeaway`; optionally accepts `figure_path` for a right-side hero illustration.
   - `task_domain`: Explains the problem domain and concrete example; pairs concise bullets with an optional `figure_path` illustration.
   - `overview`: Summarizes problem, current solution, proposed solution, contributions, and result; pairs with an optional `figure_path` or `left_column`/`right_column`.
   - `comparison`: Requires `left_column` ("Prior Bottleneck") and `right_column` ("New Insight"); optionally accepts `figure_path` to pair stacked contrast cards with a visual diagram.
   - `mechanism`: Requires `steps` (2–4 causal steps) translating math into engineering intuition; optionally accepts `figure_path` for a side-by-side mechanism diagram.
   - `figure_takeaway`: Requires `figure_path` pointing to an existing PNG, JPG, or SVG (resolved relative to `--workspace`) and a concise `figure_caption`.
   - `results`: Highlights benchmark gains and qualitative demos; optionally accepts `figure_path` for a demo/chart visual.
   - `evidence`: Highlights ablation deltas proving causality; optionally accepts `figure_path` for an ablation chart or plot.
   - `tradeoffs`: Highlights assumptions, compute/memory costs, and failure modes; optionally accepts `figure_path` for a scaling or failure-mode illustration.
5. **Assertion Titles, Native Editable Shapes/Tables, and 70–80% Visual Scale (`render_pptx.py`):**
   - **Assertion Titles (No Redundant Takeaway Banner):** `add_chrome` renders `spec.title` as a `23pt` bold assertion headline (max 2 lines) without a separate `Key Takeaway:` banner, freeing `0.69"` of vertical height.
   - **Balanced Slide 1 (`highlights`):** Slide 1 supports a 3-card **Executive Highlight Grid** (`Core Mechanism`, `Headline Result`, `Scope`) with **`15pt`** body text filling the lower 50% of the cover slide.
   - **Projection Font Floor (`>= 14pt` Native Text):** Results Headline Pill (Slide 7) uses **`16pt–18pt` bold**; Pipeline Step Sub-captions (Slide 4) use **`14pt` minimum**; Title Slide summary card body text uses **`15pt` minimum** (only Slide 2's `11pt` notation footnote and slide footer may be smaller).
   - **Full-Height Dual-Panel Slot (`5.42"`):** Dual-panel visual slides (`figure_paths`) ban bottom 3-card/bullet strips and expand visuals to **`5.42"`** height (`~85%` of content height), paired with `600 × 520` SVGs so zero dead band appears above the footer. Slide 2's `notation_primer` sits at **`y = 6.95"`**.
   - **Native Editable Tables, Flows, Column Matrices & Box Diagrams (`panels`):** Use `native_table`, `native_flow`, `native_columns`, and `panels` (`type: "diagram"`) so comparison tables, linear process flows, Limitation/Future-Direction matrices, and **all box-and-arrow schematics** (flowcharts, nested containers, before/after state boxes) render as razor-sharp, editable `python-pptx` grouped shapes (`MSO_SHAPE.ROUNDED_RECTANGLE`, native text runs with subscripts, `MSO_CONNECTOR.STRAIGHT` arrows, grouped via `add_group_shape()`) using the exact Soft Pastel Editorial palette and `1.5pt` rounded borders. Reserve SVGs (`type: "image"`) strictly for quantitative data visualizations.
   - **Full-Bleed Borderless Charts & Tight Margins (`0.35"`):** `add_figure_box(..., framed=False)` places SVG visuals directly on the `#FAF9F6` slide canvas without padded outer card boxes, using tight `0.35"` left/right margins (`w=12.63"`) to maximize chart area.
   - **Full-Width Results Layout (`results`):** Never squeeze a multi-group results chart beside a giant side card. Render `hero_metric` as a compact top-right corner badge and let the results chart span **100% of the content width** (`12.63"`).
   - **Optional Bottom Strip (`bullets: []`) & Slide 2 Footnote:** Bottom bullet strips default to empty so visuals expand to **`5.36"`** height (~80% of slide). Slide 2's `notation_primer` renders as a single-line `11pt` muted footnote pinned at `y = 7.10"`.
   - **Compact Native Pipeline Cards (`native_flow`):** Linear 4-step pipeline cards stay compact (`~55%` slide height) with a 1-line plain-English definition or core equation (`caption`) at the bottom of each card.
   - **Modular Grids (`figure_paths`):** When `figure_paths` is provided (2–4 modular SVGs), `render_pptx.py` renders each panel in its own independent PPTX shape card inside the visual zone.
   - **Slide 2 `notation_primer`, `results` `hero_metric`, Causal `→` Connectors & Final Slide `closing_takeaway`:** `render_pptx.py` renders `notation_primer` as a Key Notation & Metric Strip on Slide 2, `hero_metric` as a `36pt` Hero Metric Callout Card alongside the Results chart (`5.20"` height), `→` causal connectors between consecutive `mechanism` step cards, and `closing_takeaway` as a high-contrast Paradigm-Shift Closing Banner on the final slide.
   - **Universal `<sub>`/`<sup>` Math, Non-Breaking Deltas & Light-Mode Transparency:** `render_pptx.py` renders `<sub>`/`<sup>` and `X_sub`/`X^sup` variables using native OOXML baseline subscripts/superscripts, normalizes `(-41.3)` to non-breaking `(⁠−41.3)` and `~84%` to `≈84%`, and converts pure-white PDF figure backgrounds (`RGB > 245`) to transparent (`alpha = 0`).

---

## Execution Workflow

### Prerequisites

Ensure `python-pptx` and `pydantic` are installed in the active Python environment (e.g., `pip install -r ./requirements.txt` inside the skill folder if missing).

### Step 1: Validate `insight_brief.json`

Run the deterministic Pydantic validator first (adjusting `--input` / `--workspace` if not using `workspace/`):

```bash
python3 <skill-dir>/scripts/render_pptx.py --validate-only \
  --input <path/to/insight_brief.json> \
  --workspace <path/to/assets_dir>
```

If validation fails:
- Read the exact field and word-count error reported by Pydantic.
- Edit `insight_brief.json` to tighten verbose bullets (<= 12 words), fix missing layout fields, or correct `figure_path` references.
- Re-run `--validate-only` until it exits with code `0`.

### Step 2: Render the `.pptx` Deck

Once validation passes, run the renderer:

```bash
python3 <skill-dir>/scripts/render_pptx.py \
  --input <path/to/insight_brief.json> \
  --output <path/to/output_deck.pptx> \
  --workspace <path/to/assets_dir>
```

*(When working in a project that uses the standard `workspace/` directory, you can omit `--input`, `--output`, and `--workspace`.)*

### Step 3: Automated Visual QA (`deck-reviewer`) & Verify Output

After rendering `output_deck.pptx`, invoke the **`deck-reviewer`** skill (`.agent/skills/deck-reviewer/SKILL.md`):
1. Rasterize all slides to PNGs via `.agent/skills/deck-reviewer/scripts/rasterize_deck.py`.
2. Inspect every slide against the 5-point visual QA checklist (no text/curve overlaps, no stretched aspect ratios, no clipping or >3-line card wrapping, consistent dark-mode theme, consistent Unicode math).
3. If any slide fails, patch the offending SVG, `insight_brief.json` copy, or layout, re-render, and re-verify (up to 2 QA iterations) before reporting the final slide count and output path.
