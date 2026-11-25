"""Deciding whether a hand edit of a word was a spelling fix.

The user may go back into a word they already finished and correct it by hand
("mngo" -> "mango").  That is a strong signal of what they meant -- stronger
than any dictionary -- so Tacit learns from it.

This module holds the pure decision logic (no Tk, no memory), so it can be
tested on its own.  The checks keep rewrites, capitalisation changes and
reverted corrections out of memory.
"""

WORD_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'")

# A small fallback list, used only when pyspellchecker is not installed.
COMMON_WORDS = set((
    "a about after again all also and any are as at be because been before being both but by "
    "call can come could day did do does done down each even every few find first for from get "
    "give go going good got great had has have he her here him his how i if in into is it its "
    "just know last let like little long look made make many may me more most much must my need "
    "never new next no not now of off oh ok okay old on once one only or other our out over "
    "people please really right said same say see she should show so some soon still such sure "
    "take tell than thank thanks that the their them then there these they thing think this "
    "those though time to today tomorrow tonight too try two up us use very want was way we "
    "well were what when where which while who why will with without work would yeah yes yet "
    "you your hi hey hello bye expo demo college class project team friend friends home late "
    "early fine nice cool sorry happy morning evening night meet meeting reach text"
).split())


def max_edits(length):
    """How many letter changes still look like a typo fix, by word length."""
    if length <= 3:
        return 1
    if length <= 7:
        return 2
    return 3


def edit_distance(a, b):
    """Damerau-Levenshtein distance: adjacent swaps ("hwo"/"how") cost one."""
    la, lb = len(a), len(b)
    if not la:
        return lb
    if not lb:
        return la
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[la][lb]


def word_at(text, offset):
    """(start, end, word) of the word containing `offset`, or None.

    Apostrophes count inside a word (don't) but not at its edges.
    """
    if offset < 0 or offset > len(text):
        return None
    start = end = offset
    while start > 0 and text[start - 1] in WORD_CHARS:
        start -= 1
    while end < len(text) and text[end] in WORD_CHARS:
        end += 1
    while start < end and text[start] == "'":
        start += 1
    while end > start and text[end - 1] == "'":
        end -= 1
    if start >= end:
        return None
    return start, end, text[start:end]


def classify_edit(original, final, is_known, has_pair, require_known=False):
    """How a hand edit should be recorded: "fix", "undo" or None (ignore).

    original     the spelling before the user went back into the word
    final        the spelling they left behind
    is_known(w)  True when w is a word Tacit recognises
    has_pair(m, c)  True when the pair m -> c is already in memory
    require_known   only learn into a recognised word.  Used while the user
                    is still typing, so half-finished words are never learned.
    """
    a = (original or "").lower()
    b = (final or "").lower()
    if not a or not b or a == b:
        return None                      # unchanged, or capitalisation only
    if len(b) < 2 or not any(c.isalpha() for c in b):
        return None                      # too short, or not a word
    if has_pair(b, a):
        return "undo"                    # changed Tacit's own correction back
    if is_known(a):
        return None                      # a real word became another: a rewrite
    if edit_distance(a, b) > max_edits(max(len(a), len(b))):
        return None                      # too different to be a spelling fix
    if require_known and not is_known(b):
        return None
    return "fix"
