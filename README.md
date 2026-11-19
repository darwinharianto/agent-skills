# Agent Skills

Consolidated collection of cross-agent skills following the open `SKILL.md` convention (compatible with Antigravity/Gemini, Claude Code, and OpenAI Codex).

## Available Skills

### Paper-to-Deck Pipeline (`bundles/paper-to-deck.txt`)
- **`paper-to-deck/`** — End-to-end orchestrator chaining the 4 deck skills in order.
- **`paper-insight-analyst/`** — First-principles architectural & motivational analysis (`paper_text.md` → `insight_brief.json`).
- **`svg-illustrator/`** — Generates quantitative SVG data visualizations and rasterizes them to PNGs.
- **`technical-deck-builder/`** — Validates `insight_brief.json` and renders a 16:9 PowerPoint deck (`.pptx`) via `scripts/render_pptx.py`.
- **`deck-reviewer/`** — Runs SVG word-density audit and 5-point visual QA on rasterized slides.

### Observability & Code Understanding (`bundles/observability.txt`)
- **`arch-mapper/`** — Maps an unfamiliar codebase or new feature into a 1-page `ARCHITECTURE.md` with a Mermaid data-flow diagram, entry points, typed boundaries, and state ownership.
- **`trace-walkthrough/`** — Traces a concrete input, request, or user action end-to-end with exact `file:line` hops, data transformations, and failure boundaries.

### General Engineering & Research
- **`paper-to-code-blueprint/`** — Translates a paper's mechanism and equations into a minimal, runnable PyTorch/NumPy reference implementation with tensor-shape annotations and invariant tests.
- **`pr-review-checklist/`** — Audits git diffs and PRs for correctness, edge cases, security, scope, and test verification before committing.
- **`skill-author/`** — Enforces `agent-skills` conventions (portable paths, `requirements.txt`, trigger descriptions, and verification steps) when creating or updating skills.

## Reusable Rules

- **`rules/observable-code.md`** — Standalone cross-agent rule enforcing contracts-first design, linear top-level orchestration, typed boundaries, inspectable state, and end-of-task data-flow traces.

Copy or symlink it into any project root (or global config):

```bash
# Universal (Antigravity + OpenAI Codex)
ln -sfn /path/to/agent-skills/rules/observable-code.md /path/to/project/AGENTS.md

# Antigravity project rule
ln -sfn /path/to/agent-skills/rules/observable-code.md /path/to/project/GEMINI.md

# Claude Code project rule
ln -sfn /path/to/agent-skills/rules/observable-code.md /path/to/project/CLAUDE.md
```

## Installation

Use `./install.sh` to symlink a bundle or single skill into any project or global agent directory:

```bash
# Link the full 5-skill paper-to-deck bundle into a project (Antigravity)
./install.sh paper-to-deck /path/to/project --target antigravity

# Link the observability skills (arch-mapper + trace-walkthrough) universally
./install.sh observability /path/to/project --target universal

# Link using the universal .agents/skills standard (Codex + Antigravity)
./install.sh paper-to-deck /path/to/project --target universal

# Link for Claude Code
./install.sh paper-to-deck /path/to/project --target claude

# Link globally across all workspaces (--global)
./install.sh pr-review-checklist --global --target universal
```
