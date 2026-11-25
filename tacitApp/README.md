# tacitApp -- the typing assistant that learns from your mistakes

A simulated typing assistant that learns from your typing mistakes.

## Running it

```bash
pip install -r ../requirements.txt
python tacit_qt_demo.py      # PyQt interface (current)
python tacit_demo.py         # the older Tkinter window
```

## Files

- `tacit_qt_app.py` -- the PyQt interface: dark minimal layout, editor with
  inline highlights, suggestion strip, stat tiles, learning table, activity
  log, and a Standard / Tacit keyboard switch for comparing the two.
- `tacit_theme.py` -- all the colours, type and the Qt stylesheet.
- `tacit_qt_demo.py` -- entry point: `python tacit_qt_demo.py`.
- `tacit_app.py` -- the older Tkinter frontend, kept so the original demo
  still runs: editor, "Did you mean X?" box, stage indicator
  (Observe/Suggest/Act) + confidence meter, learning table and buttons.
- `tacit_edits.py` -- decides whether a word you corrected by hand was a
  spelling fix (edit distance + guards against rewrites and capitalisation).
- `tacit_demo.py` -- entry point: `python tacit_demo.py`.
- `tacit_demo.exe` -- the built executable (PyInstaller, one file): just
  double-click it.

## Standard vs Tacit

The **Keyboard** button switches between the two, the way a phone switches
keyboards. Standard applies the same built-in rules to everyone and never
learns -- undo its fix and it makes the same one again. The two "undos
needed" tiles count how often you had to correct each of them.

## Learning from your own edits

Go back into a word you already finished, correct the spelling yourself, then
click away (or type a space): Tacit records that as an accepted fix, so it
learns typos no dictionary proposes -- `mngo` -> `mango`. The "Fixed by you"
column counts these. Rewrites (`cat` -> `dog`), capitalisation changes and
words changed back from Tacit's own correction are not learned; the last of
those counts as an undo and lowers confidence.

## Notes

- Everything runs locally; nothing is sent anywhere. The editor is
  simulated (no real keyboard hook).
- For real llama suggestions: install Ollama from https://ollama.com/download
  and run `ollama pull llama3.2:3b` once; the app uses
  `http://localhost:11434` (see `OLLAMA_URL` in `tacit_engine.py`).
- `pip install requests` and `pip install pyspellchecker` are optional
  (recommended); without them the app uses the built-in dictionary.
- Learning data is stored in `tacit_memory.json` (same folder).
