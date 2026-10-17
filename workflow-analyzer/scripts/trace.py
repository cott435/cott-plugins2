#!/usr/bin/env python3
"""Rebuild what a Claude Code session actually did from its transcripts.

A session is one `<session>.jsonl` under `~/.claude/projects/<project>/`, plus one
`<session>/subagents/agent-<id>.jsonl` (and `.meta.json`) per agent spawned in it, at any
depth. This script reads them and writes a trace: who ran, what each was sent, every tool call
in order with its key input and whether it failed, every hook that blocked, every commit, and
what each agent handed back. Any session works; `--plugin NAME` additionally splits the main
thread into segments at each `/NAME:<command>` and points each agent at its definition.

It judges nothing; this is the evidence.

It lives beside `flow.py`, which draws the chart and the unit and turn pages, `charts.py`, the
timeline, token bars and files matrix, and `compare.py`, which sets two or more built runs
side by side.

Every build records:
  turns    the main thread split at each prompt the user (or an eval's simulated user) sent:
           one loop each, with its duration, tokens, tool calls, skills, the units it spawned,
           and every file it or its units read, wrote or edited. `turns/T<nn>.json` and
           `turns/T<nn>.html` hold each one's full steps.
  units    one per spawned agent: `units/U<nn>.json|.md|.html`.
  tokens   per unit and per turn, from each API response's usage: fresh input, cache writes,
           cache reads, output, and the largest context any one request carried.
  files    `file_ops` per unit and turn: Read/Write/Edit calls, plus reads and writes a Bash
           command shows plainly (`cat`, `head`, `sed -n`, `>`, `>>`, `tee`), marked `via: Bash`.

A session is named by a .jsonl path, a session id (or unique prefix), `latest` (the newest
session other than the one running this script, $CLAUDE_CODE_SESSION_ID), or words from the
chat's title as the app shows it (case-insensitive; all must match exactly one session).
`--project TEXT` narrows `latest`, title words and `find` to sessions whose working directory
contains TEXT.

Workspaces default to `$RUN_FLOW_HOME/<project>/<id8>/` (`~/.claude/run-flow/` unless set),
`<project>` the name of the session's working directory with any `.claude/worktrees/<name>`
suffix removed. Nothing is written anywhere else.

Usage:
  trace.py find [--plugin NAME] [--project TEXT] [--words W...] [--limit N] [--all]
      Sessions newest first, each with its title, project, branch, span, agent count and the
      slash commands typed. With --plugin, only sessions that used NAME's commands or agents.
      --all includes headless runs in temp dirs (eval harnesses).
  trace.py ws SESSION [--project TEXT]
      Print the default workspace for SESSION. Creates nothing.
  trace.py build SESSION [--plugin NAME] [--project TEXT] [--out DIR] [--full]
      Writes DIR/run.md, DIR/index.json, DIR/driver/seg-<n>.md (with --plugin),
      DIR/units/U<nn>.{md,json,html,system.md}, DIR/turns/T<nn>.{json,html}, and
      DIR/flow.html, the run as a page. DIR defaults to the session's workspace.
      --full raises every truncation limit fivefold.
  trace.py flow DIR
      Re-render DIR/flow.html and the unit and turn pages from DIR/index.json.
  trace.py view --agent TYPE (--sessions a,b | --branch GLOB) [--plugin NAME] [--root DIR] [--flat]
      Every run of one agent type across several sessions. Each session is built into its
      workspace under DIR (default $RUN_FLOW_HOME; DIR/<id8>/ with --flat, as plugin-dev's
      audit workspaces are laid out), then DIR/views/<type>-<YYYY-MM-DD>.html
      lists every unit of TYPE in time order. TYPE matches a unit's role (`profiler`) or its
      full type (`dev-team:profiler`), ignoring case. --branch takes every session (of NAME,
      with --plugin) whose git branch matches GLOB.

Step ids are stable across rebuilds of the same transcript: `D<n>` in the main thread,
`U<nn>.S<n>` inside a unit, `T<nn>` for turns. Units are numbered by first timestamp. A rebuild
while the session is still running appends new units and steps without renumbering old ones.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flow  # noqa: E402

PROJECTS = Path(os.environ.get("AUDIT_RUN_PROJECTS") or Path.home() / ".claude" / "projects")
RUNS = Path(os.environ.get("RUN_FLOW_HOME") or Path.home() / ".claude" / "run-flow")
LIMITS = {"text": 600, "cmd": 500, "err": 800, "out": 400, "arg": 200}

CMD_RE = re.compile(r"<command-name>/?([^<]+)</command-name>")
ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)
BASE_RE = re.compile(r"Base directory for this skill: (\S+)")
HANDBACK_RE = re.compile(r'<agent-message from="([^"]+)">')
TASK_RE = re.compile(r"<task-id>([^<]+)</task-id>.*?<status>([^<]*)</status>", re.S)
COMMIT_RE = re.compile(r"^\[([^\s\]]+)(?: \(root-commit\))? ([0-9a-f]{7,40})\] (.*)$", re.M)
ONELINE_RE = re.compile(r"^([0-9a-f]{7,40}) (.+)$", re.M)


def clip(s: str, kind: str) -> str:
    s = (s or "").strip()
    n = LIMITS[kind]
    return s if len(s) <= n else s[:n] + f" …[+{len(s) - n} chars]"


def tail(s: str, kind: str) -> str:
    s = (s or "").strip()
    n = LIMITS[kind]
    return s if len(s) <= n else f"…[{len(s) - n} chars] " + s[-n:]


def one_line(s: str) -> str:
    return " ⏎ ".join(x for x in (s or "").strip().splitlines() if x.strip())


def load(path: Path) -> list[dict]:
    out = []
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


# ---------------------------------------------------------------- session discovery


TS_RE = re.compile(r'"timestamp":\s*"(\d{4}-\d\d-\d\dT[^"]+)"')


def title_of(text: str) -> str:
    """The chat's name as the app shows it: the last title set by hand or by the app, else the
    last title Claude generated, else the first thing typed."""
    for key in ("customTitle", "aiTitle"):
        hits = re.findall(rf'"{key}":\s*"((?:[^"\\]|\\.)*)"', text)
        if hits:
            return json.loads(f'"{hits[-1]}"')
    m = re.search(r'"lastPrompt":\s*"((?:[^"\\]|\\.)*)"', text)
    return json.loads(f'"{m.group(1)}"')[:60] if m else "(untitled)"


def local(ts: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
    except ValueError:
        return None


def describe(s: dict) -> str:
    """Two lines per session: id and title, then where, when, how long, how big."""
    start, end = local(s["first_ts"]), local(s["last_ts"])
    if start and end:
        mins = int((end - start).total_seconds() // 60)
        same_day = start.date() == end.date()
        span = (f"{start:%Y-%m-%d %H:%M} → {end:%H:%M}" if same_day else f"{start:%Y-%m-%d %H:%M} → {end:%m-%d %H:%M}")
        span += f" ({mins // 60}h{mins % 60:02d}m)"
    else:
        span = dt.datetime.fromtimestamp(s["mtime"]).strftime("%Y-%m-%d %H:%M")
    live = " · still active" if dt.datetime.now().timestamp() - s["mtime"] < 120 else ""
    uniq = list(dict.fromkeys(f"/{c}" for c in s["commands"]))
    cmds = (", ".join(uniq[:6]) + (f" +{len(uniq) - 6}" if len(uniq) > 6 else "")) or "—"
    where = s["cwd"].replace(str(Path.home()), "~") + (f" · {s['branch']}" if s.get("branch") else "")
    at = local(s.get("fork_at", ""))
    fork = (f"\n    fork of {s['fork_of'][:8]}: its history up to {at:%m-%d %H:%M} is a copy of that chat's"
            if s.get("fork_of") and at else "")
    return (f"{s['id']}  \"{s['title']}\"\n"
            f"    {where} · {span} · {s['spawns']} agent{'' if s['spawns'] == 1 else 's'} · commands: {cmds}{live}{fork}")


def headless(cwd: str) -> bool:
    """Eval harnesses run Claude headless in temp dirs; those runs never appear in the app."""
    return cwd.startswith(("/private/tmp/", "/tmp/", "/private/var/folders/", "/var/folders/"))


GENERIC_DIRS = {"project", "repo", "workspace", "app", "src", "with_skill", "without_skill", "old_skill"}


def project_name(cwd: str) -> str:
    """The project a working directory belongs to: its name, with `.claude/worktrees/<x>` dropped."""
    if not cwd or cwd == "?":
        return "unknown-project"
    parts = Path(re.sub(r"/\.claude/worktrees/[^/]+/?$", "", cwd.rstrip("/"))).parts
    # A generic leaf (an eval harness's `<iteration>/<trajectory>/with_skill/project`) borrows its parents.
    n = 1
    while n < min(4, len(parts) - 1) and parts[-n] in GENERIC_DIRS:
        n += 1
    return "-".join(parts[-n:]) or "unknown-project"


def current_session() -> str | None:
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or None


def session_facts(f: Path, text: str, plugin: str | None) -> dict:
    """What `find` shows about one transcript: title, where, when, commands typed, agents spawned."""
    cmds, spawns, uuids = [], 0, []
    for line in text.splitlines():
        if '"uuid"' in line and (m := re.search(r'"uuid":\s*"([^"]+)"', line)):
            t = TS_RE.search(line)
            uuids.append((m.group(1), t.group(1) if t else ""))
        if "<command-name>" not in line and "subagent_type" not in line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (r.get("message") or {}).get("content")
        if r.get("type") == "user" and isinstance(content, str) and (m := CMD_RE.search(content)):
            if plugin is None or m.group(1).startswith(f"{plugin}:"):
                cmds.append(m.group(1))  # typed, not quoted inside a tool's output
        elif r.get("type") == "assistant" and isinstance(content, list):
            spawns += sum(1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use"
                          and b.get("name") in ("Agent", "Task")
                          and (plugin is None
                               or str((b.get("input") or {}).get("subagent_type", "")).startswith(f"{plugin}:")))
    cwd = re.search(r'"cwd":\s*"([^"]+)"', text)
    branch = re.search(r'"gitBranch":\s*"((?:[^"\\]|\\.)*)"', text)
    stamps = TS_RE.findall(text)
    st = f.stat()
    return {
        "path": f,
        "id": f.stem,
        "cwd": cwd.group(1) if cwd else "?",
        "branch": json.loads(f'"{branch.group(1)}"') if branch else None,
        "mtime": st.st_mtime,
        "commands": cmds,
        "spawns": spawns,
        "title": title_of(text),
        "first_ts": min(stamps) if stamps else "",
        "last_ts": max(stamps) if stamps else "",
        "uuids": uuids,
        "born": getattr(st, "st_birthtime", st.st_mtime),
        "own_agents": len(list((f.with_suffix("") / "subagents").glob("agent-*.jsonl"))),
    }


def sessions_for(plugin: str | None, include_headless: bool = False, project: str | None = None) -> list[dict]:
    """Every session (with a plugin, every one that used its commands or agents), newest first.
    `project` keeps those whose working directory contains it."""
    needle_a, needle_b = (f'"{plugin}:', f"/{plugin}:") if plugin else ("", "")
    found = []
    for f in PROJECTS.glob("*/*.jsonl"):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if plugin and needle_a not in text and needle_b not in text:
            continue
        if '"type":"user"' not in text and '"type": "user"' not in text:
            continue  # metadata-only stubs the app leaves behind
        found.append(session_facts(f, text, plugin))
    found = [s for s in found
             if (plugin is None or s["commands"] or s["spawns"])
             and (include_headless or not headless(s["cwd"]))
             and (not project or project in s["cwd"])]
    mark_forks(found)
    return sorted(found, key=lambda s: -s["mtime"])


def mark_forks(sessions: list[dict]) -> None:
    """A fork or resumed copy shares its parent's record ids up to the point it split off.
    The older file of a pair is the parent (on a tie, the one holding more agent transcripts,
    which a fork leaves behind); the fork records where the two diverge."""
    by_project: dict[Path, list[dict]] = {}
    for s in sessions:
        by_project.setdefault(s["path"].parent, []).append(s)
    for group in by_project.values():
        for s in group:
            ids = [u for u, _ in s["uuids"]]
            for other in group:
                theirs = {u for u, _ in other["uuids"]}
                older = (other["born"], -other["own_agents"]) < (s["born"], -s["own_agents"])
                if other is s or not older or not ids or ids[0] not in theirs:
                    continue
                split = next((i for i, u in enumerate(ids) if u not in theirs), len(ids))
                s["fork_of"] = other["id"]
                s["fork_at"] = s["uuids"][split][1] if split < len(ids) else s["last_ts"]
                break


def resolve(session: str, plugin: str | None, project: str | None = None) -> Path:
    p = Path(session).expanduser()
    if p.suffix == ".jsonl" and p.exists():
        return p
    me = current_session()
    if session == "latest":
        hits = [s for s in sessions_for(plugin, project=project) if s["id"] != me]
        if not hits:
            sys.exit(f"no other session under {PROJECTS}"
                     + (f" used {plugin}" if plugin else "") + (f" in a project matching {project!r}" if project else ""))
        return hits[0]["path"]
    hits = list(PROJECTS.glob(f"*/{session}*.jsonl")) if re.fullmatch(r"[\w-]{4,}", session) else []
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        sys.exit(f"session id {session!r} matches {len(hits)} sessions; give more of it")
    words = session.lower().split()
    def match(pool: list[dict]) -> list[dict]:
        return [s for s in pool if s["id"] != me and all(w in s["title"].lower() for w in words)]
    titled = match(sessions_for(plugin, project=project)) or \
             match(sessions_for(plugin, include_headless=True, project=project))
    if len(titled) == 1:
        return titled[0]["path"]
    what = f"{plugin} chat" if plugin else "chat"
    if not titled:
        sys.exit(f"no session id or {what} title matches {session!r}; run `trace.py find`"
                 + (f" --plugin {plugin}" if plugin else ""))
    more = f"\n… and {len(titled) - 8} older; add words from the title, or use the id" if len(titled) > 8 else ""
    sys.exit(f"{len(titled)} {what}s match {session!r}; pick one by id:\n"
             + "\n".join(describe(s) for s in titled[:8]) + more)


# ---------------------------------------------------------------- one transcript → events


def summarize_call(name: str, inp: dict) -> str:
    if name == "Read":
        extra = "".join(f" {k}={inp[k]}" for k in ("offset", "limit") if k in inp)
        return f"{inp.get('file_path', '?')}{extra}"
    if name == "Write":
        body = inp.get("content", "")
        n = body.count("\n") + (0 if body.endswith("\n") or not body else 1)
        return f"{inp.get('file_path', '?')} ({n} lines)"
    if name == "Edit":
        old = one_line(inp.get("old_string", ""))[:80]
        new = one_line(inp.get("new_string", ""))[:80]
        flag = " replace_all" if inp.get("replace_all") else ""
        return f"{inp.get('file_path', '?')}{flag} | old: {old!r} | new: {new!r}"
    if name == "Bash":
        return clip(inp.get("command", ""), "cmd")
    if name in ("Grep", "Glob"):
        return f"{inp.get('pattern', '?')!r} in {inp.get('path', '.')}" + (
            f" glob={inp['glob']}" if inp.get("glob") else ""
        )
    if name == "Skill":
        return f"{inp.get('skill', '?')} {inp.get('args', '')}".strip()
    if name in ("Agent", "Task"):
        bg = " [background]" if inp.get("run_in_background") else ""
        return f"{inp.get('subagent_type', 'general-purpose')} — {inp.get('description', '')}{bg}"
    if name == "SubagentHandback":
        return clip(one_line(inp.get("message", "")), "text")
    if name == "AskUserQuestion":
        return " / ".join(q.get("question", "") for q in inp.get("questions", []))
    if name == "SendMessage":
        return f"to {inp.get('to', '?')}: {clip(one_line(inp.get('message', '')), 'arg')}"
    return clip(json.dumps(inp, ensure_ascii=False), "arg")


def events_of(records: list[dict]) -> tuple[list[dict], dict]:
    """Ordered events, plus facts about the transcript (system prompt, models, skill bases)."""
    events: list[dict] = []
    by_tool_id: dict[str, dict] = {}
    facts: dict = {"system": None, "models": set(), "bases": [], "cwd": None, "branch": None, "usage": {}}

    def add(kind: str, rec: dict, **kw) -> dict:
        ev = {"kind": kind, "ts": rec.get("timestamp", ""), **kw}
        events.append(ev)
        return ev

    for rec in records:
        t = rec.get("type")
        facts["cwd"] = facts["cwd"] or rec.get("cwd")
        facts["branch"] = facts["branch"] or rec.get("gitBranch")
        msg = rec.get("message") or {}
        content = msg.get("content")

        if t == "assistant":
            if msg.get("model"):
                facts["models"].add(msg["model"])
            if msg.get("id") and isinstance(msg.get("usage"), dict):
                # one API response is split into a record per content block, each repeating its usage
                seen = facts["usage"].setdefault(msg["id"], {"ts": rec.get("timestamp", ""), **usage_of({})})
                for k, v in usage_of(msg["usage"]).items():
                    seen[k] = max(seen[k], v)
            for b in content or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b.get("text", "").strip():
                    add("say", rec, text=b["text"])
                elif b.get("type") == "thinking" and b.get("thinking", "").strip():
                    add("think", rec, text=b["thinking"])
                elif b.get("type") == "tool_use":
                    ev = add("call", rec, id=b.get("id"), name=b.get("name"), input=b.get("input") or {},
                             mid=msg.get("id"))
                    by_tool_id[b.get("id")] = ev

        elif t == "user":
            blocks = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_result":
                    ev = by_tool_id.get(b.get("tool_use_id"))
                    if ev is not None:
                        ev["error"] = bool(b.get("is_error"))
                        ev["result"] = result_text(b.get("content"))
                        tur = rec.get("toolUseResult")
                        if isinstance(tur, dict):
                            ev["meta"] = {
                                k: tur[k]
                                for k in ("agentId", "status", "totalDurationMs", "totalToolUseCount", "totalTokens",
                                          "resolvedModel")
                                if k in tur
                            }
                    continue
                text = b.get("text", "") if b.get("type") == "text" else ""
                if not text.strip() or "<local-command-caveat>" in text:
                    continue
                if (m := BASE_RE.search(text)) and text.lstrip().startswith("Base directory"):
                    facts["bases"].append(m.group(1))
                    add("skill-body", rec, base=m.group(1))
                elif m := CMD_RE.search(text):
                    a = ARGS_RE.search(text)
                    add("command", rec, name=m.group(1), args=(a.group(1).strip() if a else ""))
                elif "<task-notification>" in text:
                    m = TASK_RE.search(text)
                    add("notify", rec, task=m.group(1) if m else "?", status=m.group(2) if m else "?", text=text)
                elif m := HANDBACK_RE.search(text):
                    add("handback", rec, frm=m.group(1))
                elif not rec.get("isMeta"):
                    add("user", rec, text=text)

        elif t == "attachment":
            att = rec.get("attachment") or {}
            at = att.get("type")
            if at == "prompt_snapshot":
                sp = att.get("systemPrompt")
                facts["system"] = "\n\n".join(sp) if isinstance(sp, list) else sp
            elif at == "hook_blocking_error":
                be = att.get("blockingError")
                text = be.get("blockingError") if isinstance(be, dict) else str(be)
                ev = add("hook", rec, hook=att.get("hookName"), block=True, text=text, tool=att.get("toolUseID"))
                if (call := by_tool_id.get(att.get("toolUseID"))) is not None:
                    call.setdefault("hooks", []).append(ev)
            elif at == "hook_success" and (att.get("stderr") or att.get("stdout") or "").strip():
                add("hook", rec, hook=att.get("hookName"), block=False,
                    text=(att.get("stderr") or "") + (att.get("stdout") or ""), tool=att.get("toolUseID"))
            elif at == "queued_command" and (m := HANDBACK_RE.search(att.get("prompt") or "")):
                add("handback", rec, frm=m.group(1))

        elif t == "system" and rec.get("subtype") in ("api_error",) or (t == "system" and rec.get("level") == "error"):
            err = rec.get("error") or {}
            add("system", rec, text=f"{rec.get('subtype')}: {err.get('formatted') or err.get('message') or ''}")

    for ev in events:  # skills injected before the agent's first turn were preloaded, not typed
        if ev["kind"] in ("say", "call", "think"):
            break
        if ev["kind"] == "command":
            ev["injected"] = True
    facts["models"] = sorted(facts["models"])
    facts["usage"] = sorted(facts["usage"].values(), key=lambda u: u["ts"])
    return events, facts


# ---------------------------------------------------------------- tokens and files


def usage_of(u: dict) -> dict:
    return {"input": u.get("input_tokens") or 0, "cache_write": u.get("cache_creation_input_tokens") or 0,
            "cache_read": u.get("cache_read_input_tokens") or 0, "output": u.get("output_tokens") or 0}


def tokens_of(usages: list[dict]) -> dict:
    """Totals over API responses, plus the largest context one request carried and how many there were."""
    out = {k: sum(u[k] for u in usages) for k in ("input", "cache_write", "cache_read", "output")}
    out["context_peak"] = max((u["input"] + u["cache_write"] + u["cache_read"] for u in usages), default=0)
    out["requests"] = len(usages)
    return out


def fmt_tokens(t: dict) -> str:
    return " · ".join(f"{k} {t.get(k, 0):,}" for k in ("input", "cache_write", "cache_read", "output", "context_peak")
                      if k in t)


def wall(a: str, b: str) -> str:
    sa, sb = local(a or ""), local(b or "")
    if not (sa and sb):
        return "—"
    sec = int((sb - sa).total_seconds())
    return f"{sec // 60}m{sec % 60:02d}s"


def add_tokens(*ts: dict) -> dict:
    out = {k: sum(t.get(k, 0) for t in ts) for k in ("input", "cache_write", "cache_read", "output", "requests")}
    out["context_peak"] = max((t.get("context_peak", 0) for t in ts), default=0)
    return out


READERS = {"cat", "head", "tail", "less", "more", "nl", "wc", "sed", "awk", "jq", "diff", "tee"}
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
REDIRECTS = {">": "write", ">|": "write", "&>": "write", ">>": "edit", "&>>": "edit"}


def strip_heredocs(cmd: str) -> str:
    """The command without the bodies of its here-documents, which are data, not commands."""
    out, lines, i = [], cmd.split("\n"), 0
    while i < len(lines):
        out.append(lines[i])
        ends = [m.group(2) for m in HEREDOC_RE.finditer(lines[i])]
        i += 1
        for end in ends:
            while i < len(lines) and lines[i].strip() != end:
                i += 1
            i += 1
    return "\n".join(out)


PY_HEREDOC_RE = re.compile(r"\bpython[\d.]*\b[^\n]*?<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\2[ \t]*(?:\n|$)", re.S)
PY_ASSIGN_RE = re.compile(r"""\b(\w+)\s*=\s*(?:Path\(\s*)?(['"])([^'"\n]+)\2""")
PY_OPEN_RE = re.compile(r"""\bopen\(\s*(?:(\w+)|(['"])([^'"\n]+)\2)\s*(?:,\s*(?:mode\s*=\s*)?(['"])([^'"]*)\4)?""")
PY_PATHIO_RE = re.compile(r"""(?:\b(\w+)|Path\(\s*(['"])([^'"\n]+)\2\s*\))\.(read_text|write_text|read_bytes|write_bytes)\(""")


def python_file_ops(cmd: str) -> list[tuple[str, str]]:
    """(op, path) pairs a `python - <<EOF` script plainly shows: `open(p, 'w')`, `open(p).read()`,
    `Path(p).write_text(...)`, with p a literal or a name bound to one. A file both read and
    written is an edit. Paths built at run time are not seen."""
    ops: list[tuple[str, str]] = []
    for m in PY_HEREDOC_RE.finditer(cmd):
        body = m.group(3)
        names = {n: v for n, _, v in PY_ASSIGN_RE.findall(body) if pathlike(v)}
        seen: dict[str, set[str]] = {}

        def note(name: str | None, lit: str | None, op: str) -> None:
            path = lit or names.get(name or "")
            if path and pathlike(path):
                seen.setdefault(path, set()).add(op)

        for name, _, lit, _, mode in PY_OPEN_RE.findall(body):
            note(name, lit, "write" if any(c in (mode or "") for c in "wax+") else "read")
        for name, _, lit, how in PY_PATHIO_RE.findall(body):
            note(name, lit, "write" if how.startswith("write") else "read")
        for path, how in seen.items():
            ops.append(("edit" if how == {"read", "write"} else "write" if "write" in how else "read", path))
    return ops


def simple_commands(cmd: str) -> list[str]:
    """Split at the `;`, `|`, `&&`, `||` and newlines that are outside quotes."""
    segs, cur, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            cur.append(ch)
            if ch == quote:
                quote = None
            elif ch == "\\" and quote == '"' and i + 1 < len(cmd):
                cur.append(cmd[i + 1])
                i += 1
        elif ch in "'\"":
            quote = ch
            cur.append(ch)
        elif ch == "\\" and i + 1 < len(cmd):
            cur += [ch, cmd[i + 1]]
            i += 1
        elif ch in ";|\n" or (ch == "&" and cmd[i + 1:i + 2] == "&"):
            segs.append("".join(cur))
            cur = []
            i += ch == "&"
        else:
            cur.append(ch)
        i += 1
    return [x.strip() for x in segs + ["".join(cur)] if x.strip()]


def pathlike(tok: str) -> bool:
    return bool(tok) and not tok.startswith("-") and ("/" in tok or re.search(r"\.\w{1,8}$", tok)) \
        and not re.search(r"[*?\[\]$`'\"{}():#\s]", tok) and not tok.startswith("/dev/")


def bash_file_ops(cmd: str, cwd: str | None) -> list[tuple[str, str]]:
    """(op, path) pairs a Bash command plainly shows: files it reads with a reader such as `cat`
    or `sed -n`, files it edits with `sed -i`, and files it writes with `>`, `>>` or `tee`. A guess
    from the text: a command that reads through a script it runs is not seen, and one that is
    only printed is."""
    import shlex
    ops: list[tuple[str, str]] = []
    base = cwd  # None once a `cd` goes somewhere the text does not say

    def add(op: str, path: str) -> None:
        if Path(path).is_absolute():
            ops.append((op, path))
        elif base:
            ops.append((op, str(Path(base) / path)))

    for op, path in python_file_ops(cmd):
        add(op, path)
    for seg in simple_commands(strip_heredocs(cmd)):
        lex = shlex.shlex(seg, posix=True, punctuation_chars="<>&")
        lex.whitespace_split = True
        try:
            toks = list(lex)
        except ValueError:
            continue
        words, i = [], 0
        while i < len(toks):
            t = toks[i]
            if t in REDIRECTS and i + 1 < len(toks):
                if pathlike(toks[i + 1]):
                    add(REDIRECTS[t], toks[i + 1])
                i += 2
            elif t and set(t) <= set("<>&"):  # input redirects, here-strings, fd duplication
                i += 2
            else:
                words.append(t)
                i += 1
        if words and words[-1].isdigit() and len(toks) > len(words):
            words.pop()  # the fd of a trailing `2>`
        if not words:
            continue
        if words[0] == "cd":
            to = words[1] if len(words) > 1 else None
            if not to or re.search(r"[$`~]", to) or to == "-":
                base = None
            elif Path(to).is_absolute():
                base = to
            elif base:
                base = str(Path(base) / to)
            continue
        prog, args, op = Path(words[0]).name, words[1:], "read"
        if prog not in READERS:
            continue
        if prog == "tee":
            op = "edit" if "-a" in args else "write"
        elif prog in ("sed", "awk", "jq"):  # the first bare argument is the program, the rest its files
            in_place = any(a.startswith("-i") or a == "--in-place" for a in args)
            if prog == "sed" and "-n" not in args and not in_place:
                continue  # a plain sed prints the whole file transformed; leave it to its reader
            op = "edit" if in_place else "read"
            args = [a for a in args if a and not a.startswith("-")][1:]
        for a in args:
            if pathlike(a):
                add(op, a)
    return ops


FILE_TOOLS = {"Read": "read", "Write": "write", "Edit": "edit", "MultiEdit": "edit", "NotebookEdit": "edit"}


def file_ops_of(events: list[dict], cwd: str | None, who: str) -> list[dict]:
    """Every file a run of events read, wrote or edited, one entry per call that touched it."""
    out = []
    for ev in events:
        if ev["kind"] != "call":
            continue
        name, inp = ev["name"], ev["input"]
        pairs = []
        if name in FILE_TOOLS and (inp.get("file_path") or inp.get("notebook_path")):
            pairs = [(FILE_TOOLS[name], inp.get("file_path") or inp.get("notebook_path"))]
        elif name == "Bash":
            pairs = bash_file_ops(inp.get("command", ""), cwd)
        for op, path in pairs:
            norm = os.path.normpath(path) if Path(path).is_absolute() else path
            out.append({"path": norm, "op": op, "via": name, "step": ev.get("step"), "who": who,
                        "error": bool(ev.get("error"))})
    return out


def file_summary(ops: list[dict]) -> list[dict]:
    """One row per (path, op), in first-touch order, with how many calls and who made them."""
    rows: dict[tuple[str, str], dict] = {}
    for o in ops:
        r = rows.setdefault((o["path"], o["op"]), {"path": o["path"], "op": o["op"], "n": 0, "who": [], "via": []})
        r["n"] += 1
        for k in ("who", "via"):
            if o[k] not in r[k]:
                r[k].append(o[k])
    return list(rows.values())


def commits_of(ev: dict) -> list[str]:
    """Commits a Bash call that ran `git commit` made.

    `[branch sha] msg` in the output is certain. A `git log --oneline` line after a quiet
    commit is only HEAD after the call, and in a parallel run HEAD can be another agent's
    commit, so it is returned as `?sha` for the auditor to confirm with `git show`.
    """
    cmd = ev["input"].get("command", "") if ev.get("name") == "Bash" else ""
    if not re.search(r"\bgit\b[^|;&]*\bcommit\b", cmd):
        return []
    res = ev.get("result", "")
    sure = [m.group(2) for m in COMMIT_RE.finditer(res)]
    if sure:
        return sure
    if "git log" in cmd and (m := ONELINE_RE.search(res)):
        return [f"?{m.group(1)}"]
    return [] if ev.get("error") else ["?(sha not shown)"]


def confirm(shas: list[str], written: list[str], project: str | None) -> list[str]:
    """Drop the `?` from a HEAD-after SHA whose commit holds a file this unit wrote."""
    out = []
    for sha in shas:
        if not sha.startswith("?") or sha == "?(sha not shown)" or not project:
            out.append(sha)
            continue
        try:
            files = subprocess.run(["git", "-C", project, "show", "--name-only", "--format=", sha[1:]],
                                   capture_output=True, text=True, timeout=20).stdout.split()
        except (OSError, subprocess.TimeoutExpired):
            files = []
        mine = {str(Path(w).resolve().relative_to(Path(project).resolve())) for w in written
                if Path(w).is_absolute() and str(Path(w)).startswith(project)} | {w for w in written if not Path(w).is_absolute()}
        out.append(sha[1:] if mine & set(files) else sha)
    return out


# ---------------------------------------------------------------- full steps, for the pages


def commit_details(sha: str, ev: dict, project: str | None) -> dict:
    """One commit a call made: its message and files from the project when it still exists,
    else the message the call's own output printed and no files. Claims nothing else."""
    bare = sha.lstrip("?")
    out = {"sha": bare, "confirmed": not sha.startswith("?"), "message": "", "files": []}
    if sha == "?(sha not shown)":
        return out
    res = ev.get("result", "")
    for m in COMMIT_RE.finditer(res):
        if m.group(2) == bare:
            out["message"] = m.group(3).strip()
    if not out["message"] and (m := ONELINE_RE.search(res)) and m.group(1) == bare:
        out["message"] = m.group(2).strip()
    if project and Path(project).is_dir():
        try:
            shown = subprocess.run(["git", "-C", project, "show", "--name-only", "--format=%s", bare],
                                   capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired):
            shown = None
        if shown is not None and shown.returncode == 0 and shown.stdout.strip():
            lines = shown.stdout.splitlines()
            out["message"] = lines[0].strip()
            out["files"] = [x.strip() for x in lines[1:] if x.strip()]
    return out


def full_step(ev: dict, hooks_by_call: dict, written: list[str], project: str | None) -> dict:
    """One numbered event, whole: nothing here is clipped."""
    k = ev["kind"]
    step = {"step": ev["step"], "kind": k, "ts": ev.get("ts", ""), "summary": ev.get("summary", "")}
    if k == "call":
        name, inp = ev["name"], ev["input"]
        step.update({
            "tool": name, "input": inp, "output": ev.get("result", ""), "error": bool(ev.get("error")),
            "hooks": [{"hook": h.get("hook"), "blocked": bool(h.get("block")), "text": h.get("text") or ""}
                      for h in hooks_by_call.get(ev.get("id"), [])],
            "commits": [commit_details(sha, ev, project) for sha in confirm(commits_of(ev), written, project)],
            "write": {"path": inp.get("file_path", ""), "content": inp.get("content", "")} if name == "Write" else None,
            "edit": ({"path": inp.get("file_path", ""), "old": inp.get("old_string", ""),
                      "new": inp.get("new_string", "")} if name == "Edit" else None),
        })
        if ev.get("meta"):
            step["meta"] = ev["meta"]
    elif k in ("say", "think", "user", "system"):
        step["text"] = ev.get("text", "")
    elif k == "command":
        step.update({"name": ev.get("name"), "args": ev.get("args", ""), "injected": bool(ev.get("injected"))})
    elif k == "skill-body":
        step["base"] = ev.get("base")
    elif k == "notify":
        step.update({"task": ev.get("task"), "status": ev.get("status"), "text": ev.get("text", "")})
    elif k == "handback":
        step["from"] = ev.get("frm")
    elif k == "hook":
        step.update({"hook": ev.get("hook"), "blocked": bool(ev.get("block")), "text": ev.get("text") or ""})
    return step


def unit_json(u: dict, iu: dict, project: str | None) -> dict:
    """`units/U<nn>.json`: the unit's every step with full input and output, numbered exactly as
    in `units/U<nn>.md`. A hook shown under its call there is in that call's `hooks` here."""
    hooks_by_call: dict[str, list[dict]] = {}
    for ev in u["events"]:
        if ev["kind"] == "hook" and ev.get("under_call"):
            hooks_by_call.setdefault(ev.get("tool"), []).append(ev)
    steps = [full_step(ev, hooks_by_call, iu["files_written"], project)
             for ev in u["events"] if not (ev["kind"] == "hook" and ev.get("under_call"))]
    return {
        "unit": iu["unit"], "agent_id": iu["agent_id"], "type": iu["type"], "description": iu["description"],
        "spawner": iu["spawner"], "spawn_step": iu.get("spawn_step"), "segment": iu.get("segment"),
        "background": iu["background"], "definition": iu["definition"], "version": iu["version"],
        "models": u["facts"]["models"], "first_ts": iu["first_ts"], "last_ts": iu["last_ts"],
        "finished": iu["finished"], "tool_calls": iu["tool_calls"], "errors": iu["errors"], "turn": iu.get("turn"),
        "hook_blocks": iu["hook_blocks"],
        "skills": [e["input"].get("skill") for e in u["events"] if e["kind"] == "call" and e["name"] == "Skill"],
        "files_written": iu["files_written"], "commits": iu["commits"],
        "tokens": iu["tokens"], "file_ops": u["file_ops"],
        "prompt": u["prompt"], "steps": steps, "return": u["return"], "step_count": len(steps),
    }


# ---------------------------------------------------------------- rendering


def render_call(ev: dict, units_by_agent: dict) -> list[str]:
    name = ev["name"]
    line = f"**{name}** {summarize_call(name, ev['input'])}"
    if name in ("Agent", "Task") and (aid := (ev.get("meta") or {}).get("agentId")):
        u = units_by_agent.get(aid)
        line += f" → **{u['unit']}**" if u else f" → agent {aid}"
    if ev.get("error"):
        line += "  ❌ ERROR"
    out = [line]
    res = ev.get("result", "")
    if ev.get("error"):
        out.append(f"    ↳ {clip(one_line(res), 'err')}")
    elif name == "Bash":
        for sha in commits_of(ev):
            out.append(f"    ↳ COMMIT {sha}" if not sha.startswith("?")
                       else f"    ↳ COMMIT UNCONFIRMED — HEAD after the call was {sha[1:]}; check `git show --stat {sha[1:]}`")
        if res.strip():
            out.append(f"    ↳ {tail(one_line(res), 'out')}")
    elif name in ("Agent", "Task"):
        meta = ev.get("meta") or {}
        if meta:
            out.append(
                f"    ↳ status={meta.get('status')} tools={meta.get('totalToolUseCount')} "
                f"ms={meta.get('totalDurationMs')} model={meta.get('resolvedModel')}"
            )
    elif name in ("Grep", "Glob"):
        out.append(f"    ↳ {clip(one_line(res), 'arg')}")
    elif name == "Read":
        out.append(f"    ↳ {res.count(chr(10)) + 1 if res else 0} lines")
    elif name == "AskUserQuestion":
        out.append(f"    ↳ {clip(one_line(res), 'err')}")
    for h in ev.get("hooks", []):
        out.append(f"    ⛔ HOOK {h['hook']} blocked: {clip(one_line(h['text']), 'err')}")
    return out


def render_events(events: list[dict], prefix: str, units_by_agent: dict, start: int = 1) -> list[str]:
    lines = []
    n = start - 1
    for ev in events:
        n += 1
        ev["step"] = f"{prefix}{n}"
        k = ev["kind"]
        head = f"- `{ev['step']}` "
        if k == "call":
            body = render_call(ev, units_by_agent)
            lines.append(head + body[0])
            lines.extend("  " + b for b in body[1:])
            ev["summary"] = body[0]
            continue
        elif k == "say":
            lines.append(head + f"_said:_ {clip(one_line(ev['text']), 'text')}")
        elif k == "think":
            lines.append(head + f"_thought:_ {clip(one_line(ev['text']), 'text')}")
        elif k == "command":
            if prefix != "D" and ev.get("injected"):
                lines.append(head + f"skill preloaded: `{ev['name']}`")
            else:
                lines.append(head + f"**USER TYPED** `/{ev['name']} {ev['args']}`".rstrip())
        elif k == "user":
            lines.append(head + f"**USER:** {clip(one_line(ev['text']), 'text')}")
        elif k == "skill-body":
            lines.append(head + f"skill loaded from `{ev['base']}`")
        elif k == "notify":
            u = units_by_agent.get(ev["task"])
            who = u["unit"] if u else ev["task"]
            lines.append(head + f"← background task {who} {ev['status']}")
        elif k == "handback":
            u = units_by_agent.get(ev["frm"])
            who = u["unit"] if u else ev["frm"]
            first = one_line(u["return"]).split(" ⏎ ")[0] if u and u.get("return") else ""
            lines.append(head + f"← **{who} handed back:** {clip(first, 'arg')}")
        elif k == "hook":
            if ev.get("tool") and any(e.get("id") == ev["tool"] for e in events if e["kind"] == "call"):
                n -= 1  # shown under its call
                ev["under_call"] = True
                continue
            verb = "blocked" if ev["block"] else "said"
            lines.append(head + f"{'⛔ ' if ev['block'] else ''}HOOK {ev['hook']} {verb}: {clip(one_line(ev['text']), 'err')}")
        elif k == "system":
            lines.append(head + f"⚠ {ev['text']}")
        ev["summary"] = lines[-1][len(head):]
    return lines


SECTION_RE = re.compile(r"^Section:\s*(\S+)", re.M)
PATHLIKE_RE = re.compile(r"\b([a-z][\w-]*/[a-z][\w.-]*[\w])\b")


def lane_of(prompt: str, description: str) -> str | None:
    """What a unit worked on: a `Section:` input, else the first `a/b` name in its description or prompt."""
    if m := SECTION_RE.search(prompt or ""):
        return m.group(1)
    for text in (description, prompt):
        if m := PATHLIKE_RE.search(text or ""):
            return m.group(1)
    return None


MODE_RE = re.compile(r"^Mode:\s*(.+)$", re.M)


def mode_of(prompt: str) -> str | None:
    """The prompt's first `Mode:` line, when it has one."""
    m = MODE_RE.search(prompt or "")
    return m.group(1).strip() if m else None


def outcome(ret: str, description: str) -> dict:
    """The `Result:` of a return and, for a review, its verdict, counts and round. Heuristic, by design."""
    first = one_line(ret).split(" ⏎ ")[0] if ret else ""
    res = re.match(r"\W*Result:\W*([\w-]+)", first)
    out: dict = {"result": res.group(1).lower() if res else None, "verdict": None,
                 "critical": None, "warning": None, "round": None}
    v = re.search(r"Verdict:\W*(approve|request changes|spec-change|reject|blocked|defer)", ret or "", re.I)
    if v:
        out["verdict"] = v.group(1).lower()
        # "round-1 CRITICAL" is not a count: a count is a bare number, preferably beside its warnings
        both = re.search(r"(?<![\w-])(\d+)\s+critical\b[^.\n]{0,20}?(?<![\w-])(\d+)\s+warnings?", ret, re.I)
        crit = both or re.search(r"(?<![\w-])(\d+)\s+critical", ret, re.I)
        warn = re.search(r"(?<![\w-])(\d+)\s+warnings?", ret, re.I)
        out["critical"] = int(crit.group(1)) if crit else None
        out["warning"] = int(both.group(2)) if both else int(warn.group(1)) if warn else None
    if out["result"] in ("blocked", "stopped"):  # it wrote no review, whatever its text says it would have
        out["verdict"] = out["result"]
    if m := re.search(r"\bRound:?\W*(\d+)", ret or "") or re.search(r"\br(\d+)\b", description or ""):
        out["round"] = int(m.group(1))
    return out


def unit_return(events: list[dict]) -> str:
    for ev in reversed(events):
        if ev["kind"] == "call" and ev["name"] == "SubagentHandback":
            return ev["input"].get("message", "")
    for ev in reversed(events):
        if ev["kind"] == "say":
            return ev["text"]
    return ""


# ---------------------------------------------------------------- plugin root


def plugin_root(bases: list[str], plugin: str) -> tuple[str | None, str | None]:
    counts: dict[str, int] = {}
    for b in bases:
        p = Path(b)
        root = p.parent.parent if p.parent.name == "skills" else None
        if root is None or f"/{plugin}/" not in f"{root}/":
            continue
        counts[str(root)] = counts.get(str(root), 0) + 1
    if not counts:
        return None, None
    root = max(counts, key=counts.get)
    manifest = Path(root) / ".claude-plugin" / "plugin.json"
    version = None
    if manifest.exists():
        try:
            version = json.loads(manifest.read_text()).get("version")
        except json.JSONDecodeError:
            pass
    if version is None:
        parts = Path(root).parts
        if plugin in parts and parts.index(plugin) + 1 < len(parts):
            version = parts[parts.index(plugin) + 1]
    return root, version


def definition_for(agent_type: str, first_base: str | None, plugin: str, root: str | None) -> str | None:
    if first_base:
        return str(Path(first_base) / "SKILL.md")
    if root and agent_type.startswith(f"{plugin}:"):
        return str(Path(root) / "agents" / f"{agent_type.split(':', 1)[1]}.md")
    return None


# ---------------------------------------------------------------- build


def agent_files(session_path: Path, main_events: list[dict]) -> list[Path]:
    """Every spawned agent's transcript: the session's own, plus any a fork left behind.

    A forked or resumed chat copies its parent's history into a new session file, but the
    transcripts of agents spawned before the fork stay under the parent's directory. Those
    are found in the project's other sessions by the spawning call's tool_use id, which the
    copy keeps; nested spawns are followed until nothing new turns up.
    """
    own = sorted((session_path.with_suffix("") / "subagents").glob("agent-*.jsonl"))
    wanted = {e["id"] for e in main_events if e["kind"] == "call" and e["name"] in ("Agent", "Task")}
    have = {f.stem for f in own}
    for f in own:
        wanted |= set(re.findall(r'"type":\s*"tool_use",\s*"id":\s*"([^"]+)",\s*"name":\s*"(?:Agent|Task)"',
                                 f.read_text(encoding="utf-8", errors="replace")))
    elsewhere = [m for m in session_path.parent.glob("*/subagents/agent-*.meta.json")
                 if m.parent.parent != session_path.with_suffix("")]
    found = list(own)
    grew = True
    while grew:
        grew = False
        for m in elsewhere:
            f = m.with_name(m.name.removesuffix(".meta.json") + ".jsonl")
            if f.stem in have or not f.exists():
                continue
            try:
                tid = json.loads(m.read_text()).get("toolUseId")
            except (OSError, json.JSONDecodeError):
                continue
            if tid in wanted:
                found.append(f)
                have.add(f.stem)
                wanted |= set(re.findall(r'"id":\s*"([^"]+)",\s*"name":\s*"(?:Agent|Task)"',
                                         f.read_text(encoding="utf-8", errors="replace")))
                grew = True
    return found


def build(session_path: Path, plugin: str | None, out: Path, quiet: bool = False) -> dict:
    main_records = load(session_path)
    main_events, main_facts = events_of(main_records)
    raw_units = []
    for f in agent_files(session_path, main_events):
        aid = f.stem.removeprefix("agent-")
        meta_p = f.with_suffix(".meta.json")
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        recs = load(f)
        evs, facts = events_of(recs)
        first_ts = next((r.get("timestamp") for r in recs if r.get("timestamp")), "")
        raw_units.append({"agent": aid, "meta": meta, "events": evs, "facts": facts, "ts": first_ts, "records": recs})
    raw_units.sort(key=lambda u: (u["ts"], u["agent"]))

    all_bases = list(main_facts["bases"]) + [b for u in raw_units for b in u["facts"]["bases"]]
    root, version = plugin_root(all_bases, plugin)

    # Which tool_use spawned which agent: the parent Agent call's id is meta.toolUseId.
    spawn_site: dict[str, tuple[str, dict]] = {}
    for ev in main_events:
        if ev["kind"] == "call":
            spawn_site[ev["id"]] = ("driver", ev)
    units_by_agent: dict[str, dict] = {}
    for i, u in enumerate(raw_units, 1):
        u["unit"] = f"U{i:02d}"
        units_by_agent[u["agent"]] = u
        for ev in u["events"]:
            if ev["kind"] == "call":
                spawn_site[ev["id"]] = (u["unit"], ev)

    for u in raw_units:
        meta = u["meta"]
        site = spawn_site.get(meta.get("toolUseId", ""))
        u["spawner"] = site[0] if site else "?"
        u["spawn_call"] = site[1] if site else None
        u["type"] = meta.get("agentType") or (site[1]["input"].get("subagent_type") if site else "?")
        u["description"] = meta.get("description") or (site[1]["input"].get("description", "") if site else "")
        u["background"] = bool(site and site[1]["input"].get("run_in_background")) or meta.get("requestShape") == "background"
        first_base = u["events"][0]["base"] if u["events"] and u["events"][0]["kind"] == "skill-body" else None
        u["forked_skill"] = first_base
        u_root, u["version"] = plugin_root(u["facts"]["bases"], plugin)
        u["root"] = u_root or root
        u["version"] = u["version"] or version
        u["definition"] = definition_for(u["type"], first_base, plugin, u["root"])
        u["return"] = unit_return(u["events"])
        u["prompt"] = (site[1]["input"].get("prompt", "") if site else "") or next(
            (r["message"]["content"] for r in u["records"] if r.get("type") == "user"
             and isinstance((r.get("message") or {}).get("content"), str)), "")

    # Render units first so step ids exist; the driver refers to units by id.
    (out / "units").mkdir(parents=True, exist_ok=True)
    (out / "driver").mkdir(parents=True, exist_ok=True)
    index_units = []
    for u in raw_units:
        steps = render_events(u["events"], f"{u['unit']}.S", units_by_agent)
        calls = [e for e in u["events"] if e["kind"] == "call"]
        written = sorted({e["input"].get("file_path") for e in calls if e["name"] in ("Write", "Edit", "NotebookEdit") and e["input"].get("file_path")})
        skills = [e["input"].get("skill") for e in calls if e["name"] == "Skill"]
        commits = confirm([sha for e in calls for sha in commits_of(e)], written, main_facts["cwd"])
        errors = sum(1 for e in calls if e.get("error"))
        blocks = sum(1 for e in u["events"] if e["kind"] == "hook" and e["block"])
        u["tokens"] = tokens_of(u["facts"]["usage"])
        u["file_ops"] = file_ops_of(u["events"], u["facts"]["cwd"] or main_facts["cwd"], u["unit"])
        files = file_summary(u["file_ops"])
        spawned_at = u["spawn_call"]["step"] if u["spawn_call"] and "step" in u["spawn_call"] else None
        doc = [
            f"# {u['unit']} · {u['type']} · {u['description']}",
            "",
            f"- **Agent id:** `{u['agent']}` · **spawned by:** {u['spawner']} · "
            f"**mode:** {'background' if u['background'] else 'foreground'} · **depth:** {u['meta'].get('spawnDepth', '?')}",
            f"- **Definition:** `{u['definition'] or 'none (not a plugin agent)'}`"
            + (f" (forked skill)" if u["forked_skill"] else ""),
            f"- **System prompt as run:** `units/{u['unit']}.system.md`" if u["facts"]["system"] else "- **System prompt as run:** not recorded",
            f"- **Model:** {', '.join(u['facts']['models']) or '?'} · **first/last:** {u['ts']} / {u['events'][-1]['ts'] if u['events'] else '?'}",
            f"- **Tool calls:** {len(calls)} · **errors:** {errors} · **hook blocks:** {blocks} · "
            f"**skills invoked:** {', '.join(skills) or 'none'} · **commits:** {', '.join(commits) or 'none'}",
            f"- **Files written:** {', '.join(f'`{w}`' for w in written) or 'none'}",
            "",
            "## Prompt it was sent",
            "",
            "```text",
            u["prompt"].strip(),
            "```",
            "",
            "## Steps",
            "",
            *steps,
            "",
            "## What it handed back",
            "",
            "```text",
            u["return"].strip() or "(nothing)",
            "```",
            "",
        ]
        (out / "units" / f"{u['unit']}.md").write_text("\n".join(doc), encoding="utf-8")
        if u["facts"]["system"]:
            (out / "units" / f"{u['unit']}.system.md").write_text(u["facts"]["system"], encoding="utf-8")
        index_units.append({
            "unit": u["unit"], "agent_id": u["agent"], "type": u["type"], "description": u["description"],
            "spawner": u["spawner"], "background": u["background"], "definition": u["definition"], "version": u["version"],
            "forked_skill": bool(u["forked_skill"]), "trace": f"units/{u['unit']}.md",
            "json": f"units/{u['unit']}.json",
            "tool_calls": len(calls), "errors": errors, "hook_blocks": blocks, "commits": commits,
            "files_written": written, "first_ts": u["ts"],
            "files_read": [f["path"] for f in files if f["op"] == "read"],
            "files_edited": [f["path"] for f in files if f["op"] in ("write", "edit")],
            "tokens": u["tokens"],
            "last_ts": u["events"][-1]["ts"] if u["events"] else "",
            "finished": any(e["kind"] == "call" and e["name"] == "SubagentHandback" for e in u["events"])
                        or bool(u["spawn_call"] and "result" in u["spawn_call"]),
            "return_first_line": one_line(u["return"]).split(" ⏎ ")[0][:200] if u["return"] else "",
            "wave_key": f"{u['spawner']}:{(u['spawn_call'] or {}).get('mid') or u['agent']}",
            "lane": lane_of(u["prompt"], u["description"]),
            "role": u["type"].split(":")[-1],
            "mode": mode_of(u["prompt"]),
            **outcome(u["return"], u["description"]),
        })

    # Driver: the main thread, split into segments at each command of this plugin.
    driver_lines = render_events(main_events, "D", units_by_agent)
    for u in raw_units:
        if u["spawn_call"] is not None and "step" in u["spawn_call"]:
            for iu in index_units:
                if iu["unit"] == u["unit"]:
                    iu["spawn_step"] = u["spawn_call"]["step"]
    segments = []
    cur = None
    for ev, line_idx in zip(main_events, range(len(main_events))):
        if plugin and ev["kind"] == "command" and ev["name"].startswith(f"{plugin}:"):
            cur = {"seg": len(segments) + 1, "command": f"/{ev['name']} {ev['args']}".strip(),
                   "skill": ev["name"].split(":", 1)[1], "first": ev.get("step"), "events": []}
            segments.append(cur)
        if cur is not None:
            cur["events"].append(ev)
    index_segments = []
    for s in segments:
        steps = [e.get("step") for e in s["events"] if e.get("step")]
        s["last"] = steps[-1] if steps else s["first"]
        body = render_events(s["events"], "D", units_by_agent,
                             start=int(s["first"][1:]) if s["first"] else 1)
        spawned = [u["unit"] for u in raw_units if u["spawner"] == "driver"
                   and u["spawn_call"] is not None and u["spawn_call"] in s["events"]]
        s_root, s_version = plugin_root([e["base"] for e in s["events"] if e["kind"] == "skill-body"], plugin)
        s_root, s_version = s_root or root, s_version or version
        definition = str(Path(s_root) / "skills" / s["skill"] / "SKILL.md") if s_root else None
        doc = [
            f"# Driver segment {s['seg']} · `{s['command']}`",
            "",
            f"- **Steps:** {s['first']}–{s['last']} · **definition:** `{definition}`",
            f"- **Units spawned here:** {', '.join(spawned) or 'none'}",
            "",
            "## Steps",
            "",
            *body,
            "",
        ]
        (out / "driver" / f"seg-{s['seg']}.md").write_text("\n".join(doc), encoding="utf-8")
        index_segments.append({"seg": s["seg"], "command": s["command"], "definition": definition,
                               "plugin_root": s_root, "version": s_version,
                               "trace": f"driver/seg-{s['seg']}.md", "first": s["first"], "last": s["last"],
                               "units": spawned})

    # Units spawned below the driver belong to their top-level ancestor's segment.
    seg_of = {u: s["seg"] for s in index_segments for u in s["units"]}
    changed = True
    while changed:
        changed = False
        for iu in index_units:
            if iu["unit"] not in seg_of and iu["spawner"] in seg_of:
                seg_of[iu["unit"]] = seg_of[iu["spawner"]]
                changed = True
    for iu in index_units:
        iu["segment"] = seg_of.get(iu["unit"])

    index_turns = build_turns(main_events, main_facts, raw_units, index_units, out)

    # Full steps, one JSON per unit: written last, once spawn steps and segments are known.
    for u, iu in zip(raw_units, index_units):
        doc = unit_json(u, iu, main_facts["cwd"])
        iu["step_count"] = doc["step_count"]
        (out / "units" / f"{u['unit']}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                                                         encoding="utf-8")

    interventions = []
    for ev in main_events:
        if ev["kind"] == "call" and ev["name"] == "AskUserQuestion":
            interventions.append({"step": ev.get("step"), "ts": ev["ts"], "kind": "asked",
                                  "text": summarize_call("AskUserQuestion", ev["input"]),
                                  "answer": "; ".join(re.findall(r'"="(.*?)"(?=[.,;]|\s|$)', ev.get("result", "")))
                                            or one_line(ev.get("result", ""))[:300]})
        elif ev["kind"] == "user":
            interventions.append({"step": ev.get("step"), "ts": ev["ts"], "kind": "said",
                                  "text": one_line(ev["text"])[:300], "answer": ""})

    index = {
        "session": session_path.stem, "transcript": str(session_path), "plugin": plugin,
        "title": title_of(session_path.read_text(encoding="utf-8", errors="replace")),
        "plugin_root": root, "plugin_root_exists": bool(root and Path(root).exists()), "version": version,
        "project": main_facts["cwd"], "branch": main_facts["branch"],
        "models": sorted(set(main_facts["models"]) | {m for u in raw_units for m in u["facts"]["models"]}),
        "first_ts": main_events[0]["ts"] if main_events else "", "last_ts": main_events[-1]["ts"] if main_events else "",
        "segments": index_segments, "units": index_units, "interventions": interventions,
        "turns": index_turns,
        "tokens": {"main": tokens_of(main_facts["usage"]),
                   "units": add_tokens(*(iu["tokens"] for iu in index_units)),
                   "all": add_tokens(tokens_of(main_facts["usage"]), *(iu["tokens"] for iu in index_units))},
    }
    (out / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    run = [
        f"# Run trace · {index['title']} · session `{session_path.stem}`",
        "",
        f"- **Project:** `{index['project']}` · **branch:** `{index['branch']}`",
        *([f"- **Plugin that ran:** {plugin} at `{root}` · version **{version}**"
           + ("" if index["plugin_root_exists"] else " · ⚠ that directory no longer exists")] if plugin else []),
        f"- **Models:** {', '.join(index['models']) or '?'} · **span:** {index['first_ts']} → {index['last_ts']}",
        f"- **Tokens (all):** {fmt_tokens(index['tokens']['all'])}",
        "",
        "## Turns",
        "",
        "| Turn | Steps | Start | Wall | Tools | Err | Skills | Units | Out tok | Files changed | Prompt |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
        *[f"| {t['turn']} | {t['first_step']}–{t['last_step']} | {t['first_ts'][11:19]} | {wall(t['first_ts'], t['last_ts'])} | "
          f"{t['tool_calls']} | {t['errors']} | {', '.join(x for x in t['skills'] if x) or '—'} | {', '.join(t['units']) or '—'} | "
          f"{t['tokens']['output']:,} | {sum(1 for f in t['files'] if f['op'] in ('write', 'edit'))} | "
          f"{t['prompt_first_line'][:80].replace('|', '/')} |" for t in index_turns],
        "",
        "## Segments",
        "",
        "| Seg | Command | Steps | Units |",
        "|---|---|---|---|",
        *[f"| {s['seg']} | `{s['command']}` | {s['first']}–{s['last']} | {', '.join(s['units']) or '—'} |" for s in index_segments],
        "",
        "## Units",
        "",
        "| Unit | Seg | Type | Description | By | Tools | Err | Hook blocks | Commits | Returned |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *[f"| {u['unit']} | {u['segment'] or '—'} | {u['type']} | {u['description']} | {u['spawner']}"
          f"{' ' + u['spawn_step'] if u.get('spawn_step') else ''} | {u['tool_calls']} | {u['errors']} | "
          f"{u['hook_blocks']} | {', '.join(u['commits']) or '—'} | {u['return_first_line'][:90] or '(running or none)'} |"
          for u in index_units],
        "",
        "## Driver (whole main thread)",
        "",
        *driver_lines,
        "",
    ]
    run[run.index("## Driver (whole main thread)"):run.index("## Driver (whole main thread)")] = flow.text(index) + [""]
    (out / "run.md").write_text("\n".join(run), encoding="utf-8")
    flow.write_html(out)
    if quiet:
        return index
    print(f"trace: {out}  (page: {out / 'flow.html'})")
    print(f"  session: {session_path.stem} · \"{index['title']}\" · {index['project']}")
    if plugin:
        print(f"  plugin root: {root} (version {version}){'' if index['plugin_root_exists'] else ' — MISSING on disk'}")
    print(f"  segments: {len(index_segments)} · turns: {len(index_turns)} · units: {len(index_units)} · "
          f"driver steps: {len(main_events)} · output tokens: {index['tokens']['all']['output']:,}")
    for s in index_segments:
        print(f"  seg {s['seg']}: {s['command']} — {len(s['units'])} units spawned directly · {plugin} {s['version']}")
    versions = sorted({s["version"] for s in index_segments} | {u["version"] for u in raw_units} - {None})
    if len(versions) > 1:
        print(f"  ⚠ the run spans {plugin} versions {', '.join(versions)}: each segment's and unit's "
              f"definition in index.json points at the version it ran")
    return index


def build_turns(main_events: list[dict], main_facts: dict, raw_units: list[dict], index_units: list[dict],
                out: Path) -> list[dict]:
    """Split the main thread at each prompt the user typed: one turn (one loop of an eval) each.

    A turn owns the units it spawned and, through them, every unit below. Its tokens are the
    main thread's API responses from its first step until the next turn's, plus its units'.
    Writes `turns/T<nn>.json`, the turn's driver steps in full in the unit-page schema.
    """
    turns: list[list[dict]] = []
    for ev in main_events:
        typed = ev["kind"] == "user" or (ev["kind"] == "command" and not ev.get("injected"))
        if typed or not turns:
            turns.append([])
        turns[-1].append(ev)
    by_unit = {iu["unit"]: iu for iu in index_units}
    children: dict[str, list[str]] = {}
    for iu in index_units:
        children.setdefault(iu["spawner"], []).append(iu["unit"])
    starts = [t[0]["ts"] for t in turns] + ["\uffff"]
    hooks_by_call: dict[str, list[dict]] = {}
    for ev in main_events:
        if ev["kind"] == "hook" and ev.get("under_call"):
            hooks_by_call.setdefault(ev.get("tool"), []).append(ev)
    (out / "turns").mkdir(exist_ok=True)
    index_turns = []
    for n, evs in enumerate(turns, 1):
        tid = f"T{n:02d}"
        ids = {id(e) for e in evs}
        mine = [u["unit"] for u in raw_units if u["spawner"] == "driver" and u["spawn_call"] is not None
                and id(u["spawn_call"]) in ids]
        stack, tree = list(mine), []
        while stack:
            x = stack.pop(0)
            tree.append(x)
            stack += children.get(x, [])
        for x in tree:
            by_unit[x]["turn"] = n
        units = [by_unit[x] for x in tree]
        calls = [e for e in evs if e["kind"] == "call"]
        main_tok = tokens_of([q for q in main_facts["usage"] if starts[n - 1] <= q["ts"] < starts[n]])
        ops = file_ops_of(evs, main_facts["cwd"], "main") + [o for u in raw_units if u["unit"] in tree
                                                             for o in u["file_ops"]]
        files = file_summary(ops)
        prompt = next((e.get("text") or f"/{e.get('name')} {e.get('args', '')}" for e in evs
                       if e["kind"] in ("user", "command")), "")
        reply = next((e["text"] for e in reversed(evs) if e["kind"] == "say"), "")
        last = max([e["ts"] for e in evs if e.get("ts")] + [u["last_ts"] for u in units if u["last_ts"]] or [""])
        steps = [full_step(e, hooks_by_call, [], main_facts["cwd"]) for e in evs
                 if not (e["kind"] == "hook" and e.get("under_call"))]
        summary = {
            "turn": tid, "n": n, "first_ts": evs[0]["ts"], "last_ts": last,
            "first_step": evs[0].get("step"), "last_step": evs[-1].get("step"),
            "prompt_first_line": one_line(re.sub(r"<system-reminder>.*?</system-reminder>\s*", "", prompt, flags=re.S)
                                          or prompt).split(" ⏎ ")[0][:200],
            "reply_first_line": one_line(reply).split(" ⏎ ")[0][:200],
            "tool_calls": len(calls), "errors": sum(1 for e in calls if e.get("error")),
            "hook_blocks": sum(1 for e in evs if e["kind"] == "hook" and e.get("block")),
            "skills": [e["input"].get("skill") for e in calls if e["name"] == "Skill"],
            "units": tree, "tokens_main": main_tok,
            "tokens_units": add_tokens(*(u["tokens"] for u in units)),
            "files": files, "step_count": len(steps),
        }
        summary["tokens"] = add_tokens(main_tok, summary["tokens_units"])
        index_turns.append(summary)
        doc = {**summary, "unit": tid, "type": "turn", "description": summary["prompt_first_line"][:100],
               "spawner": "user", "models": main_facts["models"], "finished": True,
               "files_written": list(dict.fromkeys(f["path"] for f in files if f["op"] in ("write", "edit"))),
               "file_ops": ops, "prompt": prompt, "steps": steps, "return": reply}
        (out / "turns" / f"{tid}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    return index_turns


def workspace_for(path: Path, root: Path | None = None) -> Path:
    """`<root>/<project>/<id8>`, or the folder this session already has under root."""
    root = root or RUNS
    id8 = path.stem[:8]
    for old in sorted(root.glob(f"*/{id8}")):
        if (old / "index.json").exists():
            return old
    m = None
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if m := re.search(r'"cwd":\s*"([^"]+)"', line):
                break
    return root / project_name(m.group(1) if m else "") / id8


def view(plugin: str | None, agent: str, root: Path, sessions: str | None, branch: str | None,
         flat: bool = False) -> int:
    """Build each session into its workspace under root (`root/<id8>` when flat), then the
    cross-session page for one agent type."""
    if sessions:
        paths = [resolve(x.strip(), plugin) for x in sessions.split(",") if x.strip()]
    else:
        paths = [s["path"] for s in sessions_for(plugin, include_headless=True)
                 if s["branch"] is not None and fnmatch.fnmatchcase(s["branch"], branch)]
        if not paths:
            print(f"no session{f' of {plugin}' if plugin else ''} on a branch matching {branch}")
            return 1
    paths = list(dict.fromkeys(paths))
    workspaces, lines = [], []
    for path in paths:
        out = root / path.stem[:8] if flat else workspace_for(path, root)
        index = build(path, plugin, out, quiet=True)
        workspaces.append(out)
        n = sum(1 for u in index["units"] if flow.is_type(u, agent))
        lines.append(f"{path.stem[:8]} · {index['title']} · {index['branch'] or '—'} · {n} unit{'' if n == 1 else 's'} of {agent}")
    page = flow.write_view(root, workspaces, agent, dt.date.today().isoformat())
    print(page)
    for line in lines:
        print(line)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find")
    f.add_argument("--plugin")
    f.add_argument("--project")
    f.add_argument("--words", nargs="+", default=[])
    f.add_argument("--limit", type=int, default=8)
    f.add_argument("--all", action="store_true", help="include headless runs in temp dirs (eval harnesses)")
    fl = sub.add_parser("flow")
    fl.add_argument("out")
    fl.add_argument("--issues", help=argparse.SUPPRESS)
    w = sub.add_parser("ws")
    w.add_argument("session")
    w.add_argument("--plugin")
    w.add_argument("--project")
    b = sub.add_parser("build")
    b.add_argument("session")
    b.add_argument("--plugin")
    b.add_argument("--project")
    b.add_argument("--out")
    b.add_argument("--full", action="store_true")
    v = sub.add_parser("view")
    v.add_argument("--plugin")
    v.add_argument("--agent", required=True)
    v.add_argument("--root", default=str(RUNS))
    v.add_argument("--flat", action="store_true", help="build each session into ROOT/<id8>/, not ROOT/<project>/<id8>/")
    which = v.add_mutually_exclusive_group(required=True)
    which.add_argument("--sessions")
    which.add_argument("--branch")
    a = ap.parse_args()

    if a.cmd == "find":
        me = current_session()
        hits = [s for s in sessions_for(a.plugin, include_headless=a.all, project=a.project)
                if all(w.lower() in s["title"].lower() for w in a.words)]
        if not hits:
            print(f"no session under {PROJECTS}" + (f" used {a.plugin}" if a.plugin else "") + " matches")
            return 1
        for s in hits[: a.limit]:
            print(describe(s) + ("  ← this chat" if s["id"] == me else ""))
        return 0

    if a.cmd == "flow":
        print(flow.write_html(Path(a.out), Path(a.issues) if a.issues else None))
        return 0

    if a.cmd == "ws":
        print(workspace_for(resolve(a.session, a.plugin, a.project)))
        return 0

    if a.cmd == "view":
        return view(a.plugin, a.agent, Path(a.root).expanduser(), a.sessions, a.branch, a.flat)

    if a.full:
        for k in LIMITS:
            LIMITS[k] *= 5
    path = resolve(a.session, a.plugin, a.project)
    build(path, a.plugin, Path(a.out).expanduser() if a.out else workspace_for(path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
