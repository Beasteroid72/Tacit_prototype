"""Engine: the local Ollama LLM is the detector for every word; pyspellchecker and the built-in dictionary are fallbacks when Ollama is unavailable or times out.  Learning/undo behaviour is in memory.py; this module only proposes corrections."""

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
OLLAMA_TIMEOUT_SEC = 2.0   # short timeout so typing never lags

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


def is_dictionary_word(word):
    """Best-effort check that a word is a real word, for judging hand edits.

    Uses pyspellchecker when it is installed, and otherwise the built-in
    corrections plus a small common-word list, so the check still works on a
    bare install.
    """
    w = word.lower()
    if w in BUILTIN_CORRECTIONS.values():
        return True
    if spell is not None:
        try:
            return bool(spell.known([w]))
        except Exception:
            pass
    from edits import COMMON_WORDS
    return w in COMMON_WORDS


def _should_check(word):
    """Skip very short words, numbers and capitalised names."""
    if len(word) < 3:
        return False
    if word.isdigit():
        return False
    if word[:1].isupper():
        return False
    return True


def try_ollama(word, context):
    """Ask the local LLM: is `word` misspelled in context?  Returns the raw
    reply text, or None when Ollama is unavailable or times out."""
    if requests is None:
        return None
    try:
        r = requests.post(
            OLLAMA_URL + "/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "stream": False,
                "prompt": (
                    f"The user typed the word '{word}' in this sentence:\n"
                    f"{context}\n"
                    f"Is the word '{word}' misspelled in this context? "
                    f"If yes, reply with only the single best correction. "
                    f"If no, reply with OK."
                ),
            },
            timeout=OLLAMA_TIMEOUT_SEC,
        )
        if r.ok:
            resp = r.json().get("response", "").strip()
            if resp:
                return resp
    except Exception:
        pass
    return None


def _parse_correction(resp, word):
    # Extract the proposed correction from an LLM reply: take the first
    # quoted token (models often add text around the answer), else the reply
    # itself. Returns None when it equals the typed word or is not a plausible
    # single word. An "OK" reply gives None (not a mistake).
    m = re.findall(r'"([^"]+)"', resp)
    cand = m[0] if m else resp.strip()
    cand = cand.strip().strip("'").strip()
    if not cand or cand.lower() == word.lower():
        return None
    if re.fullmatch(r"[A-Za-z][A-Za-z_\-]*[A-Za-z]?", cand):
        return cand
    return None


def engine_check(word, context):
    """Return (correction_or_None, engine_name_or_None) for a completed word.

    The LLM is the detector for every word.  If Ollama is unavailable or
    times out, pyspellchecker and the built-in dictionary act as fallbacks;
    `engine_name` says which one was used so the UI can show it.
    """
    key = (word, context)
    if key in _cache:
        return _cache[key]

    result = None
    engine_name = None

    if _should_check(word):
        # 1) Ollama (local LLM), primary -- asked for every word
        if requests is not None:
            resp = try_ollama(word, context)
            if resp is not None:
                engine_name = "Ollama"
                corr = _parse_correction(resp, word)
                if corr:
                    result = (corr, "Ollama")

        # 2) pyspellchecker -- fallback when Ollama is unavailable/times out
        if result is None and spell is not None:
            try:
                in_dict = spell.word(word) if hasattr(spell, "word") else not spell.known([word])
            except Exception:
                in_dict = True
            if not in_dict:
                sugg = spell.correction(word)
                if sugg and sugg != word:
                    result = (sugg, "pyspellchecker")

        # 3) built-in table of common mistakes -- fallback when Ollama is unavailable/times out
        if result is None:
            corr = BUILTIN_CORRECTIONS.get(word.lower())
            if corr and corr != word.lower():
                result = (corr, "built-in dictionary")

    if result is None:
        result = (None, engine_name)

    _cache[key] = result
    return result


class TacitEngine:
    """Wrapper exposing engine_check() with the app's engine API."""

    def check(self, word, context):
        return engine_check(word, context)
