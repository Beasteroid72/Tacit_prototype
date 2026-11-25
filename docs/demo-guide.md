# Demo guide

A short script for showing Tacit at a stall, plus setup notes for a fresh machine.

## Demo script

Five minutes, in this order. Each step answers the question the previous one raises.

**1. It does nothing at first.** Type `teh ` — no correction. That's the **Observe**
stage: Tacit has no evidence about you yet, so it stays out of the way. Say this out
loud; a judge who sees nothing happen will otherwise assume it's broken.

**2. Give it a history.** Click **Load demo history**, then type `teh ` again. Now it
corrects on its own, and offers an undo. Point at the confidence meter: this pair is
above 75%.

**3. Undo it.** Click **Undo last fix**. Confidence drops to 67% and the pair falls back
to asking. This is the part normal autocorrect never does — being wrong once costs it
the right to act.

**4. Teach it something no dictionary knows.** Type `i like mngo here`, click back into
`mngo`, add the missing `a`, then click away. Watch the **Fixed by you** column pick it
up. No spell checker proposes `mngo → mango`; Tacit learned it by watching you fix it.

**5. Show the alternative.** Hit **Keyboard** to switch to Standard. Type `daksh ` — it
becomes `dash`. Undo it, type it again, and it becomes `dash` again. The two "undos
needed" tiles keep score. This is the whole pitch in one gesture: the same rules for
everyone, forever, versus something that notices.

**If asked "doesn't autocorrect already do this?"** — the Leave column. A word you keep
twice is never touched again. Autocorrect has no memory of your having rejected it.

## Setup on a fresh machine

1. **Python 3.10+** — [python.org/downloads](https://www.python.org/downloads/). On
   Windows, tick *Add Python to PATH* in the installer. Check with `python --version`.
2. **Dependencies** — `pip install -r requirements.txt`. Both are optional; without them
   the app falls back to its built-in typo table and says so in the engine label.
3. **Run it** — `python desktop/run.py`.
4. **Optional, for real LLM suggestions** — install
   [Ollama](https://ollama.com/download), then `ollama pull llama3.2:3b`. The app looks
   for it at `http://localhost:11434` (`OLLAMA_URL` in `desktop/engine.py`) and starts
   the server itself if it isn't running, so there is nothing to launch by hand.

On Windows you can skip all of this and double-click `dist/tacit_demo.exe`. To rebuild
that executable after changing the code: `powershell -File tools\build.ps1`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `python: can't open file 'desktop/run.py'` | run it from the repository root, not from inside `desktop/` |
| `ModuleNotFoundError: requests` / `spellchecker` | `pip install -r requirements.txt` — not fatal, the built-in table still works |
| Typing does nothing | you're still in **Observe**. Click *Load demo history*, or type a known typo like `teh` |
| Suggestions are slow the first time | Ollama is loading the model. The UI stays responsive; the engine label shows which source answered |
| It keeps "fixing" a name | that's the point of **Leave** — keep the word twice and it stops |

## The numbers, for questions

- `confidence = accepted ÷ (accepted + undone + kept + 1)`
- **Correct** at 75% and above, **Ask** from 40%, **Leave** once a word is kept twice
- **Observe** for the first 5 events, then **Suggest**, then **Act**
- From nothing, a pair reaches 75% after three accepts — so four encounters before Tacit
  acts by itself. Worth admitting before someone works it out.
