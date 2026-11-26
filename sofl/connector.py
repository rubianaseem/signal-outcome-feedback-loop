"""Read-only activity connector with a MOCK HubSpot-style and Salesforce-style source. No network, no credentials.

What is implemented and tested locally against the mock:
  - GET-only client: any other HTTP verb raises ReadOnlyViolation before anything is sent; the mock server counts any
    write it receives and the tests assert the count stays 0.
  - Cursor pagination (HubSpot `paging.next.after`, Salesforce `nextRecordsUrl`), a checkpoint file written atomically
    after every page, and resume after a crash that yields exactly the records of an uninterrupted run.
  - 429 with Retry-After (honoured, capped), 5xx with exponential backoff, a retry budget, then a clean failure.
  - Stale-snapshot detection: every page carries the snapshot version of the source. If it changes mid-run the
    run discards its partial output and restarts once; a second change fails the run. Pages from two snapshots are never mixed.
  - Records are normalised to one activity contract (docs/DATA_CONTRACTS.md).
What is NOT implemented: authentication, real HubSpot/Salesforce endpoints, field-level security, webhooks. Real
setup is described in SETUP.md and docs/DETAILS.md.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .util import write_json


class ReadOnlyViolation(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, retry_after):
        super().__init__("429")
        self.retry_after = retry_after


class ServerError(Exception):
    pass


class StaleSnapshot(Exception):
    pass


class SyncFailed(Exception):
    pass


class MockSource:
    """Serves synthetic activity records in pages. Faults are injected by call number so runs are reproducible."""

    def __init__(self, records: list[dict], flavour="hubspot", page_size=50, rate_limit_calls=(), error_calls=(), change_snapshot_at_call=None, retry_after=2):
        self.records, self.flavour, self.page_size = records, flavour, page_size
        self.rate_limit_calls, self.error_calls, self.change_at = set(rate_limit_calls), set(error_calls), change_snapshot_at_call
        self.retry_after = retry_after
        self.calls = 0
        self.writes_received = 0
        self.snapshot = "snap-1"

    def request(self, method: str, cursor: str | None):
        if method != "GET":
            self.writes_received += 1
            raise ReadOnlyViolation(method)
        self.calls += 1
        if self.change_at is not None and self.calls == self.change_at:
            self.snapshot = "snap-2"
        if self.calls in self.rate_limit_calls:
            raise RateLimited(self.retry_after)
        if self.calls in self.error_calls:
            raise ServerError("503")
        start = int(cursor or 0)
        chunk = self.records[start:start + self.page_size]
        nxt = start + self.page_size if start + self.page_size < len(self.records) else None
        if self.flavour == "hubspot":
            body = {"results": [{"id": r["activity_id"], "properties": r} for r in chunk], "snapshot": self.snapshot}
            if nxt is not None:
                body["paging"] = {"next": {"after": str(nxt)}}
        else:
            body = {"records": [{"Id": r["activity_id"], "Fields": r} for r in chunk], "done": nxt is None, "snapshot": self.snapshot}
            if nxt is not None:
                body["nextRecordsUrl"] = f"/services/data/v60.0/query/01gXX-{nxt}"
        return body


def _next_cursor(body: dict, flavour: str):
    if flavour == "hubspot":
        return (body.get("paging") or {}).get("next", {}).get("after")
    return None if body.get("done") else str(body["nextRecordsUrl"]).rsplit("-", 1)[-1]


def _normalise(body: dict, flavour: str) -> list[dict]:
    items = body["results"] if flavour == "hubspot" else body["records"]
    out = []
    for it in items:
        p = it["properties"] if flavour == "hubspot" else it["Fields"]
        if not isinstance(p, dict) or "type" not in p:
            raise ValueError("malformed record")
        out.append(dict(p))
    return out


class ReadOnlyClient:
    def __init__(self, source: MockSource, sleep=time.sleep, max_attempts=5, max_sleep=30.0, log=None):
        self.source, self.sleep, self.max_attempts, self.max_sleep, self.log = source, sleep, max_attempts, max_sleep, log or (lambda e: None)

    def get(self, cursor):
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.source.request("GET", cursor)
            except RateLimited as exc:
                wait = min(self.max_sleep, float(exc.retry_after))
                self.log({"event": "rate_limited", "attempt": attempt, "retry_after": wait})
                self.sleep(wait)
            except ServerError:
                wait = min(self.max_sleep, 0.5 * 2 ** (attempt - 1))
                self.log({"event": "server_error", "attempt": attempt, "backoff": wait})
                self.sleep(wait)
        raise SyncFailed("retry budget exhausted")

    def post(self, *a, **k):
        raise ReadOnlyViolation("this client has no write path; refused before any request is built")

    put = patch = delete = post


def sync(client: ReadOnlyClient, flavour: str, out_dir, crash_after_pages: int = 0, log=None) -> dict:
    """Pull every page into out_dir/activities.jsonl with a checkpoint. Re-run to resume. Returns a summary."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_path, data_path = out_dir / "checkpoint.json", out_dir / "activities.jsonl"
    log = log or (lambda e: None)
    restarts = 0
    while True:
        ck = json.loads(ck_path.read_text()) if ck_path.exists() else {"cursor": None, "pages": 0, "snapshot": None, "records": 0, "bytes": 0}
        if ck["pages"] > 0 and ck["cursor"] is None:   # previous run finished: start a fresh pull
            ck = {"cursor": None, "pages": 0, "snapshot": None, "records": 0, "bytes": 0}
            (out_dir / "DONE.json").unlink(missing_ok=True)
        if ck["pages"] == 0:
            data_path.write_text("")
        with open(data_path, "r+b") as fh:   # a crash between append and checkpoint must not leave a half page behind
            fh.truncate(ck.get("bytes", 0))
        pages_this_run = 0
        try:
            while True:
                body = client.get(ck["cursor"])
                snap = body.get("snapshot")
                if ck["snapshot"] and snap != ck["snapshot"]:
                    raise StaleSnapshot(f"{ck['snapshot']} -> {snap}")
                try:
                    recs = _normalise(body, flavour)
                except (ValueError, KeyError) as exc:
                    raise SyncFailed(f"malformed page after cursor {ck['cursor']}: {exc}")
                with open(data_path, "a", encoding="utf-8") as fh:
                    for r in recs:
                        fh.write(json.dumps(r, sort_keys=True) + "\n")
                ck = {"cursor": _next_cursor(body, flavour), "pages": ck["pages"] + 1, "snapshot": snap, "records": ck["records"] + len(recs), "bytes": data_path.stat().st_size}
                write_json(ck_path, ck)
                pages_this_run += 1
                if crash_after_pages and pages_this_run >= crash_after_pages and ck["cursor"] is not None:
                    raise KeyboardInterrupt("injected crash")
                if ck["cursor"] is None:
                    write_json(out_dir / "DONE.json", {"records": ck["records"], "pages": ck["pages"], "snapshot": snap})
                    return {"records": ck["records"], "pages": ck["pages"], "snapshot": snap, "restarts_after_stale_snapshot": restarts}
        except StaleSnapshot as exc:
            log({"event": "stale_snapshot", "detail": str(exc)})
            if restarts >= 1:
                raise SyncFailed("snapshot changed twice; refusing to mix pages from different snapshots")
            restarts += 1
            ck_path.unlink(missing_ok=True)
            data_path.unlink(missing_ok=True)
