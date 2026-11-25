# Tacit — Autocorrect That Learns You

A desktop typing assistant that learns each user's own typing mistakes. Everything runs
on the user's device, so typed text is never sent anywhere.

Built for the I2CONECCT-2026 Project Exhibition and Competition
(Track: Innovation / Humanitarian Technology), A. J. Institute of Engineering and Technology.

## The problem

Standard autocorrect applies the same rules to every user. People with dyslexia, hand tremors
or other motor difficulties, and second-language typists repeat the same mistakes every day,
yet the tool never learns whether its fixes were accepted or undone. It also keeps "correcting"
names, slang and code that were typed on purpose. Tools that do personalise usually send your
text to a server.

## How it works

For every mistake → correction pair, Tacit keeps a confidence score built from the user's own
feedback, and picks one of three actions:

| Action | When |
|---|---|
| **Correct** | confidence ≥ 75% — fix it automatically (Ctrl+Z undoes it) |
| **Ask** | unsure — show "Did you mean …?" and learn from the answer |
| **Leave** | the word was kept twice — names, slang and code are never touched |

```
confidence = accepted ÷ (accepted + undone + kept + 1)
```

It earns the right to act, in three stages: **Observe** (changes nothing, just watches) →
**Suggest** (asks when unsure) → **Act** (auto-corrects trusted pairs). An undo lowers the
score, so one rejected fix sends Tacit back to asking.

## What's in this repository

| Branch | Contents |
|---|---|
| `main` | The Python prototype |
| `ui-redesign` | Reworked UI and engine for the desktop app |
| `phone-demo` | A single-file browser demo of Tacit as a phone keyboard |

**Desktop app** (`tacitApp/`): Tkinter UI, a correction engine that tries a local Llama 3.2 3B
model via Ollama → pyspellchecker → a built-in word table, and a learning layer saved to
`tacit_memory.json`. Optional packages and Ollama are not required; it falls back automatically.

```bash
pip install -r requirements.txt   # optional
python tacitApp/tacit_demo.py
```

**Phone demo** (`phone-demo/` on the `phone-demo` branch): open `index.html` in any browser.
Switch between a "Standard Keyboard" (fixed rules, never learns) and the Tacit keyboard to
compare them. Runs offline, no install.

## Status

A working prototype. The editor is simulated — a system-wide keyboard hook is the next step,
followed by a before-and-after study with volunteer testers, including students with dyslexia
or motor difficulties.

## Team

| Name | USN |
|---|---|
| Aadhil Krishna | 4JK24CI001 |
| Aishwarya H C | 4JK24CI008 |
| Daksh Sharma | 4JK25IS007 |
