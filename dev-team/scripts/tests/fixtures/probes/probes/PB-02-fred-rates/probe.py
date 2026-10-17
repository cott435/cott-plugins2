"""PB-02 — run by you. FRED_API_KEY from .env; nothing is printed but counts."""
import os
import urllib.parse
import urllib.request


def c2_history():
    """Earliest DTB3 observation with your key."""
    q = urllib.parse.urlencode({"series_id": "DTB3", "api_key": os.environ["FRED_API_KEY"], "file_type": "json"})
    with urllib.request.urlopen(f"https://api.stlouisfed.org/fred/series/observations?{q}", timeout=60) as r:
        return r.status
