"""
tacit_app.py -- the Tkinter UI for "Tacit: Autocorrect That Learns You".

This is the redesigned UI layer: a calm, clean, professional look with
suggestions shown as speech bubbles directly inside the editor text.

Everything about the logic stays exactly the same as before: which
corrections are proposed and when, the Observe / Suggest / Act stages, the
learning table, the memory file, the undo and demo features.  This file only
changes how it all looks and how suggestions appear in the text.

Layout (see SECTION 6):
  - header: app name "Tacit", a three-step stage indicator
    (Observe / Suggest / Act -- the current step highlighted), a slim
    confidence meter, and a small engine label;
  - two cards with soft borders: the editor on the left, the "What Tacit has
    learned" table on the right;
  - a bottom bar: note + grouped, consistent-size buttons;
  - the honest footer note (the editor is simulated; it does not hook the
    real keyboard).
"""

# ==================== SECTION 1: SETTINGS AND COLOURS (the look) ====================
# Every colour, font, size and timing below is a named constant so you can
# change the whole look in one place.
# Beginner note: a colour is a hex string like "#d4eadc" -- try
# https://htmlcolorcodes.com if you want a colour picker.

WINDOW_GEOMETRY = "1020x760"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")   # the app name in the header
FONT_SMALL = ("Segoe UI", 9)
FONT_TINY = ("Segoe UI", 8)
FONT_ENGINE = ("Segoe UI", 9)
FONT_EDITOR = ("Segoe UI", 11)          # comfortable size for the editor text

PAD = 12                                # outer padding
CARD_PAD = 10                           # padding inside each card
BORDER = "#e3e2df"                      # soft border of the two cards
BG = "#f5f4f1"                          # window background (soft off-white)
CARD = "#ffffff"                        # the two cards' background
TEXT = "#3a3a3a"
MUTED = "#7a7a7a"                       # muted / hint text

# ---- three-step stage indicator (Observe / Suggest / Act) ----
STAGE_COLORS = {"Observe": "#c9c9c9", "Suggest": "#e8a34e", "Act": "#5aa05e"}
STAGE_ORDER = ["Observe", "Suggest", "Act"]

# ---- confidence meter (slim) ----
CONF_TRACK = "#e6e6e6"
CONF_FILL = "#c6d8d2"
CONF_W = 150
CONF_H = 6

# ---- word markers + speech bubbles (pastel, depend on the action) ----
BUB_GREEN = "#d4eadc"    # soft green: Correct / brief highlight
BUB_AMBER = "#fde9cd"    # soft amber: Ask
BUB_BLUE = "#dce6ef"     # soft blue-grey: Leave
OBSERVE_MARK = "#f3f3f2" # very faint marker while in the Observe stage

BUBBLE_PAD_X = 8
BUBBLE_PAD_Y = 6
BUBBLE_TAIL_H = 7        # pointer-tail height in pixels
BUBBLE_FADE_MS = 4000    # CORRECT bubbles disappear after this time
                          # (Tk has no true fade -- see honesty note in REPORT)
HIGHLIGHT_MS = 400        # brief soft highlight after an automatic correction

# ---- button emphasis ----
BTN_EMPHASIS_FONT = FONT_BOLD

# ---- editor ----
EDITOR_TITLE = "Your editor -- type here (simulated)"
EDITOR_HINT = "Start typing..."

# ---- learned table ----
TABLE_TITLE = "What Tacit has learned (memory: tacit_memory.json)"
TABLE_COLS = ["Mistake", "Correction", "Accepted", "Undone", "Confidence %", "Action"]
TABLE_WIDTHS = {"Mistake": 112, "Correction": 120, "Accepted": 76,
                "Undone": 76, "Confidence %": 92, "Action": 76}
TABLE_STRIPE = "#f9f9f9"  # subtle row striping
EMPTY_STATE = "Nothing learned yet. Start typing."

# ---- footer / note ----
FOOTER_TEXT = ("Simulated editor -- Tacit watches the text box below; "
               "it does not hook your real keyboard.")

# ---- action labels ----
ACTION_CORRECT = "Correct"
ACTION_ASK = "Ask"
ACTION_LEAVE = "Leave"


# ==================== SECTION 2: MEMORY (JSON) ====================
# Note: this is only the UI layer.  The memory itself is in tacit_memory.py
# (class TacitMemory) -- this app reads/writes "tacit_memory.json" through it.
# What the UI uses: memory.data, memory.stage(), memory.action(),
# memory.confidence(), memory.pair(), memory.record_accept/undo/kept,
# memory.seed(), memory.clear(), memory.save().


# ==================== SECTION 3: LEARNING LAYER (decides Correct / Ask / Leave) ====================
# Note: this is only the UI layer.  The actual logic is in tacit_memory.py
# (class TacitMemory).  The rules it applies:
#   - action == "Leave"  if the word was "kept" at least twice (LEAVE_KEPT_MIN)
#   - action == "Correct" if confidence >= CONF_CORRECT (75%)
#   - otherwise action == "Ask" (an Ask is shown when confidence >= CONF_ASK_MIN)
#   - stage == "Act" once any pair reaches "Correct" confidence, otherwise
#     "Suggest"; "Observe" until OBSERVE_UNTIL_EVENTS events.
# The UI reacts to the stage and to the action; it does not re-implement them.


# ==================== SECTION 4: SUGGESTION ENGINE (proposes corrections) ====================
# Note: this is only the UI layer.  The engine is in tacit_engine.py
# (class TacitEngine, method check(word, context) -> (correction, engine)).
# The UI calls it in a background thread (same as before) and shows whatever
# comes back as a speech bubble; the engine fallback chain (Ollama ->
# pyspellchecker -> built-in dictionary) is unchanged.


# ==================== SECTION 5: STAGE LOGIC (when to mark / show) ====================
# Note: this is only the UI layer.  The decision "what to do with a word" is
# the same as before (see SECTION 3): the UI uses memory.stage() and
# memory.action() and reacts accordingly:
#   - Observe:  very faint marker + tiny bubble "Noted. Tacit is still learning"
#   - Suggest:  Ask bubble (only when action == Ask and confidence >= threshold)
#   - Act:      auto-correct with a brief highlight + "Corrected to X" bubble,
#               or a Leave marker + "Kept as you wrote it" bubble on hover


# ==================== SECTION 6: UI LAYOUT ====================
# Two main areas as soft-bordered cards with generous padding:
#   card 1 = the editor (you type here), card 2 = the learned table.
# Plus a header (app name + stage indicator + confidence meter + engine label)
# and a bottom bar (note + grouped buttons).  See build_ui() below.


# ==================== SECTION 7: EDITOR WORD-MARKING (tags on the Text widget) ====================
# Words flagged by Tacit are marked directly in the editor with Text widget
# tags: soft backgrounds (see the pastel colours in SECTION 1).  Marker tags:

TAG_ASK = "mark_ask"        # flagged word waiting for a decision (Ask)
TAG_CORRECT = "mark_correct"  # just auto-corrected (brief highlight)
TAG_LEAVE = "mark_leave"    # word left as written (Leave marker)
TAG_OBSERVE = "mark_observe"  # very faint marker while in the Observe stage
MARK_TAGS = (TAG_ASK, TAG_CORRECT, TAG_LEAVE, TAG_OBSERVE)

# Honesty note: Tk Text supports solid underlines, not dotted ones, so the
# Leave marker is drawn as a soft solid underline (closest clean alternative
# to "dotted underline").


# ==================== SECTION 8: SUGGESTION BUBBLE (speech bubble in the editor) ====================
# The bubble is a Canvas drawn over the editor and placed with place(),
# positioned using the Text widget's bbox() for the marked word.  It has a
# small pointer tail aimed at the word, and it is removed cleanly (place_forget)
# when dismissed.  It never covers the marked word: it is placed below it.


# ==================== SECTION 9: LEARNED TABLE ====================
# Cleaner table (ttk.Treeview) with the same columns as before plus the Action
# (Correct / Ask / Leave).  Rows get subtle striping, and the action is
# colour-coded (a light tint behind the row) so you can tell them apart.
# Friendly empty state ("Nothing learned yet. Start typing.") when nothing
# is learned yet.


# ==================== SECTION 10: BUTTONS AND DEMO FEATURES ====================
# Buttons grouped at the bottom, consistent size.  "Load demo history
# (accelerated)" is slightly emphasised; "Reset" is visually quiet.
# The footer note stays honest about the simulated editor.


# ==================== SECTION 11: START-UP ====================
# main() opens the window (TacitApp) and starts the event loop.
# The entry point (tacit_demo.py) is unchanged; it calls this module's main().


import re
import threading
import tkinter as tk
from tkinter import ttk

from tacit_memory import TacitMemory
from tacit_engine import TacitEngine


class TacitApp:
    """The Tkinter window: editor on the left, learning table on the right."""

    def __init__(self, root, memory=None, engine=None):
        self.root = root
        root.title("Tacit -- Autocorrect That Learns You")
        root.geometry(WINDOW_GEOMETRY)

        self.memory = TacitMemory() if memory is None else memory
        self.engine = TacitEngine() if engine is None else engine
        self.last_fix = None      # (mistake, correction) of the last automatic fix
        self.pending_words = []   # words queued while a check is in flight
        self.ollama_busy = False  # True while a check is in flight

        self.stage_labels = {}    # stage name -> label (SECTION 6/SECTION 5)
        self.bubble = None        # the speech-bubble canvas (SECTION 8)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build_ui()
        self.set_stage()
        self.set_confidence(0.0)

    # ---------------- UI (SECTION 6: UI layout) ----------------

    def build_ui(self):
        # Header: app name + three-step stage indicator + confidence meter + engine label
        header = tk.Frame(self.root, background=BG, padx=PAD, pady=PAD)
        header.pack(side="top", fill="x")

        tk.Label(header, text="Tacit", font=FONT_TITLE, background=BG).pack(side="left")

        self.stage_frame = tk.Frame(header, background=BG)
        self.stage_frame.pack(side="left", padx=(24, 0))
        for st in STAGE_ORDER:
            lbl = tk.Label(self.stage_frame, text=st, font=FONT_SMALL,
                           background=BG, fg=MUTED, padx=4)
            lbl.pack(side="left", padx=2)
            self.stage_labels[st] = lbl

        self.conf_canvas = tk.Canvas(header, width=CONF_W, height=CONF_H,
                                     background=CONF_TRACK, highlightthickness=0)
        self.conf_canvas.pack(side="left", padx=(16, 0))
        self.conf_label = tk.Label(header, text="0%", font=FONT_SMALL, background=BG)
        self.conf_label.pack(side="left", padx=(4, 0))

        self.engine_label = tk.Label(header, text="Engine: none yet",
                                     background=BG, font=FONT_ENGINE, fg=MUTED)
        self.engine_label.pack(side="left", padx=(16, 0))

        # Main: two cards (editor + learned table), soft-bordered
        main = tk.Frame(self.root, background=BG, padx=PAD, pady=0)
        main.pack(side="top", fill="both", expand=True)

        card1 = tk.Frame(main, background=CARD, padx=CARD_PAD, pady=CARD_PAD,
                         highlightbackground=BORDER, highlightthickness=1)
        card1.pack(side="left", fill="both", expand=True, padx=(0, 12))
        self.card1 = card1

        card2 = tk.Frame(main, background=CARD, padx=CARD_PAD, pady=CARD_PAD,
                         highlightbackground=BORDER, highlightthickness=1)
        card2.pack(side="left", fill="both", expand=True)

        # ---------- Card 1: editor ----------
        tk.Label(card1, text=EDITOR_TITLE, font=FONT_TITLE, background=CARD).pack(
            anchor="w", pady=2)

        self.editor = tk.Text(card1, font=FONT_EDITOR, wrap="word", undo=True,
                              background=CARD, padx=6, pady=6, highlightthickness=0)
        self.editor.pack(fill="both", expand=True)
        self.editor.focus()
        self.editor.bind("<KeyRelease>", self.on_key_release)
        self.editor.bind("<Control-z>", lambda e: self.undo_last_fix())

        # Placeholder hint when the editor is empty
        self.placeholder = tk.Label(card1, text=EDITOR_HINT, background=CARD,
                                    fg=MUTED, font=FONT_SMALL)
        self.placeholder.pack(anchor="w", padx=6)
        self._update_placeholder()

        # Speech-bubble popup over the editor (placed with place() on demand)
        self.bubble = tk.Canvas(card1, highlightthickness=0, background=CARD)

        # Word-marking tags (SECTION 7: editor word-marking)
        self.editor.tag_configure(TAG_ASK, background=BUB_AMBER)
        self.editor.tag_configure(TAG_CORRECT, background=BUB_GREEN)
        self.editor.tag_configure(TAG_LEAVE, underline=True,
                                  background=BUB_BLUE)
        self.editor.tag_configure(TAG_OBSERVE, background=OBSERVE_MARK)

        # Hover/click bubbles for Leave-marked words
        try:
            self.editor.tag_bind(TAG_LEAVE, "<Enter>",
                                 lambda e: self._show_leave_bubble(e))
            self.editor.tag_bind(TAG_LEAVE, "<Button-1>",
                                 lambda e: self._show_leave_bubble(e))
        except Exception:
            pass

        # Clicking elsewhere dismisses the bubble
        self.root.bind("<Button-1>", self._on_root_click)

        editor_note = tk.Label(
            card1,
            text="Tacit checks a word as you finish it (Space or punctuation). "
                 "Ctrl+Z undoes the last fix.",
            font=FONT_SMALL, background=CARD, fg=MUTED)
        editor_note.pack(anchor="w", padx=6, pady=0)

        # ---------- Card 2: learned table ----------
        tk.Label(card2, text=TABLE_TITLE, font=FONT_TITLE, background=CARD).pack(
            anchor="w", pady=2)

        self.learned_tree = ttk.Treeview(card2, columns=TABLE_COLS,
                                         show="headings", height=10)
        for c in TABLE_COLS:
            self.learned_tree.heading(c, text=c)
            self.learned_tree.column(c, width=TABLE_WIDTHS[c],
                                     anchor="center", stretch=False)
        # Subtle row striping
        self.learned_tree.tag_configure("stripe", background=TABLE_STRIPE)
        # Action-colour-coded tints (Correct/Ask/Leave)
        self.learned_tree.tag_configure("action_correct", background="#e8f4ea")
        self.learned_tree.tag_configure("action_ask", background="#fdf3d9")
        self.learned_tree.tag_configure("action_leave", background="#eceff4")
        self.learned_tree.pack(fill="both", expand=True, padx=4)

        # Friendly empty state
        self.empty_state = tk.Label(card2, text=EMPTY_STATE, background=CARD,
                                    fg=MUTED, font=FONT_SMALL)
        self._update_empty_state()

        # ---------- Bottom bar: note + grouped, consistent-size buttons ----------
        bottom = tk.Frame(self.root, background=CARD, padx=PAD, pady=4)
        bottom.pack(side="bottom", fill="x")

        self.note_label = tk.Label(bottom, text="", background=CARD, font=FONT_SMALL,
                                   fg=MUTED)
        self.note_label.pack(side="left", fill="x", expand=True)

        btn_row = tk.Frame(bottom, background=CARD)
        btn_row.pack(side="right")
        for text, cmd, emphasis in [
            ("Undo last fix", self.undo_last_fix, False),
            ("Load demo history (accelerated)", self.load_demo_history, True),
            ("Reset", self.reset, False),
        ]:
            font = BTN_EMPHASIS_FONT if emphasis else FONT
            tk.Button(btn_row, text=text, font=font, command=cmd,
                      padx=10, pady=3).pack(side="left", padx=3)

        footer = tk.Label(self.root, text=FOOTER_TEXT, background=CARD,
                          font=FONT_SMALL, fg=MUTED)
        footer.pack(side="bottom", fill="x", padx=PAD, pady=0)

    # ---------------- helpers ----------------

    def note_set(self, msg):
        self.note_label.config(text=msg)

    def after(self, ms, func):
        self.root.after(int(ms), func)

    def after_idle(self, func):
        self.root.after_idle(func)

    def set_stage(self):
        # Stage indicator (SECTION 5/SECTION 6): current step highlighted
        stage = self.memory.stage()
        for st, lbl in self.stage_labels.items():
            if st == stage:
                lbl.config(fg=STAGE_COLORS[st], font=FONT_BOLD)
            else:
                lbl.config(fg=MUTED, font=FONT)
        return stage

    def set_confidence(self, conf):
        # Slim confidence meter (SECTION 6)
        try:
            conf = max(0.0, min(100.0, float(conf)))
            w = int(round(conf / 100.0 * CONF_W))
            c = self.conf_canvas
            c.delete("conf")
            c.create_rectangle(0, 0, CONF_W, CONF_H, fill=CONF_TRACK,
                               outline="", tags="conf")
            if w > 0:
                c.create_rectangle(0, 0, w, CONF_H, fill=CONF_FILL,
                                   outline="", tags="conf")
        except tk.TclError:
            pass
        self.conf_label.config(text="{:.0f}%".format(conf))

    def update_engine_label(self, engine, corr):
        text = "Engine: " + str(engine) if engine else "Engine: none needed"
        if engine and engine not in ("Ollama", "pyspellchecker", "built-in dictionary"):
            text = "fallback: " + engine
        self.engine_label.config(text=text)

    def _update_empty_state(self):
        # Friendly empty state in the learned table (SECTION 9)
        if self.learned_tree.get_children():
            self.empty_state.place_forget()
        else:
            self.empty_state.place(relx=0.02, rely=0.5, anchor="w", in_=self.learned_tree)

    def _update_placeholder(self):
        # Placeholder hint when the editor is empty (SECTION 6)
        try:
            if self.editor_text().strip():
                self.placeholder.place_forget()
            else:
                self.placeholder.place(relx=0.015, rely=0.03, anchor="nw",
                                       in_=self.card1)
        except Exception:
            pass

    def refresh_table(self):
        # Learned table with subtle striping and colour-coded actions (SECTION 9)
        tree = self.learned_tree
        tree.delete(*tree.get_children())
        for i, mistake in enumerate(sorted(self.memory.data)):
            for corr in sorted(self.memory.data[mistake]):
                s = self.memory.data[mistake][corr]
                conf = self.memory.stats_to_conf(s)
                action = self.memory.action(mistake, corr)
                action_tag = {"Correct": "action_correct", "Ask": "action_ask",
                              "Leave": "action_leave"}.get(action, "")
                tags = [action_tag] + (["stripe"] if i % 2 else [])
                rid = tree.insert("", "end", values=(
                    mistake, corr, s["accepted"], s["undone"],
                    "{:.0f}%".format(conf), action), tags=tuple(tags))
        self._update_empty_state()

    # ---------------- editor text helpers ----------------

    def editor_text(self):
        txt = self.editor.get("1.0", "end")
        if txt.endswith("\n"):
            txt = txt[:-1]
        return txt

    def offset_to_index(self, offset):
        """Map a 0-based offset in editor_text() to a Tk index string."""
        txt = self.editor_text()
        pos = 0
        for line_no, line in enumerate(txt.split("\n"), start=1):
            if offset <= pos + len(line):
                return "{}.{}".format(line_no, offset - pos)
            pos += len(line) + 1
        return "end"

    def word_range_last(self, word):
        """(start_index, end_index) of the last occurrence of `word`, or None."""
        txt = self.editor_text()
        idx = txt.rfind(word)
        if idx < 0:
            return None
        return self.offset_to_index(idx), self.offset_to_index(idx + len(word))

    def flash(self, start, end, color):
        # Brief soft highlight (used for the auto-correct glow)
        try:
            self.editor.tag_add("tacit_flash", start, end)
            self.editor.tag_config("tacit_flash", background=color)
            self.after(HIGHLIGHT_MS,
                       lambda: self.editor.tag_remove("tacit_flash", start, end))
        except tk.TclError:
            pass

    # ---------------- keyboard ----------------

    def on_key_release(self, event):
        # Typing dismisses the bubble (SECTION 8: "Typing ... dismisses it")
        self._hide_bubble()
        self._update_placeholder()
        # Tacit checks a word as the user finishes it (Space or punctuation)
        ch = event.char
        if ch and ch in " .,!?:":
            self.handle_completed_word()

    def _on_root_click(self, event):
        # Clicking elsewhere dismisses the bubble, unless the click is on the
        # bubble itself (its buttons handle themselves).
        if self._is_inside_bubble(event.widget):
            return
        self._hide_bubble()

    def _is_inside_bubble(self, widget):
        w = widget
        while w is not None:
            if w is self.bubble:
                return True
            try:
                w = w.winfo_parent()
            except Exception:
                return False
        return False

    # ---------------- core behaviour ----------------

    def handle_completed_word(self):
        try:
            idx = self.editor.index("insert")
        except tk.TclError:
            return
        text = self.editor.get("1.0", idx)
        if not text or text[-1] not in " \t.,!?;:":
            return
        m = list(re.finditer(r"[A-Za-z_0-9]+", text))
        if not m:
            return
        word = m[-1].group(0)
        rng = (self.offset_to_index(m[-1].start()),
               self.offset_to_index(m[-1].end()))
        self._hide_bubble()
        if self.memory is not None:
            self.memory.events += 1

        if self.ollama_busy:
            # A check is already in flight; queue this word so it is handled
            # one by one as the earlier ones finish.
            self.pending_words.append((word, text[-80:], rng))
            self.note_set('Queued "{}" -- waiting for the current check.'
                          .format(word))
        else:
            self.ollama_busy = True
            self.note_set('Tacit is checking "{}" (queue: {}) ...'
                          .format(word, len(self.pending_words)))
            self._start_worker(word, text[-80:], rng)

    def _start_worker(self, word, context, rng):
        threading.Thread(target=self._engine_worker, args=(word, context, rng),
                         daemon=True).start()

    def _engine_worker(self, word, context, rng):
        try:
            out = self.engine.check(word, context)
            if isinstance(out, tuple) and len(out) >= 1:
                corr = out[0]
                engine = out[1] if len(out) > 1 else None
            else:
                corr, engine = out, None
        except Exception:
            corr, engine = None, None
        try:
            self.after_idle(lambda: self._done(word, corr, engine, rng))
        except tk.TclError:
            pass

    def _done(self, word, corr, engine, rng):
        # Runs on the main thread (via after_idle)
        try:
            self._apply_word(word, corr, engine, rng)
            if self.pending_words:
                w, ctx, r = self.pending_words.pop(0)
                self.note_set('Tacit is checking "{}" (queue: {}) ...'
                              .format(w, len(self.pending_words)))
                self._start_worker(w, ctx, r)
            else:
                self.ollama_busy = False
                self.note_set('')
        except Exception:
            pass

    def _apply_word(self, word, corr, engine, rng):
        self.update_engine_label(engine, corr)
        stage = self.memory.stage()

        if corr and stage == "Act":
            action = self.memory.action(word, corr)
            if action == "Correct":
                self.auto_correct(word, corr, rng)
            elif action == "Leave":
                # Subtle dotted/soft underline + hover/click bubble (SECTION 7/8)
                self._mark_word(*rng, tag=TAG_LEAVE)
                self._show_leave_bubble(None)
        elif corr and stage == "Suggest":
            conf = self.memory.confidence(word, corr)
            action = self.memory.action(word, corr)
            if action == "Ask" and conf >= CONF_ASK_MIN:
                # Ask bubble in the editor itself (SECTION 8)
                self._show_ask_bubble(word, corr, conf)
        elif corr and stage == "Observe":
            # Very faint marker + tiny bubble, nothing changes (SECTION 5/8)
            self._mark_word(*rng, tag=TAG_OBSERVE)
            self._show_observe_bubble(rng)

        if corr:
            self.memory.pair(word, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(word, corr) if corr else 0.0)
        self._update_placeholder()

    # ---------------- marking in the editor (SECTION 7) ----------------

    def _mark_word(self, start, end, tag):
        """Apply one word-marking tag to the word's range (removes others)."""
        for t in MARK_TAGS:
            self.editor.tag_remove(t, start, end)
        self.editor.tag_add(tag, start, end)

    # ---------------- suggestion bubbles (SECTION 8) ----------------

    def _word_bbox(self, rng):
        try:
            return self.editor.bbox(rng[0], rng[1])
        except Exception:
            return None

    def _place_bubble(self, bbox):
        """Place the bubble canvas just below the marked word (never covering it)."""
        if not bbox:
            self._hide_bubble()
            return
        x0, y0, x1, y1 = bbox
        off_x = self.editor.winfo_x() - self.card1.winfo_x()
        off_y = self.editor.winfo_y() - self.card1.winfo_y()
        self.bubble.place(x=off_x + x0, y=off_y + y1 + 8, anchor="nw")

    def _hide_bubble(self):
        try:
            self.bubble.place_forget()
            self.bubble.delete("all")
        except Exception:
            pass

    def _draw_bubble_body(self, c, text, colour, extra=None):
        """Draw the bubble body (rectangle + tail; Tk has no rounded rect --
        plain rectangle is the closest clean alternative) and the text."""
        w = max(110, len(text) * 9 + 2 * BUBBLE_PAD_X)
        h = 18 + (22 if extra else 0)
        c.create_rectangle(1, 1, w - 1, h - 1, fill=colour, outline="", tags="b")
        cx = w / 2
        # Pointer tail aiming up at the word (bubble sits below the word)
        c.create_polygon(cx - 5, 0, cx + 5, 0, cx, -BUBBLE_TAIL_H,
                         fill=colour, outline="", tags="b")
        c.create_text(cx, 7, text=text, anchor="n", fill=TEXT,
                      font=FONT_SMALL, tags="b")
        if extra:
            c.create_text(cx, 24, text=extra, anchor="n", fill=TEXT,
                          font=FONT_TINY, tags="b")
        return w, h

    def _show_ask_bubble(self, word, corr, conf):
        """Ask bubble (SECTION 8): 'Did you mean X?', confidence, Yes/Keep mine."""
        rng = self.word_range_last(word)
        bb = self._word_bbox(rng) if rng else None
        if not bb:
            self._hide_bubble()
            return
        self._mark_word(rng[0], rng[1], TAG_ASK)
        c = self.bubble
        c.delete("all")
        main = 'Did you mean "{}"?'.format(corr)
        pct = "{:.0f}%".format(conf) if conf else "0%"
        w, h = self._draw_bubble_body(c, main, BUB_AMBER, extra=pct)
        # Buttons "Yes, fix it" / "Keep mine"
        yes = tk.Label(c, text="Yes, fix it", background=BUB_GREEN, fg=TEXT,
                       font=FONT_SMALL, padx=4, pady=1)
        yes.place(x=6, y=h - 12, anchor="w")
        yes.bind("<Button-1>",
                 lambda e: (self._hide_bubble(),
                            self.accept_correction(word, corr)))
        no = tk.Label(c, text="Keep mine", background=BUB_BLUE, fg=TEXT,
                      font=FONT_SMALL, padx=4, pady=1)
        no.place(x=w - 84, y=h - 12, anchor="e")
        no.bind("<Button-1>",
                lambda e: (self._hide_bubble(),
                           self.decline_correction(word, corr)))
        self._place_bubble(bb)

    def _show_correct_bubble(self, corr):
        """Correct bubble (SECTION 8): 'Corrected to X' + small Undo link, fades."""
        rng = self.word_range_last(corr)
        bb = self._word_bbox(rng) if rng else None
        if not bb:
            self._hide_bubble()
            return
        c = self.bubble
        c.delete("all")
        text = 'Corrected to "{}"'.format(corr)
        w, h = self._draw_bubble_body(c, text, BUB_GREEN)
        undo = tk.Label(c, text="Undo", background=BUB_GREEN, fg=TEXT,
                        font=FONT_SMALL, padx=2, underline=True)
        undo.place(x=w - 26, y=h - 10, anchor="e")
        undo.bind("<Button-1>",
                  lambda e: (self._hide_bubble(), self.undo_last_fix()))
        self._place_bubble(bb)
        # Honesty note: Tk has no true fade; hide it after a few seconds.
        self.after(BUBBLE_FADE_MS, self._hide_bubble)

    def _show_leave_bubble(self, event):
        """Leave bubble (SECTION 8): 'Kept as you wrote it' (hover or click)."""
        rng = self._find_marked_range(TAG_LEAVE, event)
        bb = self._word_bbox(rng) if rng else None
        if not bb:
            self._hide_bubble()
            return
        c = self.bubble
        c.delete("all")
        text = "Kept as you wrote it"
        w, h = self._draw_bubble_body(c, text, BUB_BLUE)
        self._place_bubble(bb)

    def _show_observe_bubble(self, rng):
        """Observe bubble (SECTION 5/8): tiny 'Noted. Tacit is still learning'."""
        bb = self._word_bbox(rng)
        if not bb:
            self._hide_bubble()
            return
        c = self.bubble
        c.delete("all")
        text = "Noted. Tacit is still learning"
        self._draw_bubble_body(c, text, OBSERVE_MARK)
        self._place_bubble(bb)

    def _find_marked_range(self, tag, event=None):
        ranges = self.editor.tag_ranges(tag)
        for r in reversed(ranges):
            if event is None:
                return r
            try:
                bb = self.editor.bbox(r[0], r[1])
            except Exception:
                continue
            if bb and bb[0] <= event.x <= bb[2] and bb[1] <= event.y <= bb[3]:
                return r
        return ranges[-1] if ranges else None

    # ---------------- actions (unchanged behaviour) ----------------

    def auto_correct(self, word, corr, rng):
        # Word changes with a brief soft highlight + Correct bubble
        s, e = rng
        self.editor.replace(s, e, corr)
        fr = self.word_range_last(corr)
        if fr:
            self.flash(fr[0], fr[1], BUB_GREEN)
        self._show_correct_bubble(corr)
        self.last_fix = (word, corr)
        self.memory.record_accept(word, corr)

    def accept_correction(self, mistake, corr):
        rng = self.word_range_last(mistake)
        if rng:
            self.editor.replace(rng[0], rng[1], corr)
            fr = self.word_range_last(corr)
            if fr:
                self.flash(fr[0], fr[1], BUB_GREEN)
        self._hide_bubble()
        self.last_fix = (mistake, corr)
        self.memory.record_accept(mistake, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(mistake, corr))

    def decline_correction(self, mistake, corr):
        rng = self.word_range_last(mistake)
        if rng:
            self._mark_word(rng[0], rng[1], TAG_ASK)
        self._hide_bubble()
        self.memory.record_kept(mistake, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(mistake, corr))

    def undo_last_fix(self):
        if self.last_fix is None:
            self.note_set("Nothing to undo yet.")
            return
        mistake, corr = self.last_fix
        rng = self.word_range_last(corr)
        if rng:
            self.editor.replace(rng[0], rng[1], mistake)
            fr = self.word_range_last(mistake)
            if fr:
                self.flash(fr[0], fr[1], OBSERVE_MARK)
        self.last_fix = None
        self.memory.record_undo(mistake, corr)
        self.set_stage()
        self.refresh_table()
        conf = self.memory.confidence(mistake, corr)
        self.set_confidence(conf)
        self.note_set('Undid the last fix of "{}" -> "{}". '
                      'Confidence lowered to {:.0f}%.'
                      .format(corr, mistake, conf))

    # ---------------- actions (unchanged behaviour) ----------------

    def load_demo_history(self):
        # Slightly emphasised button: pre-fill memory with demo counts
        self.memory.seed({
            "teh": {"the": {"accepted": 3, "undone": 0, "kept": 0}},
            "recieve": {"receive": {"accepted": 1, "undone": 0, "kept": 0}},
            "daksh": {"dash": {"accepted": 0, "undone": 0, "kept": 2}},
            "argv_v2": {"argv": {"accepted": 0, "undone": 0, "kept": 2}},
        })
        self.last_fix = None
        self.refresh_table()
        self.set_stage()
        self.set_confidence(self.memory.confidence("teh", "the"))
        self.note_set("Demo history loaded. Stage: {} (Teh->the is Correct at 75%; "
                      "recieve->receive is Ask at 50%; Daksh and argv_v2 are "
                      "Leave).".format(self.memory.stage()))

    def reset(self):
        # Visually quiet button: clear memory and start again from Observe
        self.memory.clear()
        self.pending_words = []
        self.ollama_busy = False
        self.editor.delete("1.0", "end")
        self._hide_bubble()
        self.last_fix = None
        self.refresh_table()
        self.set_stage()
        self.set_confidence(0.0)
        self._update_placeholder()
        self.note_set("Reset: memory cleared, starting from stage Observe.")

    # ---------------- misc ----------------

    def on_close(self):
        try:
            if self.memory is not None:
                self.memory.save()
        except Exception:
            pass
        self.root.destroy()


def main():
    # SECTION 11: Start-up
    root = tk.Tk()
    app = TacitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()



