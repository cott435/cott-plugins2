"""Reading pyproject.toml: tomllib on Python ≥ 3.11, else a small reader that is enough for the keys
`dt status` checks (tables, arrays of tables, dotted keys, numbers, booleans, strings, arrays of scalars)."""
from __future__ import annotations

import re
from pathlib import Path


def load_toml(path: Path) -> dict:
    try:
        import tomllib  # type: ignore[import-not-found]
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        return parse_toml(path.read_text(encoding="utf-8"))


def parse_toml(text: str) -> dict:
    """The fallback reader. Inline tables and multi-line strings are not supported."""
    data: dict = {}
    table = data
    pending = ""                      # a multi-line array being collected
    for raw in text.splitlines():
        line = _strip_comment(raw).strip()
        if pending:
            pending += " " + line
            if pending.count("[") > pending.count("]"):
                continue
            line, pending = pending, ""
        elif not line:
            continue
        m = re.match(r"^(\[\[?)\s*([^\]]+?)\s*\]\]?$", line)
        if m:
            parts = _key(m.group(2))
            parent = data
            for part in parts[:-1]:
                parent = parent.setdefault(part, {})
                if isinstance(parent, list):
                    parent = parent[-1]
            if m.group(1) == "[[":
                table = {}
                parent.setdefault(parts[-1], []).append(table)
            else:
                table = parent.setdefault(parts[-1], {})
                if isinstance(table, list):
                    table = table[-1]
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value.startswith("[") and value.count("[") > value.count("]"):
            pending = line
            continue
        parts = _key(key)
        t = table
        for part in parts[:-1]:
            t = t.setdefault(part, {})
        t[parts[-1]] = _value(value)
    return data


def _strip_comment(line: str) -> str:
    """Drop a `#` comment that isn't inside a quoted string."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i]
    return line


def _key(key: str) -> list[str]:
    return [p.strip().strip('"').strip("'") for p in re.findall(r'"[^"]*"|\'[^\']*\'|[^.]+', key.strip())]


def _value(value: str):
    if value.startswith("["):
        items = re.findall(r'"[^"]*"|\'[^\']*\'|[^,\[\]\s][^,\[\]]*', value)
        return [_value(i.strip()) for i in items if i.strip()]
    if value in ("true", "false"):
        return value == "true"
    if re.fullmatch(r"[+-]?\d[\d_]*", value):
        return int(value.replace("_", ""))
    if re.fullmatch(r"[+-]?\d[\d_]*\.\d+(?:[eE][+-]?\d+)?", value):
        return float(value.replace("_", ""))
    if value[:1] in "\"'":
        return value[1:-1]
    return value
