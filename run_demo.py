#!/usr/bin/env python3
"""End-to-end demo on synthetic data, no API key: the shipped fixtures (gate fails, approval refused), then synthetic world
seed 2 (gate passes) with a refused agent approval, a named-human approval and a local rules release.   python run_demo.py"""
import io
import contextlib
import json
import sys
from pathlib import Path

import agent

ROOT = Path(__file__).resolve().parent
NOW = "2026-11-26T18:00:00Z"
log = []


def step(title, argv):
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        rc = agent.main(argv)
    out = (buf.getvalue() + err.getvalue()).rstrip()
    log.append(f"$ python agent.py {' '.join(argv)}\n{out}\n(exit {rc})\n")
    print(log[-1])
    return out


step("shipped fixtures", ["run", "--now", NOW])
m = json.loads((ROOT / "outputs/run/manifest.json").read_text())
step("approval on a failed gate", ["approve", "--approver", "rubia.naseem", "--sha256", m["change_sha256"], "--now", NOW])
step("fresh world", ["run", "--world-seed", "2", "--out", "outputs/run_seed2", "--now", NOW])
m2 = json.loads((ROOT / "outputs/run_seed2/manifest.json").read_text())
step("agent tries to approve", ["approve", "--out", "outputs/run_seed2", "--approver", "claude", "--sha256", m2["change_sha256"], "--now", NOW])
step("release before approval", ["release", "--out", "outputs/run_seed2", "--now", NOW])
step("named human approves", ["approve", "--out", "outputs/run_seed2", "--approver", "demo.reviewer", "--sha256", m2["change_sha256"], "--now", NOW])
step("release", ["release", "--out", "outputs/run_seed2", "--now", NOW])
step("audit", ["verify-audit", "--out", "outputs/run_seed2"])
(ROOT / "outputs/demo_transcript.txt").write_text("\n".join(log))
