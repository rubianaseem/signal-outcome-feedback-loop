"""Run the read-only sync against the MOCK source built from data/train/activities.csv."""
from __future__ import annotations

from pathlib import Path

from sofl.connector import MockSource, ReadOnlyClient, sync
from sofl.ingest import read_csv


def demo(root, out, flavour="hubspot", inject_429=2, crash_after_pages=0):
    recs = read_csv(Path(root) / "data/train/activities.csv")[:400]
    src = MockSource(recs, flavour, page_size=50, rate_limit_calls=range(2, 2 + inject_429))
    events, naps = [], []
    cl = ReadOnlyClient(src, sleep=naps.append, log=events.append)
    if crash_after_pages:
        try:
            sync(cl, flavour, out, crash_after_pages=crash_after_pages)
        except KeyboardInterrupt:
            print(f"injected crash after {crash_after_pages} pages; resuming from checkpoint")
    res = sync(cl, flavour, out)
    return {**res, "flavour": flavour, "calls": src.calls, "rate_limited_events": sum(e["event"] == "rate_limited" for e in events),
            "sleeps_requested_s": naps, "writes_received_by_source": src.writes_received}
