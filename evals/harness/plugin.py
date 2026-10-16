#!/usr/bin/env python3
"""Stage the dev-team2 plugin for one run, the way a real project gets it: the whole plugin (manifest,
hooks, scripts, skills), loaded with `claude --plugin-dir`. Skills call `../../scripts/dt.py` relative to
their own folder and hooks call `${CLAUDE_PLUGIN_ROOT}/scripts/dt.py`; both only resolve in a whole-plugin
install, never when skills are copied into a project's .claude/skills/.

Usage: plugin.py <dest-dir>   stages <dest-dir>/dev-team2, checks it, prints problems (exit 1 if any)

Env: PLUGIN_SRC (plugin root; default: this repo), SKILLS_SRC (optional: overlay these skill folders over the
plugin's, e.g. an older skill snapshot for an A/B run), CLAUDE_BIN (for `claude plugin validate`).
"""
import json, os, re, shutil, subprocess, sys, pathlib

HERE = pathlib.Path(__file__).resolve().parent
PLUGIN_SRC = pathlib.Path(os.environ.get("PLUGIN_SRC", HERE.parents[1]))
SKILLS_SRC = os.environ.get("SKILLS_SRC")
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")
PARTS = [".claude-plugin", "hooks", "scripts", "skills"]
JUNK = {"__pycache__", ".DS_Store", ".pytest_cache"}


def _ignore(src, names):
    # dt's own unit tests and fixtures aren't part of an install; build-setup's templates/tests is.
    skip = {n for n in names if n in JUNK or n.endswith(".pyc")}
    if pathlib.Path(src).resolve() == (PLUGIN_SRC / "scripts").resolve():
        skip.add("tests")
    return skip


def stage(dest):
    """Copy the plugin to <dest>/dev-team2 and return that path."""
    root = pathlib.Path(dest) / "dev-team2"
    if root.exists():
        shutil.rmtree(root)
    for part in PARTS:
        shutil.copytree(PLUGIN_SRC / part, root / part, ignore=_ignore)
    if SKILLS_SRC:
        for s in sorted(pathlib.Path(SKILLS_SRC).iterdir()):
            if (s / "SKILL.md").exists():
                shutil.rmtree(root / "skills" / s.name, ignore_errors=True)
                shutil.copytree(s, root / "skills" / s.name, ignore=_ignore)
    return root


def check(root, validate=True):
    """Problems with a staged plugin: dt paths that don't resolve, a dt that doesn't start, a failed validate."""
    root = pathlib.Path(root)
    problems = []
    for skill in sorted((root / "skills").iterdir()):
        md = skill / "SKILL.md"
        if not md.exists():
            continue  # a skill another branch hasn't written yet
        for rel in sorted(set(re.findall(r"(\.\./\.\./scripts/[\w./-]+\.py)", md.read_text()))):
            if not (skill / rel).resolve().exists():
                problems.append(f"{skill.name}: {rel} does not resolve")
    hooks = json.loads((root / "hooks" / "hooks.json").read_text())
    for cmd in re.findall(r'"command":\s*"((?:[^"\\]|\\.)*)"', json.dumps(hooks)):
        for rel in re.findall(r"CLAUDE_PLUGIN_ROOT}/([\w./-]+)", cmd.replace("\\", "")):
            if not (root / rel).exists():
                problems.append(f"hooks.json: {rel} missing")
    r = subprocess.run([sys.executable, str(root / "scripts" / "dt.py"), "--help"], capture_output=True, text=True)
    if r.returncode != 0:
        problems.append(f"dt.py --help failed: {r.stderr.strip()[-300:]}")
    if validate and shutil.which(CLAUDE_BIN):
        r = subprocess.run([CLAUDE_BIN, "plugin", "validate", str(root)], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            problems.append(f"claude plugin validate: {(r.stdout + r.stderr).strip()[-500:]}")
    return problems


def skills_missing(root):
    """Skill folders staged without a SKILL.md (work in progress elsewhere)."""
    return sorted(p.name for p in (pathlib.Path(root) / "skills").iterdir() if p.is_dir() and not (p / "SKILL.md").exists())


if __name__ == "__main__":
    root = stage(sys.argv[1])
    probs = check(root)
    for s in skills_missing(root):
        print(f"warning: skills/{s} has no SKILL.md")
    print("\n".join(probs) or f"ok: {root}")
    sys.exit(1 if probs else 0)
