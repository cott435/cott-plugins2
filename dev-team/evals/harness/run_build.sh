#!/usr/bin/env bash
# Build eval: every arm on one target, n replicates, one run at a time (never in parallel: concurrent runs
# would share rate limits and bias wall clock, interface-first-design.md §9.2). The arm order rotates per
# replicate (A0 A1 A2 … then A1 A2 … A0), so no arm always runs first or last.
#
# Usage: evals/harness/run_build.sh <iteration-name> [target] [arm ...]
#   default target: minilab; default arms: every non-optional arm in scenarios.json (A0–A4; add A5 by name)
# Env: EVAL_WS (default: ../dev-team-workspace next to the marketplace repo), REPLICATES (default: the
#      target's `replicates`, 3), plus build_driver.py's (CLAUDE_BIN, FAKE_MODE, AGENT_MODEL, COST_CAP_USD,
#      MAX_TURNS, PRESSURE, PLUGIN_SRC, SKILLS_SRC).
# Output: $EVAL_WS/<iteration>/<target>-<arm>-r<n>/with_skill/ per run (grading.json, flow/), and
#         $EVAL_WS/<iteration>/build_summary.json, one row per run.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
ws="${EVAL_WS:-$(cd "$here/../../../.." && pwd)/dev-team-workspace}"
iter="${1:?usage: run_build.sh <iteration-name> [target] [arm ...]}"
target="${2:-minilab}"
shift $(( $# >= 2 ? 2 : 1 ))
arms=("$@")
if [ ${#arms[@]} -eq 0 ]; then
  read -r -a arms <<<"$(python3 -c "import json,sys; d=json.load(open('$here/scenarios.json')); print(' '.join(k for k, v in d['arms'].items() if not v.get('optional')))")"
fi
reps="${REPLICATES:-$(python3 -c "import json; print(json.load(open('$here/scenarios.json'))['build_targets']['$target'].get('replicates', 3))")}"
mkdir -p "$ws/$iter"
n=${#arms[@]}

for ((r = 1; r <= reps; r++)); do
  for ((i = 0; i < n; i++)); do
    arm="${arms[$(( (i + r - 1) % n ))]}"
    run="$ws/$iter/$target-$arm-r$r/with_skill"
    echo "replicate $r: $arm → $run"
    REPLICATE="$r" python3 "$here/build_driver.py" "$target" "$arm" "$run" > "$ws/$iter/$target-$arm-r$r.log" 2>&1 \
      || echo "  build_driver exited $? (see the log); grading what is there"
    python3 "$here/grade_build.py" "$run" --quiet || true
  done
done

python3 - "$ws/$iter" "$target" <<'EOF'
import json, pathlib, sys
it, target = pathlib.Path(sys.argv[1]), sys.argv[2]
rows = []
for g in sorted(it.glob(f"{target}-*-r*/with_skill/grading.json")):
    d, s = json.loads(g.read_text()), json.loads((g.parent / "summary.json").read_text())
    vals = {e["id"]: e.get("value", e["passed"]) for e in d["expectations"]}
    rows.append({"run": g.parent.parent.name, "arm": s.get("arm"), "replicate": s.get("replicate"),
                 "stop": s.get("stop_reason"), "wall_s": s.get("total_seconds"), "cost_usd": s.get("agent_cost_usd"),
                 "pass_rate": d["summary"]["pass_rate"], "harness_failures": d["harness_summary"]["failures"], **vals})
(it / "build_summary.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['run']}: {r['stop']}, {r['wall_s']}s, ${r['cost_usd']}, design pass {r['pass_rate']}, harness {r['harness_failures'] or 'ok'}")
EOF
# The iteration's flow pages (every run with a transcript): $ws/$iter/runflow/index.html
EVAL_WS="$ws" python3 "$here/runviz.py" "$iter" || echo "runviz failed: no flow pages (the eval itself is fine)"
