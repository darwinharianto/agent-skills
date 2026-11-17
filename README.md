# Agent Skills

Consolidated collection of reusable Antigravity agent skills.

## Available Skills

- **`paper-insight-analyst/`** — First-principles architectural & motivational analysis of academic papers (`workspace/paper_text.md` → `workspace/insight_brief.json`).
- **`technical-deck-builder/`** — Validates `workspace/insight_brief.json` against slide density rules and renders a 16:9 PowerPoint deck (`workspace/output_deck.pptx`) via `scripts/render_pptx.py`.

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
