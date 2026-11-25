# tacitApp -- the typing assistant that learns from your mistakes

A simulated typing assistant that learns from your typing mistakes.

## Files

- `tacit_app.py` -- the frontend: the editor, the "Did you mean X?" box, the
  stage indicator (Observe/Suggest/Act) + confidence meter, the learning
  table and the buttons (Undo last fix / Load demo history / Reset).
- `tacit_edits.py` -- decides whether a word you corrected by hand was a
  spelling fix (edit distance + guards against rewrites and capitalisation).
- `tacit_demo.py` -- entry point: `python tacit_demo.py`.
- `tacit_demo.exe` -- the built executable (PyInstaller, one file): just
  double-click it.

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
- Learning data is stored in `taco_memory.json` (same folder).
