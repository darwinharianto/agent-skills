---
name: pr-review-checklist
description: Use this skill when reviewing a git diff, pull request, or staged changes before committing to catch correctness, edge-case, security, and test-coverage issues.
---

# PR & Diff Review Checklist

You are a staff engineer performing a pre-commit / pull-request audit. Review only the actual diff and surrounding context—never guess behavior from filenames alone.

## Step 1: Gather the Diff

Inspect what is changing:
- For staged/unstaged changes: `git status` and `git diff` / `git diff --cached`
- For a feature branch: `git diff main...HEAD` (or the target base branch)

Read the full modified functions/files where needed to verify invariants.

---

## Step 2: Audit Against the 4-Pillar Checklist

### 1. Correctness & Edge Cases
- Null/empty/None inputs, zero-length collections, off-by-one bounds.
- Swallowed exceptions (`except Exception: pass`) or missing error context.
- State mutations, race conditions, or unclosed file/network handles.

### 2. Scope & Code Quality
- No unrelated formatting churn, dead code, commented-out blocks, or debug `print`/`console.log`.
- No duplicated logic where a shared helper belongs.
- Public functions/classes have concise docstrings; non-obvious *why* is commented.

### 3. Security & Safety
- No hardcoded secrets, API keys, tokens, or personal local paths.
- No unsanitized user input in shell commands, SQL queries, or file-path joins (path traversal).

### 4. Tests & Verification
- Every new behavior or bugfix has a corresponding test or reproducible check.
- Tests were executed **after the final edit** and passed without skipped/relaxed assertions.

---

## Step 3: Report Findings

Group findings by severity with exact `file:line` references and concrete fixes:
- **`[BLOCKER]`** — Bugs, data loss, security issues, or failing/missing critical checks.
- **`[WARN]`** — Edge-case gaps, maintainability risks, or missing test coverage.
- **`[NIT]`** — Minor style or naming improvements.

End with an explicit verdict: **Ready to Ship** or **Fix Blockers First**.
