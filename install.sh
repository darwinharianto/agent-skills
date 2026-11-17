#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./install.sh <bundle-or-skill> [project-dir] [--target universal|antigravity|claude|codex] [--global]

Examples:
  ./install.sh paper-to-deck /home/darwin/paper-to-deck --target antigravity
  ./install.sh paper-to-deck /path/to/repo --target universal
  ./install.sh paper-to-deck --global --target claude
  ./install.sh pr-review-checklist --global --target universal

Targets:
  universal (default)  .agents/skills   (or ~/.agents/skills with --global)
  antigravity          .agent/skills    (or ~/.gemini/config/skills with --global)
  claude               .claude/skills   (or ~/.claude/skills with --global)
  codex                .agents/skills   (or ~/.agents/skills with --global)
EOF
}

if [[ $# -lt 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

ITEM="$1"
shift

PROJECT_DIR=""
TARGET="universal"
GLOBAL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --global)
      GLOBAL=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      if [[ -z "$PROJECT_DIR" ]]; then
        PROJECT_DIR="$1"
        shift
      else
        echo "Unknown argument: $1" >&2
        exit 1
      fi
      ;;
  esac
done

if [[ "$GLOBAL" == false && -z "$PROJECT_DIR" ]]; then
  PROJECT_DIR="$(pwd)"
fi

case "$TARGET" in
  universal|codex)
    DEST_DIR=$([[ "$GLOBAL" == true ]] && echo "$HOME/.agents/skills" || echo "$PROJECT_DIR/.agents/skills")
    ;;
  antigravity)
    DEST_DIR=$([[ "$GLOBAL" == true ]] && echo "$HOME/.gemini/config/skills" || echo "$PROJECT_DIR/.agent/skills")
    ;;
  claude)
    DEST_DIR=$([[ "$GLOBAL" == true ]] && echo "$HOME/.claude/skills" || echo "$PROJECT_DIR/.claude/skills")
    ;;
  *)
    echo "Unsupported target: $TARGET (expected universal, antigravity, claude, or codex)" >&2
    exit 1
    ;;
esac

SKILLS=()
BUNDLE_FILE="$REPO_DIR/bundles/$ITEM.txt"
if [[ -f "$BUNDLE_FILE" ]]; then
  while IFS= read -r line; do
    line="${line%%#*}"
    line="${line// /}"
    [[ -n "$line" ]] && SKILLS+=("$line")
  done < "$BUNDLE_FILE"
elif [[ -d "$REPO_DIR/$ITEM" && -f "$REPO_DIR/$ITEM/SKILL.md" ]]; then
  SKILLS+=("$ITEM")
else
  echo "Error: '$ITEM' is neither a bundle in bundles/ nor a skill folder with SKILL.md." >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
for skill in "${SKILLS[@]}"; do
  src="$REPO_DIR/$skill"
  if [[ ! -f "$src/SKILL.md" ]]; then
    echo "Warning: skipping missing skill '$skill' ($src/SKILL.md not found)" >&2
    continue
  fi
  ln -sfn "$src" "$DEST_DIR/$skill"
  echo "Linked $skill -> $DEST_DIR/$skill"
done
