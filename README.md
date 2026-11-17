# Agent Skills

Consolidated collection of reusable Antigravity agent skills.

## Available Skills

- **`paper-insight-analyst/`** — First-principles architectural & motivational analysis of academic papers (`paper_text.md` → `insight_brief.json`).
- **`technical-deck-builder/`** — Validates `insight_brief.json` against slide density rules and renders a 16:9 PowerPoint deck (`.pptx`) via `scripts/render_pptx.py`.
- **`paper-to-code-blueprint/`** — Translates a paper's mechanism and equations into a minimal, runnable PyTorch/NumPy reference implementation with tensor-shape annotations and invariant tests.

## Installation

### Global (available in all workspaces)

```bash
cp -r paper-insight-analyst technical-deck-builder ~/.gemini/config/skills/
```

Or symlink them so `git pull` updates all workspaces automatically:

```bash
mkdir -p ~/.gemini/config/skills
ln -sfn "$(pwd)/paper-insight-analyst" ~/.gemini/config/skills/paper-insight-analyst
ln -sfn "$(pwd)/technical-deck-builder" ~/.gemini/config/skills/technical-deck-builder
```

### Project-local (checked into a specific repo)

```bash
mkdir -p /path/to/project/.agent/skills
cp -r paper-insight-analyst technical-deck-builder /path/to/project/.agent/skills/
```
