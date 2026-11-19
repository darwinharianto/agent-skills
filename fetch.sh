#!/usr/bin/env bash
set -euo pipefail

REPO="darwinharianto/agent-skills"
REF="main"
TARGET="universal"
PROJECT_DIR="."
GLOBAL=false
FORCE=false
LIST_ONLY=false
SOURCE_DIR=""
RULE_OUT=""

ITEMS=()
RULES=()
TMP_DIR=""

cleanup() {
  if [[ -n "${TMP_DIR:-}" && -d "${TMP_DIR:-}" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

usage() {
  cat <<'EOF'
Usage:
  fetch.sh <bundle-or-skill>... [options]
  curl -fsSL https://raw.githubusercontent.com/darwinharianto/agent-skills/main/fetch.sh | bash -s -- <bundle-or-skill>... [options]

Examples:
  # List available bundles, skills, and rules
  curl -fsSL https://raw.githubusercontent.com/darwinharianto/agent-skills/main/fetch.sh | bash -s -- --list

  # Fetch only the observability bundle into the current project (.agents/skills/)
  curl -fsSL https://raw.githubusercontent.com/darwinharianto/agent-skills/main/fetch.sh | bash -s -- observability

  # Pick specific skills + a rule for Claude Code
  curl -fsSL https://raw.githubusercontent.com/darwinharianto/agent-skills/main/fetch.sh | bash -s -- arch-mapper pr-review-checklist --rule observable-code --target claude

  # Install globally for Antigravity (~/.gemini/config/skills/)
  curl -fsSL https://raw.githubusercontent.com/darwinharianto/agent-skills/main/fetch.sh | bash -s -- observability --global --target antigravity

Options:
  --target <name>     universal (default), antigravity, claude, or codex
  --dir <path>        Target project root directory (default: .)
  --global            Install skills into the user-global skills directory
  --rule <name>       Install rule from rules/<name>.md (repeatable)
  --rule-out <path>   Explicit output file path for --rule
  --force             Overwrite an existing rule file
  --list              List available bundles, skills, and rules
  --repo <owner/repo> GitHub repository (default: darwinharianto/agent-skills)
  --ref <branch/tag>  Git branch or tag (default: main)
  --source <dir>      Use a local checkout instead of downloading from GitHub
  -h, --help          Show this help message
EOF
}

require_arg() {
  if [[ $# -lt 2 || -z "${2:-}" ]]; then
    echo "Error: option '$1' requires an argument." >&2
    exit 1
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      require_arg "$@"
      TARGET="$2"
      shift 2
      ;;
    --dir)
      require_arg "$@"
      PROJECT_DIR="$2"
      shift 2
      ;;
    --global)
      GLOBAL=true
      shift
      ;;
    --rule)
      require_arg "$@"
      RULES+=("$2")
      shift 2
      ;;
    --rule-out)
      require_arg "$@"
      RULE_OUT="$2"
      shift 2
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --list)
      LIST_ONLY=true
      shift
      ;;
    --repo)
      require_arg "$@"
      REPO="$2"
      shift 2
      ;;
    --ref)
      require_arg "$@"
      REF="$2"
      shift 2
      ;;
    --source)
      require_arg "$@"
      SOURCE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      ITEMS+=("$1")
      shift
      ;;
  esac
done

if [[ "$LIST_ONLY" == false && ${#ITEMS[@]} -eq 0 && ${#RULES[@]} -eq 0 ]]; then
  usage >&2
  exit 1
fi

case "$TARGET" in
  universal|codex)
    if [[ "$GLOBAL" == true ]]; then
      DEST_DIR="$HOME/.agents/skills"
    else
      DEST_DIR="$PROJECT_DIR/.agents/skills"
    fi
    DEFAULT_RULE_FILE="$PROJECT_DIR/AGENTS.md"
    ;;
  antigravity)
    if [[ "$GLOBAL" == true ]]; then
      DEST_DIR="$HOME/.gemini/config/skills"
    else
      DEST_DIR="$PROJECT_DIR/.agent/skills"
    fi
    DEFAULT_RULE_FILE="$PROJECT_DIR/GEMINI.md"
    ;;
  claude)
    if [[ "$GLOBAL" == true ]]; then
      DEST_DIR="$HOME/.claude/skills"
    else
      DEST_DIR="$PROJECT_DIR/.claude/skills"
    fi
    DEFAULT_RULE_FILE="$PROJECT_DIR/CLAUDE.md"
    ;;
  *)
    echo "Unsupported target: $TARGET (expected universal, antigravity, claude, or codex)" >&2
    exit 1
    ;;
esac

if [[ -n "$SOURCE_DIR" ]]; then
  if [[ ! -d "$SOURCE_DIR" ]]; then
    echo "Error: --source directory does not exist: $SOURCE_DIR" >&2
    exit 1
  fi
  SRC_ROOT="$(cd "$SOURCE_DIR" && pwd)"
else
  TMP_DIR="$(mktemp -d)"
  TAR_URL="https://github.com/${REPO}/archive/refs/heads/${REF}.tar.gz"
  curl -fsSL "$TAR_URL" | tar -xz -C "$TMP_DIR"
  SRC_ROOT="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)"
  if [[ -z "$SRC_ROOT" || ! -d "$SRC_ROOT" ]]; then
    echo "Error: failed to extract repository archive from $TAR_URL" >&2
    exit 1
  fi
fi

list_catalog() {
  echo "Bundles:"
  if [[ -d "$SRC_ROOT/bundles" ]]; then
    while IFS= read -r bfile; do
      bname="$(basename "$bfile" .txt)"
      bskills=()
      while IFS= read -r line; do
        line="${line%%#*}"
        line="${line// /}"
        [[ -n "$line" ]] && bskills+=("$line")
      done < "$bfile"
      echo "  - $bname: ${bskills[*]:-}"
    done < <(find "$SRC_ROOT/bundles" -maxdepth 1 -type f -name '*.txt' | sort)
  fi

  echo ""
  echo "Skills:"
  while IFS= read -r sfile; do
    sname="$(basename "$(dirname "$sfile")")"
    echo "  - $sname"
  done < <(find "$SRC_ROOT" -mindepth 2 -maxdepth 2 -type f -name 'SKILL.md' | sort)

  echo ""
  echo "Rules:"
  if [[ -d "$SRC_ROOT/rules" ]]; then
    while IFS= read -r rfile; do
      rname="$(basename "$rfile" .md)"
      echo "  - $rname"
    done < <(find "$SRC_ROOT/rules" -maxdepth 1 -type f -name '*.md' | sort)
  fi
}

if [[ "$LIST_ONLY" == true ]]; then
  list_catalog
  exit 0
fi

# Resolve bundles and individual skills into a deduplicated ordered list.
SKILLS=()
add_skill_unique() {
  local candidate="$1"
  local existing
  for existing in "${SKILLS[@]+"${SKILLS[@]}"}"; do
    if [[ "$existing" == "$candidate" ]]; then
      return 0
    fi
  done
  SKILLS+=("$candidate")
}

for item in "${ITEMS[@]+"${ITEMS[@]}"}"; do
  bundle_file="$SRC_ROOT/bundles/$item.txt"
  if [[ -f "$bundle_file" ]]; then
    while IFS= read -r line; do
      line="${line%%#*}"
      line="${line// /}"
      if [[ -n "$line" ]]; then
        if [[ ! -f "$SRC_ROOT/$line/SKILL.md" ]]; then
          echo "Error: skill '$line' listed in bundle '$item' was not found." >&2
          exit 1
        fi
        add_skill_unique "$line"
      fi
    done < "$bundle_file"
  elif [[ -f "$SRC_ROOT/$item/SKILL.md" ]]; then
    add_skill_unique "$item"
  else
    echo "Error: '$item' is neither a bundle in bundles/ nor a skill with SKILL.md." >&2
    exit 1
  fi
done

if [[ ${#SKILLS[@]} -gt 0 ]]; then
  mkdir -p "$DEST_DIR"
  for skill in "${SKILLS[@]}"; do
    rm -rf "$DEST_DIR/$skill"
    cp -R "$SRC_ROOT/$skill" "$DEST_DIR/$skill"
    echo "Installed skill: $skill -> $DEST_DIR/$skill"
  done
fi

if [[ ${#RULES[@]} -gt 0 ]]; then
  if [[ "$GLOBAL" == true && -z "$RULE_OUT" ]]; then
    echo "Error: --global with --rule requires --rule-out <path> (or omit --global to write to $DEFAULT_RULE_FILE)." >&2
    exit 1
  fi

  RULE_DEST="${RULE_OUT:-$DEFAULT_RULE_FILE}"

  # Deduplicate rules while preserving order and verify all exist first.
  UNIQUE_RULES=()
  for raw_rule in "${RULES[@]}"; do
    rname="${raw_rule%.md}"
    if [[ ! -f "$SRC_ROOT/rules/$rname.md" ]]; then
      echo "Error: rule '$raw_rule' not found at rules/$rname.md." >&2
      exit 1
    fi
    already=false
    for existing in "${UNIQUE_RULES[@]+"${UNIQUE_RULES[@]}"}"; do
      if [[ "$existing" == "$rname" ]]; then
        already=true
        break
      fi
    done
    if [[ "$already" == false ]]; then
      UNIQUE_RULES+=("$rname")
    fi
  done

  if [[ -e "$RULE_DEST" && "$FORCE" != true ]]; then
    echo "Error: rule destination '$RULE_DEST' already exists. Re-run with --force to overwrite." >&2
    exit 1
  fi

  mkdir -p "$(dirname "$RULE_DEST")"
  if [[ ${#UNIQUE_RULES[@]} -eq 1 ]]; then
    cp "$SRC_ROOT/rules/${UNIQUE_RULES[0]}.md" "$RULE_DEST"
    echo "Installed rule: ${UNIQUE_RULES[0]} -> $RULE_DEST"
  else
    : > "$RULE_DEST"
    first=true
    for rname in "${UNIQUE_RULES[@]}"; do
      if [[ "$first" == false ]]; then
        printf "\n---\n\n" >> "$RULE_DEST"
      fi
      cat "$SRC_ROOT/rules/$rname.md" >> "$RULE_DEST"
      first=false
      echo "Installed rule: $rname -> $RULE_DEST"
    done
  fi
fi
