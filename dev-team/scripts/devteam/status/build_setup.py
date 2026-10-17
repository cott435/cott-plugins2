"""`dt status --skill build-setup`: CONSTRAINTS.md vs pyproject.toml, the generated config vs the
architecture (`setup_checks`), agent and hook files, exceptions, tools and the `--pkg` dependents
(build-setup.md §9)."""
from __future__ import annotations

import os
import re
import shutil

from .. import md, model
from ..commands import roadmap as roadmap_cmd
from ..repo import Doc, Repo
from . import setup_checks as checks
from .common import Report, add_common, advance_ready, doc_state, fmt, plan_base
from .packages import dependency_graph, dependents
from .tomlread import load_toml

AGENT_ROLES = ("tester", "implementer", "reviewer")
SETUP_SCRIPTS = ("scripts/check.sh", "scripts/check_size.py", "scripts/floor_guard.sh", "scripts/floor_guard.py",
                 "scripts/hooks/path_guard.sh", "scripts/hooks/post_edit.sh", "scripts/hooks/stop_gate.sh",
                 "scripts/hooks/project_root.sh")


# ---- checks ------------------------------------------------------------------------------------

def _numbers(text: str) -> set[float]:
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(md.REQ_ID, " ", text)
    return {float(n) for n in re.findall(r"(?<![\w.])\d+(?:\.\d+)?", text)}


def _leaf_numbers(value) -> set[float]:
    if isinstance(value, bool):
        return set()
    if isinstance(value, (int, float)):
        return {float(value)}
    if isinstance(value, dict):
        out: set[float] = set()
        for v in value.values():
            out |= _leaf_numbers(v)
        return out
    return set()


def _fmt_num(n: float) -> str:
    return str(int(n)) if n == int(n) else str(n)


def _rules_with_keys(doc: Doc) -> list[tuple[str, str, set[float]]]:
    """(CR id, config key, numbers in its Rule/Today cell) for every CONSTRAINTS.md row naming a `tool.` key."""
    rows = []
    for _, head, trows in doc.tables():
        lower = [h.lower() for h in head]
        key_col = next((h for h in head if h.lower().startswith("config")), "")
        rule_col = next((head[i] for i, h in enumerate(lower) if h in ("rule", "today")), None)
        for _n, row in md.table_dicts(head, trows):
            rid = md.strip_md(row.get(head[0], ""))
            if not re.fullmatch(r"CR-\d{2,}", rid):
                continue
            keys = re.findall(r"`(tool\.[^`]+)`", row.get(key_col, "") or " ".join(row.values()))
            if keys:
                rows.append((rid, keys[0], _numbers(row.get(rule_col, "")) if rule_col else set()))
    return rows


def config_mismatches(repo: Repo) -> list[str]:
    """CONSTRAINTS.md table rows whose numbers differ from the config key they name in pyproject.toml."""
    rows = _rules_with_keys(repo.constraints) if repo.constraints else []
    if not rows:
        return []
    path = repo.root / "pyproject.toml"
    if not path.is_file():
        return [f"pyproject.toml missing ({len(rows)} rules name a config key)"]
    try:
        data = load_toml(path)
    except Exception as e:
        return [f"pyproject.toml unreadable ({e})"]
    out = []
    for rid, key, nums in rows:
        node = data
        for part in key.split("."):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                break
        if node is None:
            out.append(f"{rid}: {key} not set in pyproject.toml")
            continue
        found = _leaf_numbers(node)
        if not nums or not found:
            continue
        # A table (tool.size_limits) must hold every number the rule names; a scalar must be one of them.
        if not nums <= found if isinstance(node, dict) else not found <= nums:
            out.append(f"{rid}: CONSTRAINTS.md {', '.join(_fmt_num(n) for n in sorted(nums))} vs "
                       f"{key} = {', '.join(_fmt_num(n) for n in sorted(found))}")
    return out


def setup_scripts(repo: Repo) -> list[str]:
    """The hook and check scripts build-setup writes, plus any `scripts/…` an agent file names."""
    scripts = list(SETUP_SCRIPTS)
    for a in AGENT_ROLES:
        f = repo.root / ".claude" / "agents" / f"{a}.md"
        if f.is_file():
            scripts += re.findall(r"scripts/[\w./-]+\.(?:sh|py)", f.read_text(encoding="utf-8", errors="replace"))
    return list(dict.fromkeys(scripts))


# ---- report ------------------------------------------------------------------------------------

def build_setup(repo: Repo, r: Report) -> None:
    active = roadmap_cmd.active_plan(repo)
    constraints = repo.constraints
    if not active:
        r.mode("blocked", "no active plan in tasks/plan.md (run build-planning)")
    elif (active.status or "") == "Draft":
        r.mode("blocked", "tasks/plan.md is Draft, not Approved")
    elif constraints is None:
        r.mode("new")
    elif advance_ready(repo, active):
        ratcheted = md.strip_md(constraints.header.get("Ratcheted", ""))
        r.mode("ratchet" if ratcheted != model.milestone_of(active) else "current")
    elif plan_base(active) == "pending":
        r.mode("extend")       # kickoff: the bar isn't approved and recorded (`dt base`) for this plan yet
    else:
        r.mode("current")
    add_common(repo, r)
    pyproject = checks.read_pyproject(repo.root / "pyproject.toml")
    graph = dependency_graph(repo)
    r.add("constraints", doc_state(constraints))
    r.add("config_mismatches", config_mismatches(repo))
    for key, value in (("contract_mismatches", checks.contract_mismatches(pyproject, graph)),
                       ("optional_layers_existing", checks.optional_layers_existing(repo, pyproject)),
                       ("deptry_missing", checks.deptry_missing(repo, pyproject)),
                       ("protected_gaps", checks.protected_gaps(repo)),
                       ("ignores_without_exception", checks.ignores_without_exception(repo, pyproject))):
        r.add(key, "unknown" if value is None else value)
    agents = repo.root / ".claude" / "agents"
    r.add("agents_missing", [a for a in AGENT_ROLES if not (agents / f"{a}.md").is_file()])
    scripts = setup_scripts(repo)
    r.add("hooks_missing", [s for s in scripts if not (repo.root / s).is_file()])
    r.add("not_executable", [s for s in scripts if s.endswith(".sh") and (repo.root / s).is_file()
                             and not os.access(repo.root / s, os.X_OK)])
    r.add("expired_exceptions", checks.expired_exceptions(repo))
    r.add("tools_missing", [t for t in ("uv", "jq") if shutil.which(t) is None])
    deps = dependents(graph)
    r.add("dependents", deps, fmt([f"{k}<-{','.join(v)}" for k, v in deps.items()]))
    r.add("base", plan_base(active))
