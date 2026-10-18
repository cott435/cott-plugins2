"""A milestone build's state (build-phase.md §6, §10): files under `$(git rev-parse --git-common-dir)/dt-build/`,
reachable from the main checkout and every linked worktree, never committed.

    reserved/<id>.json     a half `dt ready --reserve` handed out, not claimed yet
    claims/<id>.json       a claimed half: task, role, worktree, branch, base, time, finished
    gates/<id>.json        the Stop gate's last verdict in that worktree: mode, passed, rc, tree
    escalations/<id>.json  why an agent stopped: kind, why
    rejects/<id>.json      a half's reject count, harness count and last reject
    resolved/<id>.json     the user's decision on a finding or a task (`dt build resolve`)
    reviews/<cp>.<pkg>.md  a reviewer's finding lines; `.json` the recorded outcome (`dt finding --from`)
    details/               what `dt land` saw, one file per land
    log.jsonl              append-only events
    land.lock              `dt land`'s lock

A builder half's id is `<task>.<role>` (`M1-T03.tester`); a review's is `<checkpoint>.<pkg>.reviewer`.

The tree hash of a worktree is the git tree id of its whole content as `git add -A` would stage it (tracked
files as they are on disk, untracked files that aren't ignored), written through a temporary index so the
worktree's own index is untouched. It is the same whether or not the agent committed.
"""
from __future__ import annotations

import contextlib
import fcntl
import fnmatch
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

KINDS = ("reserved", "claims", "gates", "escalations", "rejects", "resolved", "reviews", "details", "go")
ROLES = ("tester", "implementer", "solo")
ESCALATIONS = ("TEST-WRONG", "CONTRACT-CHANGE", "NEEDS-DEP")
TRAILER = "Dt-Landed"
# Files `dt claim` writes into a worktree; kept out of every diff through the shared info/exclude.
CLAIM_FILES = (".claude/packet.md", ".claude/.task_writes", ".claude/.check_pkg", ".claude/.dt",
               ".claude/.stop_attempts_*")
DT_PY = Path(__file__).resolve().parents[1] / "dt.py"


class GitError(RuntimeError):
    pass


def git(root: Path | str, *args: str, check: bool = True, env: dict | None = None,
        input: str | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
    """Run git in `root`; raise GitError (with stderr) when `check` and it fails."""
    try:
        res = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env=env,
                             input=input, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as e:
        raise GitError(f"git {' '.join(args)}: {e}") from e
    if check and res.returncode != 0:
        raise GitError(f"git {' '.join(args)}: {(res.stderr or res.stdout).strip()}")
    return res


def out(root, *args: str, **kw) -> str:
    return git(root, *args, **kw).stdout.strip()


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def real(path: str | Path) -> str:
    return os.path.realpath(str(path))


class State:
    """The `dt-build/` folder for the repository `root` belongs to (any of its checkouts)."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.common = Path(out(self.root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
        self.dir = self.common / "dt-build"

    # ---- records ------------------------------------------------------------------------------

    def path(self, kind: str, name: str = "") -> Path:
        return self.dir / kind / name if name else self.dir / kind

    def read(self, kind: str, rid: str) -> dict | None:
        try:
            return json.loads(self.path(kind, f"{rid}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def write(self, kind: str, rid: str, data: dict) -> Path:
        p = self.path(kind, f"{rid}.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(f".{p.name}.tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, p)
        return p

    def remove(self, kind: str, rid: str) -> bool:
        try:
            self.path(kind, f"{rid}.json").unlink()
            return True
        except FileNotFoundError:
            return False

    def all(self, kind: str) -> list[dict]:
        folder = self.path(kind)
        out_: list[dict] = []
        for p in sorted(folder.glob("*.json")) if folder.is_dir() else []:
            try:
                out_.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return out_

    def log(self, event: str, **fields) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": now(), "event": event, **fields}) + "\n")

    def events(self) -> list[dict]:
        try:
            lines = (self.dir / "log.jsonl").read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out_ = []
        for line in lines:
            with contextlib.suppress(ValueError):
                out_.append(json.loads(line))
        return out_

    def detail_file(self, rid: str) -> Path:
        folder = self.path("details")
        folder.mkdir(parents=True, exist_ok=True)
        n = len(list(folder.glob(f"{rid}-*.txt"))) + 1
        return folder / f"{rid}-{n}.txt"

    @contextlib.contextmanager
    def lock(self, timeout: float):
        """An exclusive flock on `dt-build/land.lock`; TimeoutError after `timeout` seconds."""
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "land.lock", "w") as f:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("another dt land holds dt-build/land.lock") from None
                    time.sleep(0.1)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    # ---- claims -------------------------------------------------------------------------------

    def claim_for(self, cwd: str | Path) -> dict | None:
        """The claim whose worktree is `cwd` or holds it (the deepest one)."""
        here = real(cwd)
        best = None
        for c in self.all("claims"):
            wt = real(c.get("worktree", ""))
            if here == wt or here.startswith(wt.rstrip(os.sep) + os.sep):
                if best is None or len(wt) > len(real(best["worktree"])):
                    best = c
        return best

    def in_flight(self) -> list[str]:
        """Reservations plus claims whose agent hasn't finished: what the concurrency cap counts."""
        return ([r["id"] for r in self.all("reserved")]
                + [c["id"] for c in self.all("claims") if not c.get("finished")])

    def exclude(self, patterns: list[str]) -> None:
        """Add patterns to the shared `info/exclude` (every worktree reads it) unless already there."""
        path = self.common / "info" / "exclude"
        path.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        have = set(text.splitlines())
        new = [p for p in patterns if p not in have]
        if new:
            sep = "" if not text or text.endswith("\n") else "\n"
            path.write_text(text + sep + "\n".join(new) + "\n", encoding="utf-8")


# ---- git views -----------------------------------------------------------------------------------

def is_main_checkout(root: Path | str) -> bool:
    return real(out(root, "rev-parse", "--path-format=absolute", "--git-dir")) == \
        real(out(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def toplevel(root: Path | str) -> Path:
    return Path(out(root, "rev-parse", "--show-toplevel"))


def main_checkout(root: Path | str) -> Path:
    """The main worktree's path (the first `git worktree list` entry)."""
    for line in out(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            return Path(line[len("worktree "):])
    return toplevel(root)


def head(root, short: bool = False) -> str:
    return out(root, "rev-parse", *(["--short"] if short else []), "HEAD")


def ref_exists(root, ref: str) -> bool:
    return git(root, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}", check=False).returncode == 0


def current_branch(root) -> str:
    """The checked-out branch name, or "HEAD" when detached."""
    return out(root, "rev-parse", "--abbrev-ref", "HEAD")


def tests_branch(task: str) -> str:
    return f"dt/{task}-tests"


def tree_hash(root: Path | str) -> str:
    """The tree id of the worktree's content as `git add -A` would stage it (see the module docstring)."""
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(d, "index")}
        git(root, "read-tree", "HEAD", env=env)
        git(root, "add", "-A", env=env)
        return out(root, "write-tree", env=env)


def changed_paths(root: Path | str, base: str) -> list[str]:
    """Paths that differ from `base`: committed, staged, unstaged, and untracked (not ignored)."""
    paths = out(root, "diff", "--name-only", "--no-renames", base).splitlines()
    paths += out(root, "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in paths if p})


def status_lines(root) -> list[str]:
    return [line for line in git(root, "status", "--porcelain").stdout.splitlines() if line]


def landings(root, rev: str = "HEAD") -> dict[str, dict]:
    """Task → {sha, role} for every `Dt-Landed: <task> <role>` trailer reachable from `rev` (newest wins)."""
    fmt = f"%H%x1f%(trailers:key={TRAILER},valueonly,separator=%x1e)%x1d"
    res = git(root, "log", f"--format={fmt}", rev, check=False)
    found: dict[str, dict] = {}
    for rec in res.stdout.split("\x1d") if res.returncode == 0 else []:
        if "\x1f" not in rec:
            continue
        sha, values = rec.strip("\n").split("\x1f", 1)
        for value in values.split("\x1e"):
            m = re.match(r"\s*(M\d+-T\d{2,})\s+(tester|implementer|solo)\b", value)
            if m and m.group(1) not in found:
                found[m.group(1)] = {"sha": sha.strip(), "role": m.group(2)}
    return found


# ---- paths and Writes ----------------------------------------------------------------------------

def _norm(path: str) -> tuple[str, bool]:
    p = path.strip().strip("`").removeprefix("./")
    for suffix in ("/**", "/*", "/"):
        if p.endswith(suffix):
            return p[: -len(suffix)] + "/", True
    return p, False


def covered(path: str, entries: list[str]) -> bool:
    """`path` is one of the Writes entries, or inside one that claims a folder (`dir/**`, `dir/*`, `dir/`)."""
    for e in entries:
        p, folder = _norm(e)
        if path == p.rstrip("/") or (folder and path.startswith(p)) or fnmatch.fnmatchcase(path, p):
            return True
    return False


def glob_match(path: str, globs: list[str]) -> bool:
    """check.sh / path_guard.sh semantics: `*` also matches `/`; case-insensitive."""
    low = path.lower()
    return any(fnmatch.fnmatchcase(low, g.strip().lower()) for g in globs if g.strip())


def role_writes(task, role: str) -> list[str]:
    """The role's share of the task's `Writes:`: tester the `tests/intent/` paths, implementer the rest, solo all."""
    intent = [w for w in task.writes if _norm(w)[0].startswith("tests/intent/")]
    if role == "tester":
        return intent
    if role == "implementer":
        return [w for w in task.writes if w not in intent]
    return list(task.writes)
