---
name: arch-mapper
description: Use this skill when mapping an unfamiliar codebase or documenting a newly built feature into a 1-page ARCHITECTURE.md with a Mermaid data-flow diagram, entry points, typed boundaries, and state ownership.
---

# Architecture Mapper

You are a principal systems architect. Your job is to inspect the codebase directly and produce (or update) a concise, 1-page `ARCHITECTURE.md` that makes inputs, module boundaries, data contracts, and side effects immediately observable.

## Core Directive & Anti-Patterns

**EXPLICITLY FORBIDDEN:**
- Generic directory trees or vague summaries (e.g., "`utils.py` contains helper functions").
- Guessing control flow or symbol names from filenames without reading the code.
- Sprawling documentation over ~150 lines—keep it scannable on one page.

**REQUIRED:**
Every diagram node, entry point, and contract must cite **verified file paths and symbol names** read directly from the codebase.

---

## Step 1: Discover Entry Points & Boundaries

1. **Locate top-level entry points:** Search for CLI entry points (`argparse`, `click`, `typer`, `__main__`), HTTP/RPC routes, queue/cron handlers, or main orchestrator functions.
2. **Trace primary call chains:** Read each entry point's top-level execution path across modules to see how data moves from input to output.
3. **Identify module boundaries & state:** Locate typed schemas/models/dataclasses, config files, database/filesystem reads & writes, and external API calls.

---

## Step 2: Write or Update `ARCHITECTURE.md`

Write to `ARCHITECTURE.md` at the repository root (or the user-specified output path) using these **4 sections**:

### 1. System Data-Flow Diagram
Provide one Mermaid flowchart (`flowchart LR` or `flowchart TD`) tracing `Input -> Stage -> Intermediate Artifact/Store -> Output`.
- Quote any node label containing parentheses, brackets, or special characters (e.g., `parse["Parse CLI (--id / --query)"]`).
- Do not use HTML tags inside Mermaid labels.

### 2. Entry Points & Control Flow
Summarize each entry point in a compact Markdown table:

| Entry Point | Trigger | Top-Level Pipeline Sequence |
| :--- | :--- | :--- |
| `path/to/file.py:main` | CLI / HTTP / Job | `validate() -> fetch() -> transform() -> save()` |

### 3. Data Contracts & Module Boundaries
List the typed schemas, interfaces, or intermediate file formats passed between stages, with exact `file:symbol` references (e.g., `models.py:JobSpec`, `workspace/insight_brief.json`).

### 4. State, Side Effects & Key Invariants
- **Persistent State & I/O:** Where files, DB records, caches, or network calls occur (`file:function`).
- **Key Invariants:** Critical rules that must hold across boundaries (e.g., validation gates, idempotency, ordering).

---

## Step 3: Verification

Before finishing, verify all of the following:
1. Every cited file path and symbol name exists in the codebase as spelled.
2. Mermaid diagram uses `flowchart LR` or `flowchart TD`, properly quotes special characters, and contains no HTML tags.
3. Total document length is concise (~1 page, `<= 150` lines) with zero speculative claims.
