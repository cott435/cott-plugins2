#!/usr/bin/env python3
"""Check one plugin: the rules every plugin here meets, then the claims it declares.

Built in, with nothing to declare:

  purpose      PURPOSE.md exists
  sizes        no definition is over its word limit (LIMITS, below), no description over
               its character limit
  frontmatter  every skill and agent frontmatter key is one the platform documents, and
               none is a key plugin agents ignore; no description holds an XML-style tag
  version      plugin.json, the marketplace row and the newest CHANGELOG heading agree
  flow page    a plugin with an agent or a workflow skill has site/flow.md, a `flow:` block
               in site/site.yml and a `flow` claim in contracts.yml, and every workflow
               skill has its page, site/workflows/<skill>.md
  modes        a skill with modes lists them in a `## Modes` table; each row that does work
               names its own references/<mode>.md, which exists and no other row names; a
               row that names no file only stops; no SKILL.md heading holds a mode's process

Declared in the plugin's `contracts.yml` (optional; the check-contracts skill has the schema):

  forbid        a pattern that must not appear in an authored file
  headings      every heading a reader names is one the owner's template defines
  names_listed  every directory under <dirs> is named in <file>, and nothing else is
  flow          the `flow:` block of site/site.yml, which the site's flow page is drawn
                from, agrees with the files of the roles, drivers and hooks it names
  limits        a higher word limit for one file, with the reason

Usage:  python3 check.py [plugin dir] [--quiet]
Exits 1 if anything fails, 0 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Word limits per kind of file, counted after the frontmatter. The one place they are set:
# the SessionStart hook prints them from here.
LIMITS = {
    "skill": 800,        # skills/*/SKILL.md
    "agent": 1000,       # agents/*.md
    "reference": 1500,   # any other .md under skills/
    "purpose": 300,      # PURPOSE.md
    "claude": 400,       # CLAUDE.md
}
DESCRIPTION_CHARS = 500

SKILL_KEYS = {"name", "description", "when_to_use", "argument-hint", "arguments",
              "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
              "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
              "metadata", "license", "compatibility"}
AGENT_KEYS = {"name", "description", "tools", "disallowedTools", "model", "maxTurns", "skills",
              "memory", "background", "omitClaudeMd", "effort", "isolation", "color",
              "experimental"}
AGENT_IGNORED = {"hooks", "mcpServers", "permissionMode", "initialPrompt"}

DEFAULT_FILES = ["agents/*.md", "skills/**/*.md", "skills/**/*.py", "scripts/*.py",
                 "hooks/*.py", "README.md", "CLAUDE.md", "PURPOSE.md", "protocol.md"]


def plugin_root(start: str | Path) -> Path | None:
    """The nearest directory at or above `start` that holds .claude-plugin/plugin.json."""
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        if (d / ".claude-plugin" / "plugin.json").is_file():
            return d
    return None


def split(path: Path) -> tuple[str, str]:
    """(frontmatter, body) of a Markdown file; the frontmatter is "" when it has none."""
    text = path.read_text(errors="ignore")
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    return (m.group(1), text[m.end():]) if m else ("", text)


def description(head: str) -> str:
    """The `description:` value, read by line: one with a colon in it is not valid YAML."""
    m = re.search(r"^description:[ \t]*(.*(?:\n[ \t]+.*)*)", head, re.M)
    return " ".join(m.group(1).split()).lstrip(">|-").strip() if m else ""


def kind_of(root: Path, path: Path) -> str | None:
    """Which LIMITS key a file falls under, or None when it has no limit."""
    rel = path.resolve().relative_to(root).as_posix()
    if rel in ("PURPOSE.md", "CLAUDE.md"):
        return "purpose" if rel == "PURPOSE.md" else "claude"
    if re.fullmatch(r"skills/[^/]+/SKILL\.md", rel):
        return "skill"
    if re.fullmatch(r"agents/[^/]+\.md", rel):
        return "agent"
    return "reference" if rel.startswith("skills/") and rel.endswith(".md") else None


def declared(root: Path) -> dict:
    config = root / "contracts.yml"
    if not config.exists():
        return {}
    try:
        import yaml
    except ImportError:
        raise LookupError("contracts.yml needs PyYAML: pip install pyyaml")
    return yaml.safe_load(config.read_text()) or {}


def size_problems(root: Path, files: list[Path] | None = None) -> list[str]:
    """One line per file over its limit. `files` narrows the check to those paths."""
    raised, problems = {}, []
    for o in declared(root).get("limits") or []:
        if not str(o.get("why") or "").strip():
            problems.append(f"contracts.yml: the limit for {o.get('file')} gives no `why`")
        raised[o.get("file")] = int(o.get("words", 0))
    if files is None:
        files = [p for g in ("PURPOSE.md", "CLAUDE.md", "agents/*.md", "skills/**/*.md")
                 for p in sorted(root.glob(g))]
    for p in files:
        kind = kind_of(root, p) if p.is_file() else None
        if not kind:
            continue
        rel = p.resolve().relative_to(root).as_posix()
        head, body = split(p)
        words, limit = len(body.split()), raised.get(rel, LIMITS[kind])
        if words > limit:
            problems.append(f"{rel}: {words} words, the limit for a {kind} file is {limit}. "
                            f"Cut {words - limit}: drop what the reader can do without, "
                            f"merge what repeats, or move detail to a references/ file")
        chars = len(description(head))
        if kind in ("skill", "agent") and chars > DESCRIPTION_CHARS:
            problems.append(f"{rel}: description is {chars} characters, the limit is "
                            f"{DESCRIPTION_CHARS}")
    return problems


def check_purpose(root: Path) -> list[str]:
    return [] if (root / "PURPOSE.md").is_file() else [
        "no PURPOSE.md: the plugin's goal is agreed with the user and written there first"]


def check_flow_page(root: Path) -> list[str]:
    """A plugin with an agent or a workflow skill maps itself: the flow page, the block it is
    drawn from, and the claim that holds the block to the files."""
    workflow = [p for p in sorted(root.glob("skills/*/SKILL.md"))
                if re.search(r"^disable-model-invocation:\s*true\s*$", split(p)[0], re.M)]
    if not workflow and not list(root.glob("agents/*.md")):
        return []
    fix = "the build-site skill's references/flow.md has the fields"
    problems = []
    if not (root / "site/flow.md").exists():
        problems.append(f"site/flow.md is missing: copy plugin-dev's templates/site/flow.md and fill it; {fix}")
    cfg = root / "site/site.yml"
    if not cfg.exists() or not re.search(r"^flow:", cfg.read_text(), re.M):
        problems.append(f"site/site.yml has no `flow:` block; {fix}")
    if not declared(root).get("flow"):
        problems.append("contracts.yml declares no `flow` claim, so nothing holds the flow page to the files")
    for p in workflow:
        page = f"site/workflows/{p.parent.name}.md"
        if not (root / page).exists():
            problems.append(f"{page} is missing: the workflow's flow chart and its steps explained; "
                            f"the build-site skill's references/workflow-page.md has the shape")
    return problems


def check_frontmatter(root: Path) -> list[str]:
    problems = []
    for glob, allowed, ignored, kind in (("skills/*/SKILL.md", SKILL_KEYS, set(), "skill"),
                                         ("agents/*.md", AGENT_KEYS, AGENT_IGNORED, "agent")):
        for p in sorted(root.glob(glob)):
            rel = p.relative_to(root)
            head, _ = split(p)
            if not head:
                problems.append(f"{rel}: no frontmatter")
                continue
            for n, line in enumerate(head.splitlines(), 2):
                m = re.match(r"([A-Za-z_][\w-]*)\s*:", line)
                if m and m.group(1) in ignored:
                    problems.append(f"{rel}:{n} `{m.group(1)}` is ignored for plugin {kind}s")
                elif m and m.group(1) not in allowed:
                    problems.append(f"{rel}:{n} `{m.group(1)}` is not a documented {kind} field")
            if not description(head):
                problems.append(f"{rel}: no description")
            # claude.ai rejects the whole plugin for a <word> in a description; the CLI does not.
            if re.search(r"<[A-Za-z/]", description(head)):
                problems.append(f"{rel}: description holds an XML-style tag; write {{word}}")
    return problems


def check_version(root: Path) -> list[str]:
    problems = []
    manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text())
    name, version = manifest.get("name"), manifest.get("version")
    if name != root.name:
        problems.append(f"plugin.json names `{name}`, the directory is `{root.name}`")
    market = root.parent / ".claude-plugin" / "marketplace.json"
    if market.is_file():
        rows = [r for r in json.loads(market.read_text()).get("plugins", []) if r.get("name") == name]
        if not rows:
            problems.append(f"no row for `{name}` in {market.parent.parent.name}'s marketplace.json")
        elif rows[0].get("version") != version:
            problems.append(f"plugin.json is {version}, its marketplace row is {rows[0].get('version')}")
    log = root / "CHANGELOG.md"
    newest = re.search(r"^## \[([^\]]+)\]", log.read_text(), re.M) if log.is_file() else None
    if not newest or newest.group(1) != version:
        problems.append(f"plugin.json is {version}, the newest CHANGELOG heading is "
                        f"{newest.group(1) if newest else 'missing'}")
    return problems


MODE_HEADING = re.compile(r"^##+ .*\bmodes\b", re.I | re.M)
MODE_MENTION = re.compile(r"\b(New|Extend|Revise|Replan|Grow|Sync) mode\b")


def mode_rows(body: str) -> list[tuple[int, str, str]] | None:
    """(line, mode, row text) per row of the `## Modes` table; None with no such heading."""
    m = MODE_HEADING.search(body)
    if not m:
        return None
    rows, lines = [], body[m.end():].split("\n")
    start = body[:m.end()].count("\n") + 1
    for n, line in enumerate(lines[1:], start + 1):
        if line.startswith("#"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if cells and not re.fullmatch(r"[-: ]+", cells[0]) and cells[0].lower() != "mode":
            rows.append((n, md_plain(cells[0]), line))
    return rows


def md_plain(cell: str) -> str:
    return re.sub(r"[*_`]", "", cell).strip()


def check_modes(root: Path) -> list[str]:
    """protocol.md, A skill is its role, plus one file per mode."""
    problems = []
    for p in sorted(root.glob("skills/*/SKILL.md")):
        rel, body = p.relative_to(root).as_posix(), split(p)[1]
        offset = split(p)[0].count("\n") + 3 if split(p)[0] else 0
        rows = mode_rows(body)
        if rows is None:
            if MODE_MENTION.search(body):
                problems.append(f"{rel}: names modes but has no `## Modes` table; list each "
                                f"mode there, its work in references/<mode>.md")
            continue
        if not rows:
            problems.append(f"{rel}: the Modes section has no table; one row per mode, each "
                            f"naming its references/<mode>.md")
        seen: dict[str, str] = {}
        for n, mode, line in rows:
            refs = sorted(set(re.findall(r"references/[\w./-]+\.md", line)))
            where = f"{rel}:{n + offset} {mode}"
            if not refs:
                if not re.search(r"\bstop\b", line, re.I):
                    problems.append(f"{where}: the mode does work but names no file; move it to "
                                    f"references/{slug(mode)}.md")
                continue
            if len(refs) > 1:
                problems.append(f"{where}: names {', '.join(refs)}; a mode has one file")
            for ref in refs:
                if not (p.parent / ref).is_file():
                    problems.append(f"{where}: {ref} does not exist")
                if ref in seen:
                    problems.append(f"{where}: {ref} is also {seen[ref]}'s file; one file per mode")
                seen.setdefault(ref, mode)
                if Path(ref).stem != slug(mode):
                    problems.append(f"{where}: {ref} should be references/{slug(mode)}.md")
        for m in re.finditer(r"^#+ .*\((" + "|".join(re.escape(r[1]) for r in rows) + r")\)",
                             body, re.M) if rows else ():
            problems.append(f"{rel}:{body[:m.start()].count(chr(10)) + 1 + offset} heading "
                            f"`{m.group(0).lstrip('# ')}` holds a mode's process; it belongs in "
                            f"references/{slug(m.group(1))}.md")
    return problems


def slug(mode: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", mode.lower()).strip("-")


def authored(root: Path, globs: list[str]) -> list[Path]:
    """Every existing file matching any glob, once, in a stable order."""
    return list(dict.fromkeys(p for g in globs for p in sorted(root.glob(g)) if p.is_file()))


def span(text: str, bounds: list | None, where: str) -> str:
    """The slice of text between two literal markers. bounds is [start, end]; end may be null."""
    if not bounds:
        return text
    start, end = (bounds + [None])[:2]
    if start not in text:
        raise LookupError(f"{where}: marker not found: {start!r}")
    i = text.index(start)
    if not end:
        return text[i:]
    if end not in text[i:]:
        raise LookupError(f"{where}: end marker not found after start: {end!r}")
    return text[i:text.index(end, i)]


def check_forbid(root: Path, spec: dict) -> list[str]:
    """A match of `pattern` (with every `all_of` in scope) fails unless an `unless` is in scope.

    Scope is the whole line, or with `near: <n>` the matched text plus n characters either
    side, so an exemption pardons the occurrence it describes and not the rest of its line.
    """
    pattern = re.compile(spec["pattern"])
    unless = [re.compile(u) for u in spec.get("unless", [])]
    all_of, near, hits = spec.get("all_of", []), spec.get("near"), []
    for p in authored(root, spec.get("files", DEFAULT_FILES)):
        for n, line in enumerate(p.read_text(errors="ignore").splitlines(), 1):
            for m in pattern.finditer(line):
                scope = line if not near else line[max(0, m.start() - near):m.end() + near]
                if any(a not in scope for a in all_of) or any(u.search(scope) for u in unless):
                    continue
                hits.append(f"{p.relative_to(root)}:{n}")
                break
    return hits


def check_headings(root: Path, spec: dict) -> list[str]:
    """Every name in a reader's `cites` is a `##` heading of the owner (within `owner_span`)."""
    block = span((root / spec["owner"]).read_text(), spec.get("owner_span"), spec["owner"])
    block = re.sub(r"(?ms)^```.*?^```", "", block)
    owned = {" ".join(m.group(1).split()).lower() for m in re.finditer(r"^## (.+?)\s*$", block, re.M)}
    if not owned:
        return [f"{spec['owner']}: no `##` headings in the owner span"]
    problems = []
    for r in spec["readers"]:
        text = (root / r["file"]).read_text()
        for c in r.get("cites", []):
            if " ".join(c.split()).lower() not in owned:
                problems.append(f"{r['file']} names '{c}', which {spec['owner']} does not define")
            elif c not in text:
                problems.append(f"contracts.yml cites '{c}' for {r['file']}, which never names it")
    return problems


# How a list cites a name: in backticks anywhere, or as a bullet on its own line.
FORMS = {
    "code": (r"`{n}`", r"`([a-z][a-z0-9-]{2,})`"),
    "list": (r"(?m)^ *- +{n} *(?:#.*)?$", r"(?m)^ *- +([a-z][a-z0-9-]+) *(?:#.*)?$"),
}


def check_names_listed(root: Path, spec: dict) -> list[str]:
    """Every directory matching `dirs` is named in `file` (within `span`), and no other name is."""
    block = span((root / spec["file"]).read_text(), spec.get("span"), spec["file"])
    form = spec.get("form", "code")
    if form not in FORMS:
        return [f"unknown form {form!r}; known: {', '.join(FORMS)}"]
    cite, existing = FORMS[form]
    names = sorted(p.name for p in root.glob(spec["dirs"].rstrip("/")) if p.is_dir())
    if not names:
        return [f"`dirs: {spec['dirs']}` matched no directory"]
    missing = [n for n in names if not re.search(cite.format(n=re.escape(n)), block)]
    extra = sorted({w for w in re.findall(existing, block) if w not in names})
    return ([f"not listed in {spec['file']}: {', '.join(missing)}"] if missing else []) + \
           ([f"listed in {spec['file']} with no such directory: {', '.join(extra)}"] if extra else [])


def actors(value) -> list[str]:
    """The names in a `flow:` list: plain names, or the keys of `{name: note}` mappings."""
    out: list[str] = []
    for v in value if isinstance(value, list) else [value] if value else []:
        out += [str(k) for k in v] if isinstance(v, dict) else [str(v)]
    return out


def mention(token: str, literal: bool = False) -> str:
    """A path or name as a pattern. In a path, `<x>`, `{x}`, `*` and `…` stand for anything
    without a space, so `plans/{slug}/x.md` finds `plans/<slug>/x.md`. A `match` string is
    looked for as written."""
    token = token.strip("`")
    pieces = [token] if literal else re.split(r"<[^>]*>|\{[^}]*\}|…|\*", token)
    start = r"(?<![\w-])" if token[:1].isalnum() else ""
    return start + r"[^\s`'\"]*?".join(re.escape(x) for x in pieces)


def first_line(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    return text.count("\n", 0, m.start()) + 1 if m else 0


EVENTS = {"PreToolUse", "PostToolUse", "Stop", "SubagentStop", "SubagentStart", "SessionStart",
          "SessionEnd", "UserPromptSubmit", "PreCompact", "Notification"}


def check_flow(root: Path, spec: dict) -> list[str]:
    """The `flow:` block agrees with the plugin's own files.

    A role's file is `agents/<id>.md`, `skills/<id>/SKILL.md`, or the `file:` its entry
    gives. Every claim is about what that file names:

      roles      every agent is a role
      skills     a model-loadable skill the file names is in the role's `always`,
                 `sometimes` or `names`, or its agent's `skills:` frontmatter, and each of
                 those lists names only skills the file names
      documents  a role in a document's `writes` or `reads` names the document (by `path`,
                 or by a `match` string taken as written), and a role that names it is in
                 `writes`, `reads` or `names`. `match: false` leaves a document unchecked.
                 A role with `relays: true` hands paths on: what it names beyond its own
                 lists is not held against it
      drivers    `skill` is a skill; every `x.py` a driver names exists, and one named in
                 `next` or `writer` is named in the driver's file
      hooks      every script wired in hooks/hooks.json is named in a driver's `held` or
                 in `flow.hooks`, and a hook named in either is wired to the event given
    """
    import yaml
    rel = spec.get("file", "site/site.yml")
    flow = (yaml.safe_load((root / rel).read_text()) or {}).get("flow") or {}
    if not flow:
        return [f"{rel} has no `flow:` block"]
    problems: list[str] = []
    agents = {x.stem: x for x in sorted(root.glob("agents/*.md"))}
    skills = {x.parent.name: x for x in sorted(root.glob("skills/*/SKILL.md"))}
    loadable = {n for n, x in skills.items()
                if not re.search(r"^disable-model-invocation:\s*true\s*$", split(x)[0], re.M)}

    roles: dict[str, tuple[str, str, str] | None] = {}     # id -> (file, frontmatter, body)
    relays: set[str] = set()
    for entry in flow.get("roles") or list(agents):
        e = entry if isinstance(entry, dict) else {"id": entry}
        rid = str(e["id"])
        path = root / e["file"] if e.get("file") else agents.get(rid) or skills.get(rid)
        if path is not None and not path.is_file():
            problems.append(f"role {rid}: `file: {e['file']}` does not exist")
            path = None
        if path:
            # The frontmatter is blanked, not cut, so a line number is the file's own.
            body = re.sub(r"\A---\n.*?\n---\n", lambda m: "\n" * m.group(0).count("\n"),
                          path.read_text(), flags=re.S)
            roles[rid] = (path.relative_to(root).as_posix(), split(path)[0], body)
        else:
            roles[rid] = None
        if e.get("relays"):
            relays.add(rid)
    problems += [f"agents/{a}.md is not in flow.roles" for a in agents if a not in roles]

    uses = flow.get("uses") or {}
    problems += [f"flow.uses.{rid}: no such role" for rid in uses if rid not in roles]
    for rid, src in roles.items():
        use = uses.get(rid) or {}
        placed = set(actors(use.get("always"))) | set(actors(use.get("sometimes"))) \
            | set(actors(use.get("names")))
        problems += [f"flow.uses.{rid}: `{s}` is not a skill of this plugin"
                     for s in sorted(placed - set(skills))]
        if src is None:
            continue
        path, head, body = src
        m = re.search(r"^skills:[ \t]*(.*(?:\n[ \t]+-.*)*)", head, re.M)
        preloaded = set(re.findall(r"[\w:-]+", m.group(1))) if m else set()
        found = {s: first_line(body, rf"(?<![\w-]){re.escape(s)}(?![\w-])") for s in skills if s != rid}
        for s in sorted(loadable):
            if found.get(s) and s not in placed | preloaded:
                problems.append(f"{path}:{found[s]} names `{s}`, which flow.uses.{rid} does not "
                                f"place (always, sometimes or names)")
        problems += [f"flow.uses.{rid} lists `{s}`, which {path} never names"
                     for s in sorted(placed & set(skills)) if not found.get(s)]

    for d in flow.get("documents") or []:
        name, match = d.get("name", "?"), d.get("match", d.get("path"))
        touch = set(actors(d.get("writes"))) | set(actors(d.get("reads")))
        named = set(actors(d.get("names")))
        if not match:
            continue
        tokens = [str(t) for t in match] if isinstance(match, list) else [str(match)]
        pattern = "|".join(f"(?:{mention(t, literal='match' in d)})" for t in tokens)
        problems += [f"flow.documents `{name}`: names lists `{rid}`, which is not a role"
                     for rid in sorted(named - set(roles))]
        for rid, src in roles.items():
            if src is None:
                continue
            line = first_line(src[2], pattern)
            if line and rid not in touch | named | relays and "all" not in touch:
                problems.append(f"{src[0]}:{line} names `{name}`, and {rid} is not in its "
                                f"writes, reads or names")
            if not line and rid in touch | named:
                problems.append(f"flow.documents `{name}` lists {rid}, and {src[0]} never names "
                                f"it (by {', '.join(tokens)})")

    hook_scripts = {x.name for x in root.glob("hooks/*.py")}
    scripts = hook_scripts | {x.name for g in ("scripts/*.py", "skills/*/scripts/*.py") for x in root.glob(g)}
    wired: dict[str, set[str]] = {}
    hooks_file = root / "hooks" / "hooks.json"
    if hooks_file.exists():
        for event, groups in (json.loads(hooks_file.read_text()).get("hooks") or {}).items():
            for h in (h for group in groups for h in group.get("hooks") or []):
                for word in re.findall(r"[\w-]+\.py", " ".join([h.get("command", ""), *(h.get("args") or [])])):
                    wired.setdefault(word, set()).add(event)
    held: list[tuple[str, set[str], list[str]]] = []      # (where, hook scripts, events)
    for d in flow.get("drivers") or []:
        sid = str(d.get("skill"))
        if sid not in skills:
            problems.append(f"flow.drivers: `{sid}` is not a skill of this plugin")
            continue
        body = skills[sid].read_text()
        for key in ("ledger", "next", "writer", "held", "spawns", "returns"):
            for word in re.findall(r"[\w-]+\.py", str(d.get(key, ""))):
                if word not in scripts:
                    problems.append(f"flow.drivers.{sid}.{key}: `{word}` is not a script or hook of this plugin")
                elif key in ("next", "writer") and word not in body:
                    problems.append(f"flow.drivers.{sid}.{key}: skills/{sid}/SKILL.md never names `{word}`")
        text = str(d.get("held", ""))
        held.append((f"flow.drivers.{sid}.held", set(re.findall(r"[\w-]+\.py", text)) & hook_scripts,
                     re.findall(r"\w+", text)))
    for h in flow.get("hooks") or []:
        held.append((f"flow.hooks `{h.get('script')}`", {str(h.get("script"))},
                     re.findall(r"\w+", str(h.get("event", "")))))
    for where, names, events in held:
        for word in sorted(names):
            if word not in wired:
                problems.append(f"{where}: `{word}` is not wired in hooks/hooks.json")
        for event in events:
            if event in EVENTS and not any(event in wired.get(w, ()) for w in names):
                problems.append(f"{where}: no hook named there is wired to `{event}`")
    problems += [f"hooks/hooks.json wires `{word}`, which neither a driver's `held` nor flow.hooks names"
                 for word in sorted(set(wired) - {w for _, names, _ in held for w in names})]
    return problems


DECLARED = {"forbid": check_forbid, "headings": check_headings, "names_listed": check_names_listed,
            "flow": check_flow}


def run(root: Path) -> list[tuple[str, list[str]]]:
    """Every check as (name, problems); an empty list is a pass."""
    rows = [("purpose", check_purpose(root)), ("frontmatter", check_frontmatter(root)),
            ("version", check_version(root))]
    try:
        rows.insert(1, ("sizes", size_problems(root)))
        claims = declared(root)
        rows.append(("flow page", check_flow_page(root)))
        rows.append(("modes", check_modes(root)))
    except LookupError as e:
        return rows + [("contracts.yml", [str(e)])]
    for kind, specs in claims.items():
        if kind == "limits":
            continue
        if kind not in DECLARED:
            rows.append((kind, [f"unknown kind; known: {', '.join(DECLARED)}, limits"]))
            continue
        for spec in specs or []:
            try:
                rows.append((spec.get("name", kind), DECLARED[kind](root, spec)))
            except (LookupError, OSError, KeyError, re.error) as e:
                rows.append((spec.get("name", kind), [f"could not run: {e!r}"]))
    return rows


def report(root: Path, quiet: bool = False) -> tuple[bool, str]:
    """(passed, text) for one plugin; with `quiet` the text holds failures only."""
    rows = run(root)
    lines = []
    for name, problems in rows:
        if problems:
            lines.append(f"FAIL  {name}")
            lines += [f"      {p}" for p in problems]
        elif not quiet:
            lines.append(f"PASS  {name}")
    failed = sum(1 for _, problems in rows if problems)
    if not quiet or failed:
        lines.append(f"{root.name}: {len(rows) - failed}/{len(rows)} pass")
    return not failed, "\n".join(lines)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("Word limits: " + ", ".join(f"{k} {n}" for k, n in LIMITS.items())
              + f". Description: {DESCRIPTION_CHARS} characters.")
        return 0
    root = plugin_root(args[0] if args else ".")
    if root is None:
        print("no .claude-plugin/plugin.json at or above this directory")
        return 1
    ok, text = report(root, "--quiet" in sys.argv)
    if text:
        print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
