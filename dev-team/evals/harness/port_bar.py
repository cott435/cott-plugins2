#!/usr/bin/env python3
"""Port a planning-eval project's bar to build-setup's CURRENT templates, for a build eval on a real plan:
`port_bar.py <planning-project> <dest> [--plugin <plugin root>] [--json <file>]`.

A planning run ends at "planning done" (docs, an Approved tasks/plan.md with its Base, an Approved CONSTRAINTS.md,
a uv project), but its bar may come from an older build-setup. This clones the project's default branch into <dest>
(history kept, the branch renamed `main`, no remote back to the source) and re-renders the templates build-setup
regenerates whole: scripts/check.sh, check_size.py, floor_guard.sh/.py, red_check.py, scripts/hooks/*,
.claude/agents/{tester,implementer,reviewer}.md, .claude/settings.json (allow rules merged into any existing file),
the .gitignore additions (missing lines appended) and CONSTRAINTS.md (Status line kept, so it stays Approved).

Every `{{placeholder}}` value is read back from the project's own rendered files by aligning each with its current
template (difflib): check.sh (PROTECTED, SRC_DIRS, PACKAGES_DIR, TYPE_GATE, pkg_scope), tester.md (source globs),
CONSTRAINTS.md (dates, rules, boundaries, exceptions, measured values). The only derived values are the ones the
old templates had no slot for: `worktree_links` (gitignored entries beyond the template's, else `none`) and any
protected glob the current list requires that the old one lacks (the rule, not a project fact). pyproject.toml,
uv.lock, scripts/vulture_whitelist.py and tests/conftest.py are kept; the report lists what the current pyproject
template has that the project's lacks.

Then `uv sync`, commit "bar: current build-setup templates", `dt base` and commit, and check: `dt status --skill
build-setup`, `dt lint`, `scripts/check.sh gate` at the base, and the plan's shape. The report is printed (and
written as JSON with --json); `port(src, dest, plugin)` returns it (build_driver.py passes the staged plugin).
"""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
PH = re.compile(r"\{\{([a-z_]+)\}\}")
ALONE = re.compile(r"^\{\{([a-z_]+)\}\}$")
AGENTS = (".claude/agents/tester.md", ".claude/agents/implementer.md", ".claude/agents/reviewer.md")
SOURCES = ("scripts/check.sh", ".claude/agents/tester.md", "CONSTRAINTS.md")   # where placeholder values are read
LOOSE = (0, 1, 2)
KEEP = ("pyproject.toml", "uv.lock", "scripts/vulture_whitelist.py", "tests/conftest.py")


def load_bp(plugin: Path):
    """build-setup's template renderer (skills/build-setup/tests/project.py) from that copy of the plugin."""
    path = plugin / "skills" / "build-setup" / "tests" / "project.py"
    spec = importlib.util.spec_from_file_location(f"bp_port_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(cmd, cwd, check=False, timeout=1800, env=None) -> subprocess.CompletedProcess:
    e = dict(os.environ, NO_COLOR="1", **(env or {}))
    e.pop("VIRTUAL_ENV", None)
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, timeout=timeout, env=e)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(map(str, cmd))} (exit {r.returncode}):\n{(r.stdout + r.stderr)[-3000:]}")
    return r


def git(dest: Path, *a, check=True) -> str:
    return run(["git", *a], dest, check=check).stdout.strip()


# ---- reading placeholder values back ---------------------------------------------------------------------

def line_regex(tline: str, loose: int = 0) -> tuple[re.Pattern, list[str]]:
    """A template line as a regex, one group per placeholder. Looser levels keep less of the text after the last
    placeholder, so a line whose tail the template changed still yields its value: 1 its first 3 characters,
    2 its first character at the end of the line."""
    parts = PH.split(tline)              # literal, name, literal, name, …, literal
    names = parts[1::2]
    lits = parts[0::2]
    if loose:
        lits[-1] = lits[-1][:3] if loose == 1 else lits[-1][:1]
    rx = "".join(re.escape(lit) + ("(.*?)" if i < len(names) else "") for i, lit in enumerate(lits))
    return re.compile(rx + ("" if loose == 1 else "$")), names


def extract(template: str, rendered: str) -> tuple[dict[str, str], list[str]]:
    """Placeholder values of `rendered` (a file once made from an older version of `template`): the two are aligned
    line by line; inside each differing block, literal template lines anchor, a line with inline placeholders is
    matched as a regex, and a placeholder alone on its line takes every rendered line up to the next anchor.
    Returns (values, placeholders not found)."""
    t, o = template.splitlines(), rendered.splitlines()
    vals: dict[str, str] = {}
    sm = difflib.SequenceMatcher(None, t, o, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        tl, ol, cur = t[i1:i2], o[j1:j2], 0
        for k, line in enumerate(tl):
            alone = ALONE.match(line)
            if alone:
                nxt = tl[k + 1] if k + 1 < len(tl) else None
                end = len(ol)
                if nxt is not None:
                    for j in range(cur, len(ol)):
                        if anchor_hits(nxt, ol[j]):
                            end = j
                            break
                vals.setdefault(alone.group(1), "\n".join(ol[cur:end]))
                cur = end
                continue
            if not PH.search(line):
                for j in range(cur, len(ol)):
                    if ol[j] == line:
                        cur = j + 1
                        break
                continue
            for loose in LOOSE:
                rx, names = line_regex(line, loose)
                hit = next(((j, m) for j in range(cur, len(ol)) if (m := rx.match(ol[j]))), None)
                if hit:
                    j, m = hit
                    for n, v in zip(names, m.groups()):
                        vals.setdefault(n, v)
                    cur = j + 1
                    break
    missing = sorted(set(PH.findall(template)) - set(vals))
    return vals, missing


def anchor_hits(tline: str, oline: str) -> bool:
    if ALONE.match(tline):
        return False
    if not PH.search(tline):
        return tline == oline
    return any(line_regex(tline, loose)[0].match(oline) for loose in LOOSE)


# ---- values ----------------------------------------------------------------------------------------------

def gather(dest: Path, tpl: Path, bp) -> tuple[dict[str, str], dict]:
    notes: dict = {"read": {}, "derived": {}, "conflicts": [], "missing": []}
    vals: dict[str, str] = {}
    for rel in SOURCES:
        old = dest / rel
        if not old.exists():
            notes["missing"].append(f"{rel} (not in the project)")
            continue
        got, _missing = extract((tpl / rel).read_text(encoding="utf-8"), old.read_text(encoding="utf-8"))
        for k, v in got.items():
            if k in vals and vals[k] != v:
                notes["conflicts"].append(f"{k}: {vals[k]!r} ({notes['read'][k]}) vs {v!r} ({rel})")
                continue
            if k not in vals:
                vals[k] = v
                notes["read"][k] = rel
    # The Status line is kept whole (Approved stays Approved); its date and owner fill the template's slots.
    status = re.search(r"(?m)^\*\*Status:\*\*.*?\*\*Last reviewed:\*\*\s*(\S+)\s+by\s+(\S+)",
                       (dest / "CONSTRAINTS.md").read_text(encoding="utf-8") if (dest / "CONSTRAINTS.md").exists() else "")
    if status:
        for k, v in zip(("date", "owner"), status.groups()):
            vals.setdefault(k, v)
            notes["read"].setdefault(k, "CONSTRAINTS.md")
    # The protected list: the project's, plus any glob the current rule requires that it lacks.
    old_globs = re.findall(r"'([^']+)'", vals.get("protected_globs", ""))
    multi = bool(vals.get("packages_dir", "").strip())
    need = [*bp.PROTECTED, *(["packages/*/pyproject.toml"] if multi else [])]
    added = [g for g in need if g not in old_globs]
    if added or not old_globs:
        globs = old_globs + added
        vals["protected_globs"] = " ".join(f"'{g}'" for g in globs)
        vals["protected_globs_md"] = ", ".join(f"`{g}`" for g in globs)
        notes["derived"]["protected_globs"] = f"added {added} (required by the current Protected list)"
    if "protected_globs_md" not in vals:
        vals["protected_globs_md"] = ", ".join(f"`{g}`" for g in re.findall(r"'([^']+)'", vals["protected_globs"]))
        notes["derived"]["protected_globs_md"] = "from check.sh's PROTECTED (the same list)"
    md_globs = re.findall(r"`([^`]+)`", vals.get("protected_globs_md", ""))
    if set(md_globs) != set(re.findall(r"'([^']+)'", vals["protected_globs"])):
        notes["conflicts"].append(f"protected list: check.sh {old_globs} vs CONSTRAINTS.md {md_globs}")
    if "source_globs" not in vals:
        vals["source_globs"] = '"packages/*/src/**"' if multi else '"src/**"'
        notes["derived"]["source_globs"] = f"{vals['source_globs']} from the shape (no old tester.md line)"
    if "worktree_links" not in vals:
        extra = gitignore_extras(dest, tpl)
        vals["worktree_links"] = ", ".join(f"`{e}`" for e in extra) if extra else "none"
        notes["derived"]["worktree_links"] = (f"{vals['worktree_links']}: .gitignore entries beyond the template's"
                                              if extra else "none: .gitignore has nothing beyond the template's lines")
    return vals, notes


def gitignore_extras(dest: Path, tpl: Path) -> list[str]:
    ours = {ln.strip() for ln in (tpl / "gitignore.additions").read_text().splitlines()}
    path = dest / ".gitignore"
    lines = path.read_text().splitlines() if path.exists() else []
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#") and ln.strip() not in ours
            and not ln.startswith("!")]


# ---- rendering -------------------------------------------------------------------------------------------

def render_bar(dest: Path, tpl: Path, bp, vals: dict[str, str]) -> dict:
    written, unchanged = [], []
    old_constraints = (dest / "CONSTRAINTS.md").read_text(encoding="utf-8") if (dest / "CONSTRAINTS.md").exists() else ""

    def put(rel: str, text: str):
        p = dest / rel
        before = p.read_text(encoding="utf-8") if p.exists() else None
        if before == text:
            unchanged.append(rel)
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        written.append(rel)

    for rel in bp.SCRIPTS:
        if rel in KEEP:
            continue
        put(rel, bp.render((tpl / rel).read_text(encoding="utf-8"), vals))
        if rel.endswith(".sh"):
            (dest / rel).chmod(0o755)
    for rel in AGENTS:
        put(rel, bp.render((tpl / rel).read_text(encoding="utf-8"), vals))
    # settings.json: the template's allow rules merged into any existing file.
    new = json.loads((tpl / ".claude/settings.json").read_text())
    sp = dest / ".claude/settings.json"
    if sp.exists():
        cur = json.loads(sp.read_text())
        perms = cur.setdefault("permissions", {})
        perms.setdefault("defaultMode", new["permissions"]["defaultMode"])
        perms["allow"] = list(dict.fromkeys(perms.get("allow", []) + new["permissions"]["allow"]))
        new = cur
    put(".claude/settings.json", json.dumps(new, indent=2) + "\n")
    # .gitignore: the template's lines it lacks, appended.
    gi = dest / ".gitignore"
    have = gi.read_text(encoding="utf-8") if gi.exists() else ""
    present = {ln.strip() for ln in have.splitlines()}
    add = [ln for ln in (tpl / "gitignore.additions").read_text().splitlines()
           if ln.strip() and not ln.startswith("#") and ln.strip() not in present]
    if add:
        put(".gitignore", have.rstrip("\n") + "\n" + "\n".join(add) + "\n")
    # CONSTRAINTS.md: the current template, the project's values, its own Status line (Approved stays Approved).
    text = bp.render((tpl / "CONSTRAINTS.md").read_text(encoding="utf-8"), vals)
    old_status = next((ln for ln in old_constraints.splitlines() if ln.startswith("**Status:**")), None)
    if old_status:
        text = re.sub(r"(?m)^\*\*Status:\*\*.*$", lambda _m: old_status, text, count=1)
    put("CONSTRAINTS.md", text)
    diff = [ln for ln in difflib.unified_diff(old_constraints.splitlines(), text.splitlines(), lineterm="", n=0)
            if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    left = [f"{rel}: {sorted(set(PH.findall((dest / rel).read_text())))}" for rel in written
            if (dest / rel).suffix in (".sh", ".py", ".md", ".json") and PH.search((dest / rel).read_text())]
    return {"written": written, "unchanged": unchanged, "gitignore_added": add, "constraints_diff": diff,
            "placeholders_left": left}


def pyproject_gaps(dest: Path, tpl: Path, multi: bool) -> list[str]:
    """What the current pyproject template has that the project's lacks: dev tools and [tool.*] sections."""
    name = "pyproject.workspace.toml" if multi else "pyproject.toml"
    t = (tpl / name).read_text(encoding="utf-8")
    p = (dest / "pyproject.toml").read_text(encoding="utf-8")

    def dev(text):
        m = re.search(r"(?ms)^dev = \[(.*?)^\]", text)
        return set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()

    def heads(text):
        return {h for h in re.findall(r"(?m)^\[([^\]\[]+)\]\s*$", text) if h.startswith("tool.")}
    out = [f"dev dependency {d!r}" for d in sorted(dev(t) - dev(p))]
    out += [f"section [{h}]" for h in sorted(heads(PH.sub("x", t)) - heads(p))]
    return out


# ---- checks ----------------------------------------------------------------------------------------------

def plan_shape(text: str) -> dict:
    sys.path.insert(0, str(HERE))
    import grade_build  # noqa: E402
    plan = grade_build.parse_plan(text)
    tasks = plan["tasks"]

    def has(name):
        return sum(1 for b in re.split(r"(?m)^### ", text)[1:] if re.match(r"M\d+-T\d+:", b) and f"**{name}:**" in b)
    n = len(tasks)
    g = grade_build.graph_facts(plan)
    return {"tasks": n, "kind_field": f"{has('Kind')}/{n}", "mode_field": f"{has('Mode')}/{n}",
            "writes_field": f"{has('Writes')}/{n}", "depends_field": f"{has('Depends on')}/{n}",
            "kinds": {k: sum(t["kind"] == k for t in tasks) for k in sorted({t["kind"] for t in tasks})},
            "modes": {k: sum(t["mode"] == k for t in tasks) for k in sorted({t["mode"] for t in tasks})},
            "dependency_graph_rows": len(plan["graph"]),
            "dependency_graph_section": bool(re.search(r"(?m)^## Dependency graph", text)),
            "checkpoints": [c["title"] for c in plan["checkpoints"]],
            "barrier_checkpoint": any(c["barrier"] for c in plan["checkpoints"]),
            "exit_checkpoint": any(c["exit"] for c in plan["checkpoints"]),
            "waves": len(g["waves"]), "width": g["width"], "critical_path_tasks": g["cp_tasks"],
            "ready_after_interface": len(g["ready_after_interface"]), "split_tasks": len(g["split_tasks"])}


def checks(dest: Path, dt: Path, old_scope: str, skeleton: str | None = None) -> dict:
    out: dict = {}
    st = run([sys.executable, dt, "--root", dest, "status", "--skill", "build-setup", "--json"], dest)
    try:
        data = json.loads(st.stdout)
    except ValueError:
        st = run([sys.executable, dt, "--root", dest, "status", "--skill", "build-setup"], dest)
        data = {"raw": st.stdout[-3000:]}
    gaps = {k: v for k, v in data.items() if v and k not in ("mode", "blocked", "dependents", "docs", "next_ids",
                                                              "base", "constraints", "raw", "skill")}
    out["status"] = {"mode": data.get("mode"), "blocked": data.get("blocked"), "constraints": data.get("constraints"),
                     "base": data.get("base"), "gaps": gaps, "raw": data.get("raw")}
    deps = data.get("dependents") or {}
    scope = dict(re.findall(r'^\s*([\w.-]+)\) echo "([^"]*)"', old_scope, re.M))
    mism = [f"{k}: check.sh {sorted(scope.get(k, '').split())} vs dt {sorted({k, *v})}" for k, v in deps.items()
            if sorted(scope.get(k, "").split()) != sorted({k, *v})] if isinstance(deps, dict) else []
    out["pkg_scope_vs_dependents"] = mism or "match"
    lint = run([sys.executable, dt, "--root", dest, "lint", "--json"], dest)
    try:
        ld = json.loads(lint.stdout)
        probs = ld.get("problems") or []
        errs = [p for p in probs if p.get("severity") == "E"]
        out["lint"] = {"exit": lint.returncode, "errors": len(errs), "warnings": len(probs) - len(errs),
                       "error_lines": [" ".join(str(p.get(k, "")) for k in ("path", "line", "code", "message")).strip()
                                       for p in errs][:40]}
    except ValueError:
        out["lint"] = {"exit": lint.returncode, "errors": None, "raw": (lint.stdout + lint.stderr)[-2000:]}
    t0 = time.time()
    gate = run(["bash", "scripts/check.sh", "gate"], dest, timeout=1800)
    tail = (gate.stdout + gate.stderr).strip().splitlines()
    out["gate"] = {"exit": gate.returncode, "seconds": round(time.time() - t0, 1),
                   "failed_steps": [ln for ln in tail if re.search(r"FAIL|✗|error", ln, re.I)][:20], "tail": tail[-25:]}
    if gate.returncode and skeleton:
        out["gate_with_skeleton"] = skeleton_gate(dest, skeleton)
    return out


def skeleton_gate(dest: Path, init: str) -> dict:
    """The gate once the package module exists (what the interface task's first write gives it), in a probe that
    leaves the tree as it was: does anything else in the bar fail at the base?"""
    p = dest / init
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f'"""{p.parent.name}."""\n', encoding="utf-8")
    try:
        sync = run(["uv", "sync", "--frozen", "--quiet"], dest, timeout=3600)
        t0 = time.time()
        gate = run(["bash", "scripts/check.sh", "gate"], dest, timeout=1800)
        tail = (gate.stdout + gate.stderr).strip().splitlines()
        return {"module": init, "uv_sync_exit": sync.returncode, "exit": gate.returncode,
                "seconds": round(time.time() - t0, 1),
                "failed_steps": [ln for ln in tail if re.search(r"FAILED", ln)][:20], "tail": tail[-25:]}
    finally:
        p.unlink()
        try:
            p.parent.rmdir()
        except OSError:
            pass
        run(["uv", "sync", "--frozen", "--quiet", "--no-install-project"], dest, timeout=3600)


# ---- the port --------------------------------------------------------------------------------------------

def port(src: Path, dest: Path, plugin: Path = PLUGIN, gate: bool = True) -> dict:
    src, dest, plugin = Path(src).resolve(), Path(dest).resolve(), Path(plugin).resolve()
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"port_bar: {dest} is not empty")
    bp = load_bp(plugin)
    tpl = bp.TEMPLATES
    dt = plugin / "scripts" / "dt.py"
    branch = run(["git", "symbolic-ref", "--short", "HEAD"], src, check=True).stdout.strip()
    dirty = run(["git", "status", "--porcelain"], src).stdout.strip()
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "-q", "--no-hardlinks", "--single-branch", "--branch", branch, src, dest], dest.parent, check=True)
    git(dest, "remote", "remove", "origin")
    if branch != "main":
        git(dest, "branch", "-m", branch, "main")
    if not git(dest, "config", "user.email", check=False):
        git(dest, "config", "user.email", "eval@dev-team.local")
        git(dest, "config", "user.name", "dev-team eval")
    report: dict = {"source": str(src), "source_branch": branch, "source_head": git(dest, "rev-parse", "--short", "HEAD"),
                    "source_dirty": dirty.splitlines()[:10], "dest": str(dest), "branch": "main",
                    "plugin": str(plugin)}
    old_check = (dest / "scripts/check.sh").read_text() if (dest / "scripts/check.sh").exists() else ""
    vals, notes = gather(dest, tpl, bp)
    report["values"] = {"read": notes["read"], "derived": notes["derived"], "conflicts": notes["conflicts"],
                        "missing_sources": notes["missing"]}
    report["values_used"] = {k: vals[k] for k in ("protected_globs", "src_dirs", "packages_dir", "type_gate",
                                                  "source_globs", "worktree_links") if k in vals}
    needed = set()
    for rel in [*bp.SCRIPTS, *AGENTS, "CONSTRAINTS.md"]:
        if rel not in KEEP:
            needed |= set(PH.findall((tpl / rel).read_text(encoding="utf-8")))
    lacking = sorted(needed - set(vals))
    if lacking:
        raise SystemExit(f"port_bar: no value for {lacking} in the project's files (read: {sorted(vals)})")
    multi = bool(vals.get("packages_dir", "").strip())
    report["render"] = render_bar(dest, tpl, bp, vals)
    if report["render"]["placeholders_left"]:
        raise SystemExit(f"port_bar: placeholders left: {report['render']['placeholders_left']}")
    report["pyproject_gaps"] = pyproject_gaps(dest, tpl, multi)
    report["kept"] = [k for k in KEEP if (dest / k).exists()]

    # A planning project has no code yet: the interface task writes the package's __init__.py, so until it lands the
    # project itself can't be built. The venv then gets the dependencies and tools only (--no-install-project).
    src_dirs = vals.get("src_dirs", "src").split()
    report["package_modules"] = {d: sorted(str(p.relative_to(dest)) for p in (dest / d).glob("*/__init__.py"))
                                 for d in src_dirs}
    t0 = time.time()
    sync = run(["uv", "sync", "--frozen", "--quiet"], dest, timeout=3600)
    report["uv_sync"] = {"exit": sync.returncode, "seconds": round(time.time() - t0, 1),
                         "tail": (sync.stdout + sync.stderr).strip().splitlines()[-8:]}
    if sync.returncode:
        dep = run(["uv", "sync", "--frozen", "--quiet", "--no-install-project"], dest, timeout=3600)
        report["uv_sync"]["no_install_project"] = {"exit": dep.returncode, "seconds": round(time.time() - t0, 1),
                                                   "tail": (dep.stdout + dep.stderr).strip().splitlines()[-8:]}
    # The rendered Python is formatted to the project's own Ruff settings (its line length), as build-setup's
    # renderer does after rendering; nothing else is touched.
    py = [rel for rel in report["render"]["written"] if rel.endswith(".py")]
    ruff = dest / ".venv" / "bin" / "ruff"
    if py and ruff.exists():
        fmt = run([ruff, "format", "--quiet", *py], dest)
        report["render"]["formatted"] = {"files": py, "exit": fmt.returncode}
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "bar: current build-setup templates\n\nRe-rendered by port_bar.py from the "
        "project's own values; CONSTRAINTS.md stays Approved.")
    run([sys.executable, dt, "--root", dest, "base"], dest, check=True)
    git(dest, "commit", "-q", "-am", "M1: record the bar's base")
    report["base"] = git(dest, "rev-parse", "--short", "HEAD~1")
    report["head"] = git(dest, "rev-parse", "--short", "HEAD")
    plan_text = (dest / "tasks" / "plan.md").read_text(encoding="utf-8")
    report["plan_header"] = next((ln for ln in plan_text.splitlines() if ln.startswith("**Milestone:**")), "")
    report["plan"] = plan_shape(plan_text)
    m = re.search(r'pkg_scope\(\) \{\n\s*case "\$1" in\n(.*?)\n\s*\*\) return 1', old_check, re.S)
    skeleton = None
    if not multi and src_dirs == ["src"] and not report["package_modules"]["src"]:
        name = re.search(r'(?m)^name\s*=\s*"([^"]+)"', (dest / "pyproject.toml").read_text())
        skeleton = f"src/{name.group(1).replace('-', '_')}/__init__.py" if name else None
    report["checks"] = checks(dest, dt, m.group(1) if m else vals.get("pkg_scope_cases", ""), skeleton) if gate else {}
    report["clean"] = not git(dest, "status", "--porcelain")
    return report


def summary(r: dict) -> str:
    p, c = r["plan"], r.get("checks") or {}
    st = c.get("status") or {}
    lines = [f"port_bar: {r['source']} ({r['source_branch']} @ {r['source_head']}) -> {r['dest']} (main)",
             f"  rendered: {len(r['render']['written'])} files written, {len(r['render']['unchanged'])} unchanged; "
             f"gitignore +{len(r['render']['gitignore_added'])}; kept {', '.join(r['kept'])}",
             f"  values read from: {sorted(set(r['values']['read'].values()))}; derived: {r['values']['derived'] or 'none'}",
             f"  conflicts: {r['values']['conflicts'] or 'none'}; pyproject gaps vs template: {r['pyproject_gaps'] or 'none'}",
             f"  uv sync: exit {r['uv_sync']['exit']} in {r['uv_sync']['seconds']}s"
             + (f" ({r['uv_sync']['tail'][-1].strip()}; --no-install-project: exit "
                f"{r['uv_sync']['no_install_project']['exit']})" if "no_install_project" in r["uv_sync"] else "")
             + f"; package modules at base: {r['package_modules']}",
             f"  base {r['base']}, head {r['head']}, clean {r['clean']}",
             f"  plan: {r['plan_header']}",
             f"  plan shape: {p['tasks']} tasks; Kind {p['kind_field']}, Mode {p['mode_field']}, Writes {p['writes_field']}, "
             f"Depends {p['depends_field']}; kinds {p['kinds']}; modes {p['modes']}",
             f"  graph: section {p['dependency_graph_section']} ({p['dependency_graph_rows']} rows); {p['waves']} waves, "
             f"width {p['width']}, critical path {p['critical_path_tasks']}; {p['ready_after_interface']} ready after "
             f"the interface; checkpoints {p['checkpoints']} (barrier {p['barrier_checkpoint']}, exit {p['exit_checkpoint']})"]
    if c:
        lines += [f"  dt status --skill build-setup: mode {st.get('mode')}"
                  f"{(' (' + str(st.get('blocked')) + ')') if st.get('blocked') else ''}; CONSTRAINTS "
                  f"{st.get('constraints')}; base {st.get('base')}; gaps {st.get('gaps') or 'none'}",
                  f"  pkg_scope vs dt dependents: {c['pkg_scope_vs_dependents']}",
                  f"  dt lint: exit {c['lint']['exit']}, {c['lint'].get('errors')} errors, "
                  f"{c['lint'].get('warnings')} warnings"
                  + "".join(f"\n    {e}" for e in c["lint"].get("error_lines", [])[:15]),
                  f"  check.sh gate at base: exit {c['gate']['exit']} in {c['gate']['seconds']}s"
                  + "".join(f"\n    {e}" for e in (c["gate"]["failed_steps"] or c["gate"]["tail"][-3:])[:12])]
        sk = c.get("gate_with_skeleton")
        if sk:
            lines.append(f"  check.sh gate with only {sk['module']} added (a probe, not committed): exit {sk['exit']} "
                         f"in {sk['seconds']}s" + "".join(f"\n    {e}" for e in (sk["failed_steps"] or sk["tail"][-3:])[:12]))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project")
    ap.add_argument("dest")
    ap.add_argument("--plugin", default=str(PLUGIN))
    ap.add_argument("--json", help="also write the full report here")
    ap.add_argument("--no-gate", action="store_true", help="skip dt status, dt lint and check.sh gate")
    a = ap.parse_args(argv)
    r = port(Path(a.project), Path(a.dest), Path(a.plugin), gate=not a.no_gate)
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1))
    print(summary(r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
