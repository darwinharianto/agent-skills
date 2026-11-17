# Agent Skills

Consolidated collection of cross-agent skills following the open `SKILL.md` convention (compatible with Antigravity/Gemini, Claude Code, and OpenAI Codex).

## Available Skills

### Paper-to-Deck Pipeline (`bundles/paper-to-deck.txt`)
- **`paper-to-deck/`** — End-to-end orchestrator chaining the 4 deck skills in order.
- **`paper-insight-analyst/`** — First-principles architectural & motivational analysis (`paper_text.md` → `insight_brief.json`).
- **`svg-illustrator/`** — Generates quantitative SVG data visualizations and rasterizes them to PNGs.
- **`technical-deck-builder/`** — Validates `insight_brief.json` and renders a 16:9 PowerPoint deck (`.pptx`) via `scripts/render_pptx.py`.
- **`deck-reviewer/`** — Runs SVG word-density audit and 5-point visual QA on rasterized slides.

### General Engineering & Research
- **`paper-to-code-blueprint/`** — Translates a paper's mechanism and equations into a minimal, runnable PyTorch/NumPy reference implementation with tensor-shape annotations and invariant tests.
- **`pr-review-checklist/`** — Audits git diffs and PRs for correctness, edge cases, security, scope, and test verification before committing.
- **`skill-author/`** — Enforces `agent-skills` conventions (portable paths, `requirements.txt`, trigger descriptions, and verification steps) when creating or updating skills.

## Installation

Use `./install.sh` to symlink a bundle or single skill into any project or global agent directory:

```bash
# Link the full 5-skill paper-to-deck bundle into a project (Antigravity)
./install.sh paper-to-deck /path/to/project --target antigravity

# Link using the universal .agents/skills standard (Codex + Antigravity)
./install.sh paper-to-deck /path/to/project --target universal

# Link for Claude Code
./install.sh paper-to-deck /path/to/project --target claude

# Link globally across all workspaces (--global)
./install.sh pr-review-checklist --global --target universal
```
