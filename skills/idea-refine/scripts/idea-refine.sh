#!/bin/bash
set -e

# Detects whether idea-refine should run in "new" or "extend" mode.
# Ensures docs/ exists and reports the state of docs/brief.md, docs/spec.md,
# and each idea file in docs/ideas/ as JSON.

DOCS_DIR="${1:-docs}"
BRIEF="$DOCS_DIR/brief.md"
SPEC="$DOCS_DIR/spec.md"
IDEAS_DIR="$DOCS_DIR/ideas"

mkdir -p "$DOCS_DIR"

status_of() {
  # Prints the value after "**Status:**" (e.g. Draft, Accepted, Specced), or "unknown".
  local s
  s=$(grep -m1 -o '\*\*Status:\*\* *[A-Za-z]*' "$1" 2>/dev/null | sed 's/\*\*Status:\*\* *//')
  echo "${s:-unknown}"
}

if [ -f "$BRIEF" ]; then
  MODE="extend"; BRIEF_EXISTS=true; BRIEF_STATUS=$(status_of "$BRIEF")
  BRIEF_WORDS=$(wc -w < "$BRIEF" | tr -d ' ')
  mkdir -p "$IDEAS_DIR"
else
  MODE="new"; BRIEF_EXISTS=false; BRIEF_STATUS="none"; BRIEF_WORDS=0
fi

if [ -f "$SPEC" ]; then
  SPEC_EXISTS=true; SPEC_STATUS=$(status_of "$SPEC")
else
  SPEC_EXISTS=false; SPEC_STATUS="none"
fi

IDEAS=""
if [ -d "$IDEAS_DIR" ]; then
  for f in "$IDEAS_DIR"/*.md; do
    [ -e "$f" ] || continue
    entry="{\"path\": \"$f\", \"status\": \"$(status_of "$f")\"}"
    IDEAS="${IDEAS:+$IDEAS, }$entry"
  done
fi

echo "Mode: $MODE (brief: $BRIEF_STATUS, spec: $SPEC_STATUS)" >&2
echo "{\"mode\": \"$MODE\", \"brief\": {\"path\": \"$BRIEF\", \"exists\": $BRIEF_EXISTS, \"status\": \"$BRIEF_STATUS\", \"words\": $BRIEF_WORDS}, \"spec\": {\"path\": \"$SPEC\", \"exists\": $SPEC_EXISTS, \"status\": \"$SPEC_STATUS\"}, \"ideas\": [$IDEAS]}"
