# tacitApp -- the typing assistant that learns from your mistakes

A simulated typing assistant that learns from your typing mistakes.

## Files

- `tacit_app.py` -- the frontend: the editor, the "Did you mean X?" box, the
  stage indicator (Observe/Suggest/Act) + confidence meter, the learning
  table and the buttons (Undo last fix / Load demo history / Reset).
- `tacit_demo.py` -- entry point: `python tacit_demo.py`.
- `tacit_demo.exe` -- the built executable (PyInstaller, one file): just
  double-click it.

## Notes

- Everything runs locally; nothing is sent anywhere. The editor is
  simulated (no real keyboard hook).
- For real llama suggestions: install Ollama from https://ollama.com/download
  and run `ollama pull llama3.2:3b` once; the app uses
  `http://localhost:11434` (see `OLLAMA_URL` in `tacit_engine.py`).
- `pip install requests` and `pip install pyspellchecker` are optional
  (recommended); without them the app uses the built-in dictionary.
- Learning data is stored in `taco_memory.json` (same folder).
