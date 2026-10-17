"""PB-02 — run by you: parses out/statement.ofx; counts only reach evidence."""
import re

from probe_kit import load_env, private, record, write_evidence

ROW = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.S)


def rows(name):
    text = private(name).read_text()
    return [dict(re.findall(r"<(\w+)>([^<\r\n]*)", block)) for block in ROW.findall(text)]


if __name__ == "__main__":
    load_env(["CCU_OFX_PASSWORD"])
    now = rows("statement.ofx")
    need = ("DTPOSTED", "TRNAMT", "NAME", "FITID")
    record("C1", {"rows": len(now), "complete": sum(all(k in r for k in need) for r in now)},
           passed=bool(now) and all(all(k in r for k in need) for r in now))
    prev = {r.get("FITID") for r in rows("statement-prev.ofx")}
    record("C2", {"overlap": len(prev & {r.get("FITID") for r in now})}, passed=bool(prev))
    write_evidence("PB-02", "user")
