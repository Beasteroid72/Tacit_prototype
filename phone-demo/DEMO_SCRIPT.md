# Tacit phone demo — how to run it at the stall

## Open it
Double-click `index.html` (Chrome or Edge). It works offline — no install, no internet.
Tip: press F11 for full screen.

## 2-minute script

1. **The idea (10 s)** — "Phones let you switch keyboards — Samsung Keyboard, Gboard. Tacit is a keyboard that learns *you*."
2. **Standard keyboard (30 s)** — tap 🌐 → **Standard Keyboard**. Type `Hi I am Daksh ` → it changes it to "Dash". Tap **↶ Undo**, type `Daksh ` again → it does it again. "Standard autocorrect never learns." (Undo counter goes up.)
3. **Switch to Tacit (5 s)** — tap 🌐 → **Tacit Keyboard**.
4. **Learning from scratch (optional, 30 s)** — click **Reset memory**. Type a few words: Tacit is in **Observe** (grey) and changes nothing. After 5 words it moves to **Suggest** (amber): type `teh ` → it *asks* "the?" in the strip. Tap **the**.
5. **Trained Tacit (45 s)** — click **Load demo history** (stage **Act**, green):
   - `teh ` → auto-corrected to "the" (75%+ confidence).
   - press **Ctrl+Z** → undone, confidence drops (watch the table). "One undo makes it more careful."
   - `recieve ` → it **asks** (50%, not sure yet).
   - `Daksh ` and `argv_v2 ` → **left alone**: you kept them twice before, so Tacit learned they're intentional.
6. **Learning from your own edits (30 s)** — type `hi hwo are you ` (no correction — Tacit doesn't know "hwo").
   Click on "hwo", fix it to "how", then click at the end of the message. The strip shows
   *"Learned from your edit: hwo → how"* and the table gets a ✎. Type `hwo ` again → Tacit now asks "how?".
   Fix it yourself 3 times in total (or accept) and it auto-corrects.
7. **Privacy (10 s)** — "Everything runs in this page on this laptop. Nothing you type is sent anywhere."

## Words that trigger corrections
teh, hte, adn, taht, waht, jsut, recieve, freind, becuase, definately, wich, seperate, adress,
thier, untill, tommorow, beleive, wierd, acheive, occured, goverment, realy, yuo — plus Daksh, argv_v2.

## Good to know
- Logic is ported from `Tacit_prototype/tacitApp/tacit_memory.py`: same formula
  (accepted ÷ (accepted + undone + kept + 1)), same thresholds (ask 40%, auto-correct 75%, leave after 2 keeps,
  observe for 5 words) and the same demo history.
- Two small demo-only differences from the Python prototype: a brand-new mistake is asked about on first sight
  (the prototype waits until 40%), and Ask-level words are still asked about in the Act stage.
- No local AI model here — corrections come from the built-in word list, so the demo is predictable.
- Memory is saved in the browser. Use **Reset memory** before each new visitor if you want to start fresh.
