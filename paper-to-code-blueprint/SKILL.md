---
name: paper-to-code-blueprint
description: Use this skill when translating an academic paper (paper_text.md or insight_brief.json) into a minimal, runnable PyTorch/NumPy reference implementation with tensor-shape annotations and invariant tests.
---

# Paper-to-Code Blueprint

You are a principal ML systems engineer. Your job is to translate a paper's core mechanism (from `insight_brief.json` and/or `paper_text.md`, defaulting to `workspace/` if present) into a **minimal, self-contained, runnable reference implementation** and **invariant test suite**.

## Core Directive: No Hand-Wavy Pseudocode

**EXPLICITLY FORBIDDEN:**
- Placeholder comments (`# TODO`, `...`, `pass`) inside core architectural or mathematical blocks.
- Unannotated tensor reshapes/transposes where dimension semantics are unclear.
- Ignoring edge cases like masking, scaling factors, initialization schemes, or weight tying.

**REQUIRED:**
Every core equation in the paper's mechanism must map 1-to-1 to executable code with explicit symbolic tensor-shape comments and automated invariant tests.

---

## Step 1: Extract the Implementation Spec

Read the available inputs (`insight_brief.json` for causal steps & equations, `paper_text.md` for exact dimensions, initialization, and edge-case details):

1. **Symbolic Dimension Legend:** Define single-letter dimension symbols at the top of the file (e.g., `B`: batch, `N`: sequence length, `D`: `d_model`, `H`: num heads, `d_k`: head dim).
2. **Hyperparameter Config:** Create a `@dataclass` holding both the paper's **base config** and a **tiny CPU test config**.
3. **Core Modules Only:** Implement the novel mechanism(s) cleanly without training-loop boilerplate (unless the training objective itself is the paper's core contribution).

---

## Step 2: Write the Reference Blueprint

Create the target implementation file (e.g., `blueprint.py` or `<paper_slug>_blueprint.py` in the user-specified output path or `workspace/`):

- **Framework:** Use PyTorch (`torch.nn`) by default, or NumPy/JAX if requested.
- **Shape Annotations:** Annotate every tensor transformation inline:
  ```python
  # q, k, v: (B, N, D) -> (B, H, N, d_k)
  ```
- **Equation Traceability:** Tag key lines with the paper section/equation (e.g., `# Sec 3.2.1, Eq. (1): scale by 1/sqrt(d_k)`).
- **Initialization & Numerical Stability:** Include critical details (e.g., zero-init of LoRA `B`, `1/sqrt(d_k)` variance scaling, `-inf` or `-1e9` masking before softmax).

---

## Step 3: Write & Run Invariant Tests

Create a companion test script (e.g., `test_<paper_slug>_blueprint.py`) covering **all three** invariant classes:

1. **Shape & Dynamic-Axis Invariance:** Verify output shapes across multiple `(B, N)` combinations.
2. **Paper-Specific Mathematical / Causality Invariants:**
   - *Autoregressive / Causal models:* Perturbing token `t+1` must produce `0.0` change in outputs at positions `<= t`.
   - *Adapter / Residual methods (e.g., LoRA):* Output at initialization must equal the frozen base layer output.
   - *Normalization / Scaling:* Verify variance or probability-sum invariants (`sum(attn, dim=-1) == 1.0`).
3. **Gradient Flow Check:** Run `.backward()` on a dummy scalar loss and assert all trainable parameters receive finite, non-NaN gradients.

Run the test suite in the active Python environment and confirm all checks pass before reporting completion.
