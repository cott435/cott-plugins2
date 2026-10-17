#!/usr/bin/env bash
# Run trajectories in parallel, then grade, measure and package them.
#
# Usage: evals/harness/run.sh <iteration-name> [trajectory-id ...]
#   default trajectories: rl-incremental rl-all-at-once quant-incremental quant-all-at-once
# Env: EVAL_WS (default: ../dev-team-workspace next to the marketplace repo), plus driver.py's
#      (PLUGIN_SRC, SKILLS_SRC, AGENT_MODEL, USER_MODEL, COST_CAP_USD, CLAUDE_BIN).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
ws="${EVAL_WS:-$(cd "$here/../../../.." && pwd)/dev-team-workspace}"
iter="${1:?usage: run.sh <iteration-name> [trajectory-id ...]}"
shift
trajs=("$@")
[ ${#trajs[@]} -gt 0 ] || trajs=(rl-incremental rl-all-at-once quant-incremental quant-all-at-once)
mkdir -p "$ws/$iter"

for t in "${trajs[@]}"; do
  python3 "$here/driver.py" "$t" "$ws/$iter/$t/with_skill" > "$ws/$iter/$t.log" 2>&1 &
  echo "started $t (log: $ws/$iter/$t.log)"
done
wait

for t in "${trajs[@]}"; do
  run="$ws/$iter/$t/with_skill"
  python3 "$here/grade.py" "$run" | head -1 || true
  python3 "$here/docstats.py" "$run/project/docs" > "$ws/$iter/$t.docstats.json" || true
done
EVAL_WS="$ws" python3 "$here/package.py" "$iter"
