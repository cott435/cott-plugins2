"""PL-01 steps: read raw rows, apply the universe."""


def read_raw(path, start, end):
    return [line.split(",") for line in open(path)][1:]


def apply_universe(rows, start, end):
    return [r for r in rows if start <= r[0] <= end]
