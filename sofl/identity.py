"""Host normalisation and account resolution for CRM activity exports (slice 2 of revenue-signal-router).

v2 fix of the slice-1 parse-order bug. v1 stripped the URL scheme first and split on "@" second, so the
messy export value `user@https://WWW.iris.example./pricing` became the host `https`. v2 peels the value in a
loop: strip a scheme if one starts the string, take the authority (up to the first / ? # or backslash),
and if the authority holds an "@", keep everything after that "@" and go round again.
A value is never resolved by guessing: anything that does not yield a plausible host returns "".
"""
from __future__ import annotations

import re

from .untrusted import clean_invisible

PERSONAL = {"gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com", "hotmail.co.uk", "outlook.com",
            "live.com", "icloud.com", "me.com", "aol.com", "proton.me", "protonmail.com", "gmx.de", "web.de", "mail.com"}
SECOND_LEVEL = {"co.uk", "org.uk", "ac.uk", "com.au", "co.nz", "co.jp", "com.br", "co.in", "co.za", "com.sg"}
_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:(//)?")
_HOST_OK = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def norm_host(value: str) -> str:
    s = clean_invisible(str(value or "")).strip().lower()
    m = re.search(r"<([^<>]+)>", s)          # "Jane Doe <jane@acme.example>"
    if m:
        s = m.group(1).strip()
    s = s.strip("\"'()[],;")
    for _ in range(6):
        sm = _SCHEME.match(s)
        if sm and (sm.group(1) or s.startswith("mailto:")):
            s = s[sm.end():]
            continue
        authority = re.split(r"[/?#\\]", s, maxsplit=1)[0]
        if "@" in authority:
            s = s[s.index("@") + 1:]
            continue
        break
    s = re.split(r"[/?#\\]", s, maxsplit=1)[0]
    s = re.sub(r":\d+$", "", s).strip().strip(".")
    if s.startswith("www."):
        s = s[4:]
    return s if _HOST_OK.match(s) else ""


def registrable(host: str) -> str:
    parts = [p for p in host.split(".") if p]
    if len(parts) >= 3 and ".".join(parts[-2:]) in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


class Resolver:
    """account_id from an explicit id, else from the host of an email/domain/url value, else None (review)."""

    def __init__(self, accounts: dict[str, dict]):
        self.accounts = accounts
        self.by_domain, self.by_alias = {}, {}
        for a in accounts.values():
            if a.get("domain"):
                self.by_domain[norm_host(a["domain"])] = a["account_id"]
            for al in a.get("aliases", []):
                self.by_alias[norm_host(al)] = a["account_id"]

    def lookup_host(self, host: str):
        if host in self.by_domain:
            return self.by_domain[host], "domain"
        if host in self.by_alias:
            return self.by_alias[host], "alias"
        reg = registrable(host)
        if reg != host:
            if reg in self.by_domain:
                return self.by_domain[reg], "subdomain"
            if reg in self.by_alias:
                return self.by_alias[reg], "subdomain_alias"
        return None, None

    def resolve(self, ref: dict) -> dict:
        aid = str(ref.get("account_id") or "").strip().lower()
        if aid in self.accounts:
            return {"account_id": aid, "method": "crm_id"}
        if aid:
            return {"account_id": None, "method": "unresolved", "reason": "unknown_account_id"}
        for field in ("email", "domain", "url"):
            host = norm_host(ref.get(field) or "")
            if not host:
                continue
            if host in PERSONAL:
                return {"account_id": None, "method": "unresolved", "reason": "personal_email"}
            found, method = self.lookup_host(host)
            if found:
                return {"account_id": found, "method": method}
            return {"account_id": None, "method": "unresolved", "reason": "unknown_domain"}
        return {"account_id": None, "method": "unresolved", "reason": "no_reference"}
