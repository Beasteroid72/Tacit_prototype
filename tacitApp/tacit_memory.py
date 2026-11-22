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
