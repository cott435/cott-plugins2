#!/bin/bash
set -e

# Reports what spec-writing needs before it starts, as JSON:
#   - mode: "new" (no docs/spec.md) or "extend"
#   - brief and spec status
#   - idea files and their status; "ready" lists ideas that are Accepted (waiting to be specced)
#   - for each requirement prefix in the spec (e.g. SAVE, QR, DATA): the highest ID used and the next free one
# IDs are never reused, so "next" counts removed (struck-through) requirements too.

DOCS_DIR="${1:-docs}"
BRIEF="$DOCS_DIR/brief.md"
SPEC="$DOCS_DIR/spec.md"
IDEAS_DIR="$DOCS_DIR/ideas"

status_of() {
  local s
  s=$(grep -m1 -o '\*\*Status:\*\* *[A-Za-z]*' "$1" 2>/dev/null | sed 's/\*\*Status:\*\* *//')
  echo "${s:-unknown}"
}

if [ ! -f "$BRIEF" ]; then
  echo "No $BRIEF — run idea-refine first." >&2
  echo "{\"mode\": \"blocked\", \"reason\": \"no brief\"}"
  exit 0
fi
BRIEF_STATUS=$(status_of "$BRIEF")

if [ -f "$SPEC" ]; then
  MODE="extend"; SPEC_STATUS=$(status_of "$SPEC")
  IDS=$(grep -o '\*\*[A-Z][A-Z0-9]*-[0-9][0-9]*\*\*' "$SPEC" | tr -d '*' \
    | awk -F- '{n=$2+0; if(!($1 in m)||n>m[$1]) m[$1]=n} END{for(k in m) printf "%s\"%s\": {\"highest\": \"%s-%02d\", \"next\": \"%s-%02d\"}", (c++?", ":""), k, k, m[k], k, m[k]+1}')
else
  MODE="new"; SPEC_STATUS="none"; IDS=""
fi

IDEAS=""; READY=""
if [ -d "$IDEAS_DIR" ]; then
  for f in "$IDEAS_DIR"/*.md; do
    [ -e "$f" ] || continue
    st=$(status_of "$f")
    IDEAS="${IDEAS:+$IDEAS, }{\"path\": \"$f\", \"status\": \"$st\"}"
    [ "$st" = "Accepted" ] && READY="${READY:+$READY, }\"$f\""
  done
fi

echo "Mode: $MODE (brief: $BRIEF_STATUS, spec: $SPEC_STATUS)" >&2
echo "{\"mode\": \"$MODE\", \"brief\": {\"path\": \"$BRIEF\", \"status\": \"$BRIEF_STATUS\"}, \"spec\": {\"path\": \"$SPEC\", \"status\": \"$SPEC_STATUS\"}, \"ideas\": [$IDEAS], \"ready\": [$READY], \"ids\": {$IDS}}"
