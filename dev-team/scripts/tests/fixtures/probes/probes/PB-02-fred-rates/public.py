"""PB-02 — the agent's check (C1): FRED's public series page, no key."""
import json
import urllib.request

SERIES = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"


def c1_series_exists():
    """The DTB3 series serves daily rows (first line is the header)."""
    with urllib.request.urlopen(SERIES, timeout=60) as r:
        header = r.readline().decode().strip()
    return {"header": header.split(",")}


if __name__ == "__main__":
    print(json.dumps(c1_series_exists()))
