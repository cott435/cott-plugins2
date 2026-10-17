"""PB-01 — the agent's checks: Frankfurter needs no key. Reads no environment."""
import json, urllib.request

from probe_kit import record, write_evidence

BASE = "https://api.frankfurter.dev/v1"


def rate(day):
    with urllib.request.urlopen(f"{BASE}/{day}?from=EUR&to=USD", timeout=30) as r:
        return json.load(r)


if __name__ == "__main__":
    past = rate("2024-03-15")
    record("C1", {"rates": len(past.get("rates", {}))}, passed="USD" in past.get("rates", {}))
    weekend = rate("2024-03-16")
    record("C2", {"dated": weekend.get("date")}, passed=weekend.get("date") == "2024-03-15")
    write_evidence("PB-01", "agent", BASE)
