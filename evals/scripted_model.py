"""A scripted fake model for the disposition classifier. No network, no API key. This is NOT Claude: it exists to
exercise the validator and fallbacks. Modes rotate: valid, quote_not_in_note, code_not_allowed, garbage, timeout."""
from __future__ import annotations

import itertools
import json

from sofl.disposition import classify_rules
from sofl.llm import LLMError

MODES = ["valid", "quote_not_in_note", "code_not_allowed", "garbage", "timeout"]


class FakeModel:
    name = "scripted"

    def __init__(self, modes=MODES):
        self.modes = itertools.cycle(modes)
        self.calls = []
        self.counts = {m: 0 for m in modes}

    def complete(self, system: str, user: str, max_tokens: int = 600) -> str:
        note = user.split("<note>", 1)[1].rsplit("</note>", 1)[0]
        self.calls.append(note)
        mode = next(self.modes)
        self.counts[mode] += 1
        code = classify_rules(note)
        if mode == "valid":
            return json.dumps({"code": code, "quote": note})
        if mode == "quote_not_in_note":
            return json.dumps({"code": "meeting_booked", "quote": "they agreed to a meeting on Friday"})
        if mode == "code_not_allowed":
            return json.dumps({"code": "hot_lead", "quote": note})
        if mode == "garbage":
            return "Sure! I think this account is hot."
        raise LLMError("timeout", True)
