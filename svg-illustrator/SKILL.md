---
name: svg-illustrator
description: Use this skill when creating crisp, Soft Pastel Editorial technical SVG illustrations (task-domain examples, end-to-end pipelines, component deep-dives, and ablation/scaling charts) and converting them to high-DPI PNGs for technical-deck-builder.
---

# SVG Technical Illustrator

You are a technical visual designer. Your job is to turn abstract ML/systems concepts from `insight_brief.json` into **crisp, legible, vector-first SVG illustrations** saved in `workspace/figures/` and converted to high-DPI PNGs (via [svg_to_png.py](./scripts/svg_to_png.py)) for import into PowerPoint by `technical-deck-builder`.

## Why SVG First?
- **Zero blurry or misspelled text:** Every label, tensor shape, equation term, and metric delta is exact—no raster/AI-generated plot artifacts or decorative icons.
- **Mathematically accurate curves:** Scaling plots ($O(n^2 d)$ vs. $O(n d^2)$) and bar charts use exact computed coordinates.
- **Consistent Soft Pastel Editorial theme:** Matches the Warm Alabaster PowerPoint palette (`#FAF9F6` canvas, `#FFFFFF`/`#F1F5F9` cards, `#1E293B` dark charcoal ink, and soft pastel fills with saturated borders).
- **Clean notation:** Use proper math symbols (`π`, `√d_k`, `·`, `²`) and `<tspan>` subscripts.
- **Seamless PowerPoint import:** `svg_to_png.py` rasterizes SVGs at 200 DPI using `pymupdf`.

---

## Scope: Quantitative Data Visualizations Only

- **No Box-and-Arrow Schematics in SVGs:** Do **not** render comparison tables, linear process flows, 2-column matrices, Hero Stat Callouts, or **any box-and-arrow diagram** (rounded rectangles, nested containers, text callouts, before/after state boxes, connecting arrows) as static SVGs. Let `technical-deck-builder` render all of those as native, grouped, editable `python-pptx` shapes (`panels` with `type: "diagram"`).
- **Reserve `svg-illustrator` Strictly for Data Visualizations:** Use SVGs only for quantitative bar charts, line curves, scatter plots, proportional stacked bars, and mathematical plots that require coordinate axes and data scaling.
- **Exact Chart Annotations:** Never use `~` characters that look like minus signs (`~84%`); write `≈84%` or `84%` clearly. Never break negative parenthetical deltas across lines (`(−41.3)`). Reconcile related percentages consistently across labels.

## Modular Multi-SVG Design System

**Never build one giant composite SVG for multi-panel slides** (e.g., side-by-side comparisons, dual plots, or multi-stage blocks). Instead, emit **separate, self-contained SVG files** per logical visual unit (e.g., `slide_2_left.svg` + `slide_2_right.svg`, `slide_8_panel_a.svg` + `slide_8_panel_b.svg`) and pass them via `figure_paths` in `insight_brief.json` so PowerPoint renders each panel as an independent, editable shape.

Match each SVG's `viewBox` to its target slot aspect ratio (never center a short landscape SVG inside a tall slot with blank bands above/below):
- **Single Widescreen Full-Height Slot (`12.63" × 5.36"`):** `viewBox="0 0 1200 540"`
- **2-Panel Modular Full-Height Grid (`6.20" × 5.42"` each):** `viewBox="0 0 600 520"` (eliminates dead bands above the footer)
- **2-Panel Modular Compact Grid (with bottom strip, `6.20" × 3.80"`):** `viewBox="0 0 600 360"`
- **3-Panel Modular Grid (`4.06" × 5.36"` each):** `viewBox="0 0 420 480"`

Rules for every SVG:
- **Mandatory Baseline Context on Delta Charts:** Whenever a bar chart plots relative drops or deltas (e.g., `−41.3 pts`), always display the **starting unmasked baseline** next to each bar label (e.g., `−41.3 pts (from 78.2%)`) so the audience knows the scale of the drop.
- **Explicit Subset Qualifiers & Shared Backbones:** If a chart plots a representative subset (e.g., 4 of 11 VLMs), include `(4 of 11 VLMs shown)` in the chart title/subtitle. For cross-masking charts, explicitly name the shared backbone in the title.
- **Reconcile Distribution Buckets & Ablation Units:** Never display overlapping un-reconciled percentages on the same chart (use one mutually exclusive partition that sums cleanly). On ablation bar charts, label the intervention state explicitly (`Ours Masked (20%)`) and keep **consistent units** across all bars (`% IoU Acc`, never mixing `20%` and `+30.7`).
- **Anti-Card & Visual Encoding Rule (CRITICAL):** **Ban bullet points (`•`) and full sentences inside SVGs.** Never render multi-line prose boxes or stacked text cards as "diagrams." Encode concepts visually:
  - *Comparative metrics / trade-offs* → **bar charts, scatter plots, or curves**.
  - *Data / masking / routing* → **matrices, `0/1` binary mask grids, image/patch icons, weighted arrows, tensor blocks, or before/after state transitions**.
- **Strict Word Cap:** Hard limit of **≤ 4 words per `<text>` node** (check ≤ 5 in QA) and **≤ 35 total words per SVG**.
- **No Duplicate Titles/Subtitles Inside SVGs:** The slide template already renders the slide title and `Key Takeaway` banner. Start diagram content at `y = 20px` and use the reclaimed height for larger visual primitives and labels.
- **Explicit Causal Chain Connectors:** For multi-step deep-dive diagrams, link consecutive phases with a visual **cause → effect connector bar/arrow** and short causal label (e.g., `Step 1 → Step 2: Prepares θ_o1`) so the audience sees *why* Step $k$ is a prerequisite for Step $k+1$.
- **Minimum Projection Font Size (`>= 20px`):** Increase minimum SVG axis/tick/bar label sizes to **`20px–22px`** (and titles to **`24px–26px`**) on a `1200px` coordinate grid (or equivalent proportional scale) so every chart value is effortlessly readable from the back of a lecture room.
- **Explicit Y-Axis Metric Title & Accurate Line Labels:** Every bar/line chart must include a rotated Y-axis title stating the exact metric and unit (e.g., `Grounding Accuracy (%)` or `Post-Masking IoU (%)`). Never attach a negative delta label (`-84%`) to a flat high-accuracy line; label flat baseline curves with their actual level (`Prior Heads & Random (≈84% Acc)`) and place drop deltas (`-78.8% Drop`) directly on the collapsing curve.
- **Clean SVG Subscripts/Superscripts:** Never rewrite `D_c` → `D(c)` or drop characters (`θ_o1` → `θ₁`). Keep faithful notation (`D_c`, `D_tr`, `θ_o1`, `θ_o2`, `L_redirect`) or explicit `<tspan dy="4" font-size="75%">...</tspan><tspan dy="-4">&#8203;</tspan>` — `svg_to_png.py` automatically converts `_subscript` tokens into `<tspan>` subscripts and adjusts centered `<text>` anchors so PyMuPDF renders every subscript cleanly without overlaps.
- **Series-Color Consistency (Grouped Bar Charts):** Every series in a grouped bar chart must use its exact legend swatch color across **all** x-axis categories—never recolor an individual bar in a series to a different highlight/warning color.
- **Plateau & Curve Label Collision Avoidance (`>= 16px` / `>= 22px` Buffer):** Keep curve/region labels offset from all plotted lines with a minimum `16px` buffer and `#FFFFFF` background pills with saturated borders. For callout pills near **flat horizontal plateaus** (`y ≈ 100%`), offset the pill **at least `22px` below** the plateau line so pill borders never touch plotted curves.
- **Palette (Soft Pastel Editorial — Never Use Light Pastel for Text):**
  - **Canvas Background:** `#FAF9F6` (Warm Alabaster) or `#FFFFFF`
  - **Card / Sub-surface Fill:** `#FFFFFF` or `#F1F5F9` (stroke `#CBD5E1`, `stroke-width="1.5"`, `rx="10"`)
  - **Typography Ink:** Primary `#1E293B` (Deep Charcoal), Muted `#475569` (Slate)
  - **Semantic Pastel Node & Chart Colors (Soft Fill + Saturated Stroke + Dark Label Ink):**
    - **Blue:** fill `#E0F2FE`, stroke `#0284C7`, label `#0369A1`
    - **Mint Green:** fill `#DCFCE7`, stroke `#16A34A`, label `#15803D`
    - **Soft Rose / Coral:** fill `#FFE4E6`, stroke `#E11D48`, label `#BE123C`
    - **Warm Amber:** fill `#FEF3C7`, stroke `#D97706`, label `#B45309`
    - **Soft Lavender:** fill `#F3E8FF`, stroke `#9333EA`, label `#7E22CE`
- **Font:** `font-family="Arial, Helvetica, sans-serif"`, minimum `16px–18px`.
- **Arrows:** Always define a clean `<marker id="arrow" ...>` in `<defs>` using saturated strokes (`#0284C7`, `#16A34A`, `#E11D48`).

---

## What to Illustrate (Mapped to the 6-Part Analysis)

1. **Task Domain Example (`task_domain.svg`):**
   - Show a concrete input -> output example of the problem (e.g., image -> pixel segmentation masks; image -> bounding boxes; English sentence -> French sentence with token alignment).
2. **End-to-End Pipeline (`end_to_end.svg`):**
   - Full left-to-right (or top-to-bottom) system diagram showing input, major stages, tensor/data flow, and final output.
3. **Component Deep Dives (`component_<name>.svg`):**
   - Zoom into *one* mechanism (e.g., Scaled Dot-Product Attention, Multi-Head subspace split, Residual + LayerNorm, or Sinusoidal Encoding) showing *what* happens and *why* it works (e.g., variance `d_k -> 1` before softmax).
4. **Results & Demos (`results_demo.svg`):**
   - Clean benchmark comparison chart or qualitative demo visualization (if not already covered by an extracted paper figure).
5. **Ablations (`ablations_chart.svg`):**
   - High-contrast bar or delta chart with exact numbers above each bar, highlighting the optimal/causal configuration in Emerald `#10B981`.

---

## Workflow

1. Write each SVG file to `workspace/figures/<name>.svg`.
2. Verify layout hygiene:
   - No text overflowing its box or overlapping arrows.
   - Generous margins (`>= 24px` outer padding, `>= 14px` inside boxes).
   - Keep labels concise (1–4 words per node).
3. Convert to high-DPI PNG (optional if passing `.svg` directly to `render_pptx.py`, recommended for previewing):
   ```bash
   python3 .agent/skills/svg-illustrator/scripts/svg_to_png.py \
     workspace/figures/<name>.svg \
     workspace/figures/<name>.png \
     --dpi 200
   ```
4. Reference `figures/<name>.png` (or `figures/<name>.svg`) in `insight_brief.json` under `figure_path`.
