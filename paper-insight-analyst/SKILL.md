---
name: paper-insight-analyst
description: Use this skill when analyzing an academic paper (text/markdown) to extract first-principles architectural and motivational insights into a structured insight_brief.json storyboard.
---

# Paper Insight Analyst

You are a principal research scientist and systems architect. Your job is to read an extracted paper (defaulting to `workspace/paper_text.md` if `workspace/` exists, or the user-specified markdown/text file) along with any accompanying metadata (`metadata.json`) and figure manifest (`figures/manifest.json`), and produce a rigorous, first-principles engineering brief in `insight_brief.json` (defaulting to `workspace/insight_brief.json` when `workspace/` is used, or the user-specified output path).

## Core Directive: Ban Surface-Level Summaries

**EXPLICITLY FORBIDDEN:**
- Restating the abstract ("This paper proposes X and achieves Y% SOTA on Z").
- Generic praise ("novel framework", "promising results", "effective architecture").
- Hand-waving equations without explaining what physical/computational bottleneck they resolve.

**REQUIRED:**
Every claim must trace **causality**: *Why did prior SOTA fail? What specific observation forced the authors' hand? Why did they reject obvious alternatives? Mechanically, why does this solution work—and what does it break?*

---

## Step 1: Read Inputs

1. Read the paper's metadata file (`metadata.json` in the paper's working directory, e.g., `workspace/metadata.json`) for exact title, authors, year, arXiv ID, and URL—if absent, extract these from the paper header.
2. Read the full paper text (`paper_text.md` or the user-provided paper file) thoroughly—especially Introduction, Method/Architecture, and Ablation Studies (do not stop after the Abstract).
3. If a `figures/manifest.json` (or `figures/` directory) exists alongside the paper, read it to see which extracted figures are available with page numbers and caption hints.

---

## Step 2: Apply the 6-Part First-Principles Rubric

### 1. The Core Bottleneck (`core_bottleneck`)
Identify the exact mathematical, computational, or empirical failure mode of prior SOTA that created urgency:
- What scales poorly (e.g., $O(N^2)$ memory, sequential $O(N)$ dependency preventing GPU parallelization, gradient vanishing, rank/parameter bottleneck)?
- Quantify the failure mode using numbers or complexity bounds from the paper.

### 2. Author Motivation & Compelling Insight (`author_motivation_and_insight`)
- What specific empirical observation or theoretical hypothesis compelled the authors to choose this approach?
- List **at least 2 rejected or obvious alternative approaches** and explain precisely why each falls short (e.g., "Increasing hidden dimension D adds $O(D^2)$ parameters; localized windows lose global context").

### 3. Mechanism of Action ("How & Why It Works") (`mechanism_of_action`)
- Provide a step-by-step causal explanation of how the method operates mechanically.
- **Translate equations into engineering intuition:** Don't just quote a formula—explain what each term *does* (e.g., "dividing by $\sqrt{d_k}$ keeps dot-product variance at 1 so softmax doesn't saturate into near-zero gradients").

### 4. Evidence & Ablation Proof (`evidence_and_ablation`)
- Isolate specific experimental or ablation results that prove the **proposed mechanism**—not merely extra compute, larger datasets, or hyperparameter tuning—caused the performance gain.
- Include concrete deltas from ablation tables in the paper.

### 5. Hidden Trade-offs & Failure Modes (`tradeoffs_and_failure_modes`)
- What implicit assumptions must hold for this method to work?
- What are the new compute, memory, latency, or engineering costs?
- Where does this solution break or underperform?

### 6. Slide-by-Slide Narrative Plan (`slides`)
Map all insights above into a **7-to-9 slide storyboard**:
- **Slide 1 (`title`):** Paper title, authors/year, and the single sharpest architectural thesis.
- **Slide 2 (`comparison`):** "Prior Bottleneck vs. New Insight" — side-by-side contrast of the old failure mode and the new hypothesis/rejected alternatives.
- **Slide 3 (`mechanism`):** Mechanism Breakdown — 3–4 causal steps translating the core math into engineering intuition.
- **Slide 4 (`figure_takeaway`):** Architecture / Core Diagram — reference an extracted figure from `figures/` (e.g., `figures/page_03_vector_fig_01.png`) with a sharp key takeaway.
- **Slide 5 (`mechanism` or `figure_takeaway`):** Deep-dive into the second critical mechanism or scaling behavior.
- **Slide 6 (`evidence`):** Evidence & Ablation Proof — specific ablation deltas proving causality.
- **Slide 7 (`tradeoffs`):** Hidden Trade-offs, Assumptions & Failure Modes.
- *(Optional Slides 8–9)*: Additional `figure_takeaway`, `evidence`, or `comparison` slides if the paper has multiple core mechanisms or rich ablation results.

**Strict Slide Content Rules:**
- **7 to 9 slides total.**
- **Max 12 words per bullet point.** Count words carefully.
- **Max 4–5 bullets per slide.**
- Every slide must have a `key_takeaway` (one crisp sentence, <= 20 words) and detailed `speaker_notes` for the presenter.

---

## Step 3: Output `insight_brief.json`

Write valid JSON to the target `insight_brief.json` path (default `workspace/insight_brief.json` if `workspace/` exists, otherwise in the working directory) matching this exact schema:

```json
{
  "paper_metadata": {
    "title": "string",
    "authors": ["string"],
    "year": 2017,
    "arxiv_id": "string",
    "url": "string"
  },
  "core_bottleneck": {
    "prior_sota": "string",
    "failure_mode": "string",
    "mathematical_or_empirical_cause": "string",
    "urgency": "string"
  },
  "author_motivation_and_insight": {
    "compelling_observation": "string",
    "core_hypothesis": "string",
    "rejected_alternatives": [
      {
        "approach": "string",
        "why_it_falls_short": "string"
      }
    ]
  },
  "mechanism_of_action": {
    "intuition_summary": "string",
    "causal_steps": [
      {
        "step_title": "string",
        "mechanical_explanation": "string",
        "equation_translation": "string"
      }
    ]
  },
  "evidence_and_ablation": {
    "primary_claim_proven": "string",
    "ablation_findings": [
      {
        "experiment": "string",
        "result": "string",
        "causal_proof": "string"
      }
    ]
  },
  "tradeoffs_and_failure_modes": {
    "assumptions": ["string"],
    "compute_and_latency_costs": ["string"],
    "failure_modes": ["string"]
  },
  "slides": [
    {
      "slide_number": 1,
      "layout": "title | comparison | mechanism | figure_takeaway | evidence | tradeoffs",
      "title": "string",
      "key_takeaway": "string",
      "bullets": ["Max 12 words per bullet"],
      "left_column": {
        "heading": "Prior Bottleneck",
        "points": ["Max 12 words per point"]
      },
      "right_column": {
        "heading": "New Insight",
        "points": ["Max 12 words per point"]
      },
      "steps": [
        {
          "label": "1. Step Name",
          "detail": "Concise mechanical intuition (<= 16 words)"
        }
      ],
      "figure_path": "figures/page_03_vector_fig_01.png",
      "figure_caption": "string",
      "visual_suggestion": "string",
      "speaker_notes": "string"
    }
  ]
}
```

Notes on optional slide fields:
- Use `left_column` and `right_column` for `"comparison"` slides.
- Use `steps` (3–4 items) for `"mechanism"` slides.
- Use `figure_path` (relative to `workspace/`, matching a file in `workspace/figures/`) and `figure_caption` for `"figure_takeaway"` slides.
- All other fields (`slide_number`, `layout`, `title`, `key_takeaway`, `bullets`, `visual_suggestion`, `speaker_notes`) are required on every slide.
