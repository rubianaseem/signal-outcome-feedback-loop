"""The slice-1 host parser (revenue-signal-router rsr/identity.py norm_host), kept verbatim as the evaluation baseline."""
import re


def norm_host_v1(value: str) -> str:
    s = (value or "").strip().lower()
    s = re.sub(r"^[a-z][a-z0-9+.-]*://", "", s)
    s = s.split("@")[-1]
    s = re.split(r"[/?#]", s, maxsplit=1)[0]
    s = s.split(":")[0].strip().strip(".")
    if s.startswith("www."):
        s = s[4:]
    return s
