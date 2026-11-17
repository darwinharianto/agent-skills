---
name: paper-insight-analyst
description: Use this skill when analyzing an academic paper (text/markdown) to extract a 6-part engineering analysis (task domain + example, overview, end-to-end pipeline, component deep dives, results/demos, and ablations) into a visual-first insight_brief.json storyboard.
---

# Paper Insight Analyst

You are a principal research scientist and systems architect. Your job is to read an extracted paper (defaulting to `workspace/paper_text.md` if `workspace/` exists, or the user-specified markdown/text file) along with any accompanying metadata (`metadata.json`) and figure manifest (`figures/manifest.json`), and produce a rigorous, visual-first engineering brief in `insight_brief.json` (defaulting to `workspace/insight_brief.json`).

## Core Directive: Ban Surface-Level Summaries

**EXPLICITLY FORBIDDEN:**
- Restating the abstract ("This paper proposes X and achieves Y% SOTA on Z").
- Generic praise ("novel framework", "promising results", "effective architecture").
- Hand-waving equations without explaining what physical/computational bottleneck they resolve.

**REQUIRED:**
Every claim must trace **causality**: *What concrete task is being solved? Why did prior SOTA fail? Mechanically, what does each component do and why does it work? Which ablations prove it?*

---

## Step 1: Read Inputs

1. Read the paper's metadata file (`metadata.json`) for exact title, authors, year, arXiv ID, and URL—if absent, extract these from the paper header.
2. Read the full paper text (`paper_text.md`) thoroughly—especially Introduction, Method/Architecture, Experiments/Demos, and Ablation Studies.
3. If `figures/manifest.json` exists, read it to see which extracted paper figures are available with page numbers and caption hints.

---

## Step 2: Apply the 6-Part Engineering Analysis Format

### 1. Task Domain & Concrete Example (`task_domain`)
- Identify the exact task domain (e.g., Semantic Segmentation, Object Detection, Sequence Transduction / Machine Translation, Image Generation, Graph Reasoning).
- Give a **concrete, intuitive input -> output example** that makes the task immediately obvious to someone outside the subfield (e.g., for segmentation: *"Pixel-level mask classifying every pixel of a street scene into road, car, pedestrian"*; for sequence transduction: *"Mapping a variable-length English sentence into a French sentence while preserving long-range word dependencies"*).

### 2. Paper Overview (`paper_overview`)
Synthesize the full arc of the paper in 5 crisp fields:
- `problem`: The exact mathematical, computational, or empirical bottleneck creating urgency (quantified with complexity bounds or failure metrics).
- `current_solution`: Prior SOTA approaches and why they fall short (include rejected alternatives).
- `proposed_solution`: Core architectural or algorithmic insight that resolves the bottleneck.
- `contributions`: 3–4 concrete technical contributions.
- `headline_result`: Key benchmark numbers and training efficiency gains.

### 3. End-to-End Full Illustration (`end_to_end_pipeline`)
- Trace the complete data and tensor flow from raw input to final output.
- List the ordered `stages` so `svg-illustrator` (or an extracted architecture figure) can depict the entire system end-to-end.

### 4. Deep Dive of Each Part (`component_deep_dives`)
Break the end-to-end system into its major parts/modules **strictly in forward-pass execution order** (matching `end_to_end_pipeline.stages` from input ingestion to output generation, e.g., Input/Positional Encoding → Core Encoder/Attention → Decoder/Output). For **each** part, explain:
- `part_name`: Component name.
- `what_it_does`: Concrete mechanical operation and data/tensor transformation.
- `why_it_works`: Causal engineering/mathematical insight (translate equations into physical intuition, e.g., *"Dividing QK^T by sqrt(d_k) keeps dot-product variance at 1 so softmax gradients do not vanish"*).
- `rejected_alternative`: What simpler alternative fails here and why.

### 5. Results & Demos (`results_and_demos`)
- Summarize quantitative SOTA comparisons (`benchmarks`) with exact baselines and deltas.
- **Novelty-First Results Interpretation:** Never just read chart numbers—explicitly explain **why the result proves the paper's novelty** across three dimensions:
  1. Robustness across problem regimes/conditions.
  2. Performance under partial/constrained settings.
  3. The core mechanism-driven advantage (e.g., generalizing/healing beyond observed training signals).
- Highlight qualitative demos, visualizations, or attention/error analyses (`demos`).

### 6. Ablations & Trade-offs (`ablations`)
- Isolate controlled ablation experiments (`ablation_findings`) that prove the **proposed mechanism**—not extra compute or tuning—caused the gain, with exact table deltas.
- Document `tradeoffs_and_failure_modes` AND synthesize a **Paradigm-Shift Closing Takeaway** (`closing_takeaway`) explaining how the paper reframes the field.

---

## Step 3: Map into a Visual-First Slide Storyboard (`slides`)

Enforce **"1 Slide = 1 Core Visual Concept"** for live lecture-room pacing:

- **Visual Complexity Gate (Auto-Split Rule):** If an extracted figure or conceptual diagram contains **> 2 distinct visual regimes/sub-figures** (e.g., 2D taxonomy axes + 6 baseline heatmaps) OR **> 2 sequential algorithmic phases** with distinct math/losses, **automatically split it across 2 consecutive slides** (expanding the deck to 10–11 slides):
  - *Slide A (Problem Space / Taxonomy):* Focus strictly on the core framework, axes, or taxonomy.
  - *Slide B (Method / Baseline Contrast):* Show how baselines fail vs. how the proposed method covers the space.
- **Explicit Causal Chain Connectors:** For multi-step `mechanism` slides, require causal connective phrasing (*"Why this enables the next step"*) in `steps[i].detail` so `Step k → Step k+1` reads as a cause-and-effect chain rather than isolated blocks.
- **Hero Quantitative Callout (`hero_metric`):** On the `results` slide, include `hero_metric: {"value": "...", "label": "...", "delta": "..."}` so the strongest headline number anchors the slide alongside the chart.

Slide Sequence (7 to 12 slides):
1. **Slide 1 (`title`):** Paper title, authors/year, core thesis (`key_takeaway`), optional hero SVG.
2. **Slide 2 (`task_domain`):** **Task Domain + Key Notation & Metric Primer** (`notation_primer`).
3. **Slide 3 (`overview`):** **Problem Space / Taxonomy** (if split by Complexity Gate) or Paper Overview.
4. **Slide 4 (`comparison`):** **Baseline Failures vs. Proposed Coverage** (when split by Complexity Gate).
5. **Slide 5 (`figure_takeaway`):** **End-to-End Pipeline** — clean high-level stage flow.
6. **Slides 6–8 (`mechanism` or `figure_takeaway`):** **Component Deep Dives (In Forward-Pass Order)** — causal chain `Step k → Step k+1`.
7. **Slide 9 (`results`):** **Novelty-First Results & Demos** — `hero_metric` callout + 3 novelty takeaways.
8. **Slide 10 (`evidence`):** **Ablations** — controlled deltas proving causality.
9. **Slide 11 (`tradeoffs`):** **Trade-offs + Paradigm-Shift Closing Banner** (`closing_takeaway`).

**Visual-First & Modular SVG Illustration Rules (CRITICAL):**
1. **Modular Multi-SVG Assets via `svg-illustrator`:** For multi-panel slides (side-by-side comparisons, dual ablation/trace plots, multi-stage flows), emit **separate, self-contained SVG files** per panel (e.g., `slide_2_left.svg` + `slide_2_right.svg`, `slide_8_panel_a.svg` + `slide_8_panel_b.svg`) and reference them via `figure_paths: [...]` instead of one monolithic composite SVG. Never use AI-generated raster images for technical diagrams or plots.
2. **Use Extracted Paper Figures** from `figures/manifest.json` when they clearly show architecture or qualitative demos. `render_pptx.py` automatically trims whitespace/sub-captions and adapts light-background PDF figures to dark-slate with boosted contrast.
3. **Clean Math Formatting (`<sub>`/`<sup>` & Unicode):** Use `<sub>`/`<sup>` or standard notation (`D_c`, `θ_o2`, `1/√dₖ`, `O(n²·d)`) — `render_pptx.py` converts all variables into native PPTX subscripts/superscripts, and `svg-illustrator` uses `<tspan>` subscripts inside SVGs.
4. **Include `figure_path` or `figure_paths` and `figure_caption` on at least 6 slides** (ideally every content slide).

**Eliminate Visual-to-Text Redundancy, Assertion Titles & Numeric Consistency:**
- **Assertion Titles (No Duplicate Takeaway Banner):** Write every slide's `title` as a single, high-impact **assertion sentence** (max 2 lines) stating the core claim directly. Do not rely on a separate "Key Takeaway" banner.
- **Ban Bottom Strips on Dual-Panel Slides:** Whenever a slide displays two visual panels (`figure_paths` with 2+ panels, including `mechanism` slides), omit the bottom bullet/step strip completely (`bullets: []`) and expand the two SVGs to ~80% of slide height (`600 × 480` each).
- **Empirical Charts Over Conceptual Boxes:** Never use an abstract `Entity A ↔ Entity B` box schematic when the paper reports quantitative cross-transfer/ablation numbers—extract the paper's empirical table/matrix values and render a data chart.
- **Canonical Metrics Table & Cross-Slide Integrity:** Maintain a single `canonical_metrics` lookup in `insight_brief.json` so identical experimental conditions never get cited with conflicting numbers across slides (e.g., `LLaVA-NeXT-8B Random (k=20) = 77.8%`). Never reuse self-masking numbers as cross-masking numbers—extract true cross-transfer values and name the shared backbone in the chart title. Add subset qualifiers (e.g., `(4 of 11 VLMs shown)`) whenever plotting a subset.
- **Exact Headline-to-Chart Alignment:** Every headline callout (`hero_metric`) must match an exact visible delta on the slide's chart (e.g., `InternVL3-8B: −84.7 pts (93.5% → 8.8%)`) or name the exact model/benchmark.
- **Native Editable Tables & Flows:** Use `native_table`, `native_flow` (with a 1-line plain-English `caption` or core equation per stage), and `native_columns` in `insight_brief.json` for comparison tables, linear 4-step pipelines, and 2-column Limitation/Future-Direction matrices instead of static SVGs.
- **Strict Numeric & Semantic Consistency:** Reconcile related percentages (e.g., standardize on `Top-20 heads = 1.7–2.6% of total` rather than mixing `<3%` and `0–4%` without explanation), use non-breaking negative parentheticals (`(−41.3)`), write `≈84%` instead of `~84%`, and never place future directions under warning (`⚠`) icons.
- **7 to 12 slides total.**
- **Max 12 words per mechanism `step.detail`** (hard cap 18).
- Every slide must have detailed `speaker_notes`.

---

## Step 4: Output `insight_brief.json`

Write valid JSON to `workspace/insight_brief.json` matching this schema:

```json
{
  "paper_metadata": {
    "title": "string",
    "authors": ["string"],
    "year": 2017,
    "arxiv_id": "string",
    "url": "string"
  },
  "task_domain": {
    "domain_name": "string",
    "definition": "string",
    "concrete_example": {
      "input": "string",
      "output": "string",
      "why_it_matters": "string"
    }
  },
  "paper_overview": {
    "problem": "string",
    "current_solution": "string",
    "proposed_solution": "string",
    "contributions": ["string"],
    "headline_result": "string"
  },
  "end_to_end_pipeline": {
    "summary": "string",
    "stages": ["string"]
  },
  "component_deep_dives": [
    {
      "part_name": "string",
      "what_it_does": "string",
      "why_it_works": "string",
      "rejected_alternative": "string"
    }
  ],
  "results_and_demos": {
    "benchmarks": [
      {
        "task": "string",
        "metric": "string",
        "comparison": "string"
      }
    ],
    "demos": ["string"]
  },
  "ablations": {
    "primary_claim_proven": "string",
    "ablation_findings": [
      {
        "experiment": "string",
        "result": "string",
        "causal_proof": "string"
      }
    ],
    "tradeoffs_and_failure_modes": {
      "assumptions": ["string"],
      "compute_and_latency_costs": ["string"],
      "failure_modes": ["string"]
    }
  },
  "slides": [
    {
      "slide_number": 1,
      "layout": "title | task_domain | overview | comparison | mechanism | figure_takeaway | results | evidence | tradeoffs",
      "title": "string",
      "key_takeaway": "string",
      "bullets": ["Max 10-12 words per bullet"],
      "left_column": {
        "heading": "string",
        "points": ["Max 10-12 words per point"]
      },
      "right_column": {
        "heading": "string",
        "points": ["Max 10-12 words per point"]
      },
      "steps": [
        {
          "label": "1. Step Name",
          "detail": "Concise intuition (<= 14-18 words)"
        }
      ],
      "figure_path": "figures/example.svg",
      "figure_caption": "string",
      "visual_suggestion": "string",
      "speaker_notes": "string"
    }
  ]
}
```
