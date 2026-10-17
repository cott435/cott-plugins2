# PB-01: Sharadar delivers what the DATA- requirements need

Run by you (every check needs your Sharadar key). Spends API calls on your subscription only.

1. Copy `.env.example` to `.env` and put your key in it. Never paste it in chat.
2. `delisted_members.csv` is your list of former S&P 500 members that delisted.
3. `cd probes/PB-01-sharadar && python3 probe.py` (about a minute). It writes `evidence/` and keeps raw rows in `out/`.
4. Say "ran it".
