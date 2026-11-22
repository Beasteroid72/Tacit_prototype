# Tacit demo -- files, install, and usage

## Files (what each file does)
- tacit_app.py -- the Tkinter app: your editor, the learning table, behaviors (auto-correct, ask prompts, undo, reset, load demo history).
- tacit_engine.py -- correction engine: tries Ollama (llama3.2:3b) -> pyspellchecker -> built-in table of common mistakes (teh, recieve, freind, ...). Results cached per word.
- tacit_memory.py -- learning layer: TacitMemory tracks accepted/undone/kept per (mistake, correction), saved to the tacit_memory.json file.
- tacit_demo.py -- entry point: run it with: python tacit_demo.py
- tacit_demo.zip -- this zip (contains the app files above).

## 1. Install Python (Windows)
1. Download Python from https://www.python.org/downloads/ (Python 3.10+).
2. Run the installer; check the option Add Python to PATH.
3. In PowerShell: python --version (should print Python 3.10+).

## 2. Optional packages (PowerShell)
   pip install -r requirements.txt
(installs requests + pyspellchecker; the app also works without them -- see the Engine label.)

## 3. Optional: Ollama (real LLM suggestions)
1. Download and install Ollama from https://ollama.com/download.
2. In PowerShell: ollama pull llama3.2:3b
3. The app finds Ollama at http://localhost:11434 (OLLAMA_URL) using model llama3.2:3b (OLLAMA_MODEL).

## 4. Run the app
   python tacit_demo.py
Window: left = your editor (type a word + Space); top bar = stage (Observe/Suggest/Act, colored) + confidence of the last word; right = live table of learned pairs (Mistake / Correction / Accepted / Undone / Confidence % / Action); bottom = buttons:
- Undo last fix (or Ctrl+Z): reverts the last auto-correction; lowers confidence.
- Load demo history (accelerated): seeds demo memory: teh->the (Correct, 75%), recieve->receive (Ask, 50%), Daksh + argv_v2 (Leave).
- Reset: clears memory, starts again from stage Observe.
Footer of the window: simulated editor -- Tacit watches the text box; it does not hook your real keyboard.

## 5. Windows: installable / portable version
- build.ps1 -- builds a onefile windowed app: run .uild.ps1 (creates a dist folder with a single exe).
- requirements.txt -- the two optional dependencies.

## 6. Correction logic (re-checked)
- Engine order: Ollama -> pyspellchecker -> built-in table. Results cached per word. Ollama calls run in background threads, so the UI never freezes while waiting. Memory is saved on every change.
- Confidence = accepted / (accepted + undone + kept + 1) * 100. Action: Leave if kept >= 2; else Correct at 75 percent or above; else Ask.
- Verified on this machine: engine_check('Teh') -> ('the', 'built-in dictionary'); engine_check('recieve') -> ('receive', 'built-in dictionary'); engine_check('quick') -> (None, None).

## 7. Troubleshooting
1. Running python tacit_demo.py says cannot open the file -- run it from the project folder.
2. ModuleNotFoundError: No module named requests or pyspellchecker -- pip install -r requirements.txt; not fatal: the app falls back to the built-in dictionary.
3. Nothing happens when typing -- check the Engine label on the window; type a known mistake like teh, or click Load demo history (accelerated).
