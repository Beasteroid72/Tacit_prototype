# Tacit — Autocorrect That Learns You

Autocorrect applies the same rules to everybody. Tacit watches whether *you* accepted
or undid each fix, and only acts once it has earned the right to. Everything runs on
your own machine; nothing you type is sent anywhere.

Built for the I2CONECCT-2026 Project Exhibition, A. J. Institute of Engineering and
Technology — track: Innovation / Humanitarian Technology.

---

## The problem

People who type the same mistake every day — dyslexic writers, people with hand tremors,
second-language typists — get no benefit from autocorrect learning, because it doesn't
learn. It never notices that you undid the same "fix" fifty times, and it keeps rewriting
names, slang and code you typed on purpose. The tools that *do* personalise usually do it
by sending your text to a server.

## How it works

Tacit keeps a record for every `mistake → correction` pair, scored only from your own
reactions to it:

```
confidence = accepted ÷ (accepted + undone + kept + 1)
```

That score picks one of three actions:

| Action | When | What you see |
|---|---|---|
| **Correct** | confidence ≥ 75% | the word is fixed as you type; `Ctrl+Z` undoes it |
| **Ask** | 40–75% | "Did you mean …?" — your answer becomes evidence |
| **Leave** | you kept the word twice | never touched again — names, slang, code |

It also has to earn its way up through three stages: **Observe** (watches, changes
nothing) → **Suggest** (asks when unsure) → **Act** (fixes trusted pairs on its own).
An undo pushes a pair back down, so one wrong fix returns Tacit to asking.

**Learning from your own edits.** Go back into a word you already finished, fix the
spelling yourself, and click away — Tacit records that as an accepted correction. This is
how it picks up typos no dictionary would ever propose (`mngo → mango`). Rewrites
(`cat → dog`) and capitalisation changes are ignored, and changing back something Tacit
did counts as an undo.

**Where candidate corrections come from**, in order: a local Llama 3.2 3B model through
Ollama, then pyspellchecker, then a built-in table of common typos. Each step is optional —
with none of them installed the built-in table still works, and the window tells you which
source answered.

## Running it

```bash
pip install -r requirements.txt
python desktop/run.py
```

Windows users can instead double-click `dist/tacit_demo.exe` — no Python needed.

Optional, for real LLM suggestions: install [Ollama](https://ollama.com/download) and run
`ollama pull llama3.2:3b` once. The app starts the Ollama server itself if it isn't already
running, and carries on without it if it isn't installed.

The **Keyboard** button switches between Standard and Tacit, the way a phone switches
keyboards — the quickest way to see the difference. `docs/demo-guide.md` has a short
script to walk through.

## Layout

```
desktop/          the PC app
  run.py            ← start here (PyQt interface)
  app_qt.py         the PyQt window
  memory.py         confidence, stages, the Correct/Ask/Leave decision
  engine.py         proposes corrections: Ollama → pyspellchecker → built-in table
  edits.py          decides whether a word you fixed by hand was a spelling fix
  theme.py          colours and stylesheet
  run_tkinter.py    ← the original Tkinter version, kept for reference
  app_tkinter.py
docs/             demo script and setup notes
tools/            build and GitHub helper scripts (PowerShell)
dist/             the pre-built Windows .exe
```

The learning data lives in `tacit_memory.json` next to wherever you run the app from. It
isn't committed — it's different for every user.

## Branches

| Branch | Contents |
|---|---|
| `main` | the desktop prototype |
| `phone-demo` | a single-file browser demo of Tacit as a phone keyboard — open `index.html` |

## Status

A working prototype, with two honest gaps:

- The editor is **simulated**. Tacit watches its own text box; it does not hook your real
  keyboard yet. That hook is the next piece of work.
- A new pair needs **three accepts** before Tacit corrects it on its own, and that count is
  per exact misspelling. Sharing evidence between a word's different misspellings, and
  between typos of the same kind, is the main thing that would make it feel fast to learn.

After that: a before-and-after typing study with volunteer testers, including students with
dyslexia or motor difficulties.

## Team

| Name | USN |
|---|---|
| Aadhil Krishna | 4JK24CI001 |
| Aishwarya H C | 4JK24CI008 |
| Daksh Sharma | 4JK25IS007 |
