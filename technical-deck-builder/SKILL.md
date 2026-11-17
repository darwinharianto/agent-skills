---
name: technical-deck-builder
description: Use this skill when validating an insight_brief.json storyboard against slide visual density rules and rendering a 16:9 technical PowerPoint (.pptx) presentation.
---

# Technical Deck Builder

You are responsible for turning a structured `insight_brief.json` storyboard into a crisp, zero-overflow 16:9 technical presentation (`.pptx`) using [render_pptx.py](./scripts/render_pptx.py).

By default, `render_pptx.py` reads `workspace/insight_brief.json`, resolves `figures/` relative to `workspace/`, and writes `workspace/output_deck.pptx`. In any project with a different layout, pass `--input`, `--output`, and `--workspace` explicitly.

## Slide Narrative & Visual Density Rules

Before rendering, verify `insight_brief.json` satisfies every density and layout constraint:

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
   - `figure_takeaway`: Requires `figure_path` pointing to an existing PNG (resolved relative to `--workspace`) and a concise `figure_caption`.
   - `evidence`: Highlights ablation deltas proving causality.
   - `tradeoffs`: Highlights assumptions, compute/memory costs, and failure modes.

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

### Step 3: Verify Output

Confirm that the target `.pptx` file exists, is non-empty, and report the slide count and output path.
