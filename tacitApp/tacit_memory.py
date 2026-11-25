"""Tacit memory: a learning layer over correction records.

Tracks accepted / undone / kept outcomes per (mistake, correction) pair and
derives a confidence that guides whether to Ask, Correct or Leave a pair,
plus a stage (Observe / Suggest / Act) for a run of observed events.
"""

import copy
import json

CONF_ASK_MIN = 40.0
CONF_CORRECT = 75.0
LEAVE_KEPT_MIN = 2
OBSERVE_UNTIL_EVENTS = 5
MEMORY_FILE = "tacit_memory.json"


class TacitMemory:
    def __init__(self, path=MEMORY_FILE):
        self.path = path
        self.data = {}
        self.events = 0
        self.load()

    def load(self):
        try:
            with open(self.path, "r") as f:
                d = json.load(f)
            if isinstance(d, dict):
                self.events = int(d.pop("_events", 0))
                self.data = d
        except (OSError, ValueError, json.JSONDecodeError):
            self.data = {}
            self.events = 0

    def save(self):
        try:
            with open(self.path, "w") as f:
                json.dump({"_events": self.events, **self.data}, f, indent=2)
        except OSError:
            pass

    def pair(self, mistake, corr):
        stats = self.data.setdefault(mistake, {})
        return stats.setdefault(corr, {"accepted": 0, "undone": 0, "kept": 0})

    def record_accept(self, mistake, corr):
        self.pair(mistake, corr)["accepted"] += 1
        self.save()

    def record_undo(self, mistake, corr):
        self.pair(mistake, corr)["undone"] += 1
        self.save()

    def record_kept(self, mistake, corr):
        self.pair(mistake, corr)["kept"] += 1
        self.save()

    def record_self_fix(self, mistake, corr):
        """The user corrected this word by hand; counts as an accept.

        `self_fixed` is kept separately so the table can show how many of the
        accepts came from the user's own edits rather than from a prompt.
        """
        s = self.pair(mistake, corr)
        s["accepted"] += 1
        s["self_fixed"] = s.get("self_fixed", 0) + 1
        self.save()

    def has_pair(self, mistake, corr):
        """True when this pair is already known (without creating it)."""
        return corr in self.data.get(mistake, {})

    def personal_fix(self, word):
        """The correction the user taught by fixing this word themselves.

        Lets Tacit propose fixes no dictionary knows.  Pairs the user has kept
        on purpose are skipped; the most confident of the rest wins.
        """
        corrs = self.data.get(word.lower())
        if not corrs:
            return None
        best, best_conf = None, -1.0
        for corr, s in corrs.items():
            if not s.get("self_fixed") or s.get("kept", 0) >= LEAVE_KEPT_MIN:
                continue
            conf = self.stats_to_conf(s)
            if conf > best_conf:
                best, best_conf = corr, conf
        return best

    def forget_pair(self, mistake, corr):
        """Drop a pair once every count is back to zero."""
        corrs = self.data.get(mistake)
        if not corrs or corr not in corrs:
            return
        s = corrs[corr]
        if any(s.get(k, 0) for k in ("accepted", "undone", "kept", "self_fixed")):
            return
        del corrs[corr]
        if not corrs:
            del self.data[mistake]

    def stats_to_conf(self, s):
        return 100.0 * s["accepted"] / (s["accepted"] + s["undone"] + s["kept"] + 1)

    def confidence(self, mistake, corr):
        return self.stats_to_conf(self.pair(mistake, corr))

    def action(self, mistake, corr):
        s = self.pair(mistake, corr)
        if s["kept"] >= LEAVE_KEPT_MIN:
            return "Leave"
        if self.stats_to_conf(s) >= CONF_CORRECT:
            return "Correct"
        return "Ask"

    def stage(self):
        if self.events < OBSERVE_UNTIL_EVENTS:
            return "Observe"
        for corrs in self.data.values():
            for s in corrs.values():
                if self.stats_to_conf(s) >= CONF_CORRECT:
                    return "Act"
        return "Suggest"

    def seed(self, data):
        self.data = copy.deepcopy(data)
        self.events = OBSERVE_UNTIL_EVENTS
        self.save()

    def clear(self):
        self.data = {}
        self.events = 0
        self.save()
