# PB-02: Canary Credit Union's OFX export

Run by you.
1. Download the last two monthly OFX exports from online banking; save them as `out/statement.ofx` and `out/statement-prev.ofx`.
2. Copy `.env.example` to `.env` and put your online-banking password in it (the script only uses it to check it never reaches evidence).
3. `cd probes/PB-02-ofx-export && python3 probe.py`, then say "ran it".
