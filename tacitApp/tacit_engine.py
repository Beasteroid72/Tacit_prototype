"""Candidate generation engine: live Ollama correction, pyspellchecker, built-in dictionary."""

import re

try:
    import requests
except ImportError:
    requests = None

try:
    from spellchecker import SpellChecker

    spell = SpellChecker()
except Exception:
    spell = None

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:3b"
OLLAMA_TIMEOUT_SEC = 3.0

BUILTIN_CORRECTIONS = {
    "teh": "the",
    "becuase": "because",
    "freind": "friend",
    "definately": "definitely",
    "recieve": "receive",
    "wich": "which",
    "seperate": "separate",
    "adress": "address",
    # names / code-like words (used by the demo): decline twice -> Leave
    "daksh": "dash",
    "argv_v2": "argv",
}

_cache = {}


def try_ollama(word, context):
    if requests is None:
        return None
    try:
        r = requests.post(
            OLLAMA_URL + "/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "prompt": f"The user typed the word '{word}' in this sentence:\n{context}\nIf the word is spelled correctly, reply with exactly the same word. Otherwise reply with only the correct spelling.",
            },
            timeout=OLLAMA_TIMEOUT_SEC,
        )
        if r.ok:
            resp = r.json().get("response", "").strip()
            if resp and len(resp) <= 60:
                return resp
    except Exception:
        pass
    return None


def _parse_correction(resp, word):
    # Extract the proposed correction from an LLM reply: prefer the first
    # double-quoted token (models often add text around the answer), else the
    # stripped reply itself. Returns None when it equals the typed word or is
    # not a plausible single word.
    m = re.findall(r'"([^"]+)"', resp)
    cand = m[0] if m else resp.strip()
    if not cand or cand.lower() == word.lower():
        return None
    if re.fullmatch(r"[A-Za-z][A-Za-z_\-]*[A-Za-z]?", cand):
        return cand
    return None


def engine_check(word, context):
    """Return (correction_or_None, engine_name_or_None)."""
    if word in _cache:
        return _cache[word]

    result = None
    llama_ok = False

    # 1) Ollama (local LLM), primary
    if requests is not None:
        corr = try_ollama(word, context)
        if corr:
            llama_ok = True
            cand = _parse_correction(corr, word)
            if cand:
                result = (cand, "Ollama")

    # 2) pyspellchecker
    if result is None and spell is not None:
        try:
            in_dict = spell.word(word) if hasattr(spell, "word") else not spell.known([word])
        except Exception:
            in_dict = True
        if not in_dict:
            sugg = spell.correction(word)
            if sugg and sugg != word:
                result = (sugg, "pyspellchecker")

    # 3) built-in table of common mistakes
    if result is None:
        corr = BUILTIN_CORRECTIONS.get(word.lower())
        if corr and corr != word.lower():
            result = (corr, "built-in dictionary")

    if result is None:
        result = (None, "Ollama" if llama_ok else None)

    _cache[word] = result
    return result


class TacitEngine:
    """Wrapper exposing engine_check() with the app's engine API."""

    def check(self, word, context):
        return engine_check(word, context)
