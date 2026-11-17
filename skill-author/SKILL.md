---
name: skill-author
description: Use this skill when creating or updating a reusable agent skill in agent-skills so it follows portable path, dependency, frontmatter, and verification conventions.
---

# Skill Author

Use this checklist whenever creating a new skill or refactoring an existing one in `agent-skills` so every skill is self-contained and portable across workspaces.

## Step 1: Directory Layout

Create a lowercase, hyphenated folder at the repo root:

```text
<skill-name>/
├── SKILL.md            # Required
├── requirements.txt    # Required if scripts/ import third-party packages
├── scripts/            # Optional deterministic CLI helpers
└── references/         # Optional bulky docs/schemas (loaded on demand)
```

---

## Step 2: Frontmatter & Trigger Rules

Start `SKILL.md` with valid YAML frontmatter:
- `name`: Must match `<skill-name>` exactly.
- `description`: Must use third-person trigger phrasing (`"Use this skill when..."`) stating both **what** it does and **when** to activate it.

---

## Step 3: Enforce Portability

1. **No hardcoded skill paths:** Never write `.agent/skills/<skill-name>/...` in commands—link scripts relatively (`./scripts/foo.py`) or refer to `<skill-dir>/scripts/foo.py` so the skill works both globally (`~/.gemini/config/skills/`) and project-locally (`.agent/skills/`).
2. **No hardcoded project directories:** Scripts and instructions must accept `--input` / `--output` (or user-specified paths). Project conventions like `workspace/` may only be used as fallback defaults.
3. **Self-contained dependencies:** Any Python/Node package imported by `scripts/` must be declared in `<skill-name>/requirements.txt` (or `package.json`) with a Prerequisites note in `SKILL.md`.

---

## Step 4: Structure & Verification

Every `SKILL.md` must include:
1. **Core Directive / Anti-Patterns:** Explicitly state what is forbidden (e.g., surface-level summaries, `# TODO` placeholders).
2. **Step-by-Step Workflow:** Clear, numbered execution steps.
3. **Verification Step:** How the agent confirms success before finishing (e.g., `--validate-only`, running unit tests, checking output files).

Before committing to `agent-skills`:
- Add a one-line entry for the new skill in `README.md`.
- Test any scripts (`--help` or dry-run) to confirm they run cleanly.
