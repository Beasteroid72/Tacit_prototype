"""
tacit_app.py -- the Tkinter UI for "Tacit: Autocorrect That Learns You".

Editor on the left, the learned-corrections table on the right.  The engine
(from tacit_engine) proposes corrections, the memory (from tacit_memory) keeps
track of mistakes, corrections, confidence and actions.  Everything runs
locally; nothing is sent anywhere, and there is no real keyboard hook --
this is a text editor you type into.
"""

# --- Settings (tunable) ----------------------------------------------------
FONT = ("Segoe UI", 10)
FONT_TITLE = ("Segoe UI", 11, "bold")
FONT_SMALL = ("Segoe UI", 9)
FONT_NOTE = ("Segoe UI", 8)
STAGE_COLORS = {"Observe": "#9e9e9e", "Suggest": "#ff9800", "Act": "#4caf50"}
COLOR_GREEN = "#4caf50"   # auto-correct / accepted
COLOR_AMBER = "#ff9800"   # asked words
COLOR_GREY = "#9e9e9e"    # left alone / undone
CONF_ASK_MIN = 40.0
FLASH_MS = 400
WINDOW_GEOMETRY = "1080x780"
CONF_BAR_W = 130

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
        self.ask_pair = None      # (mistake, correction) currently asked about
        self.pending_words = []   # words queued while a check is in flight
        self.ollama_busy = False  # True while a check is in flight

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.build_ui()
        self.set_stage()
        self.set_confidence(0.0)

    # ---------------- UI ----------------

    def build_ui(self):
        # ---- top bar: stage indicator + confidence meter + engine label ----
        top = tk.Frame(self.root, bg="#ffffff")
        top.pack(side="top", fill="x", padx=8, pady=(6, 2))

        stage_frame = tk.Frame(top, bg=STAGE_COLORS["Observe"], padx=8, pady=2)
        stage_frame.pack(side="left", fill="y")
        self.stage_frame = stage_frame
        self.stage_label = tk.Label(stage_frame, text="Stage: Observe",
                                    bg=STAGE_COLORS["Observe"], fg="white",
                                    font=FONT_TITLE)
        self.stage_label.pack()

        conf_frame = tk.Frame(top, bg="#ffffff")
        conf_frame.pack(side="left", fill="y", padx=(20, 0))
        self.conf_label = tk.Label(conf_frame, text="Confidence (last word): 0%",
                                   font=FONT)
        self.conf_label.pack(side="top", anchor="w")
        self.conf_canvas = tk.Canvas(conf_frame, width=CONF_BAR_W, height=8,
                                     bg="white", highlightthickness=0)
        self.conf_canvas.pack(side="top", pady=1)

        self.engine_label = tk.Label(top, text="Engine: none yet",
                                     bg="#ffffff", font=FONT_SMALL)
        self.engine_label.pack(side="left", fill="y", padx=(20, 0))

        # ---- main: editor (left) + learned table (right) ----
        main = tk.Frame(self.root)
        main.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 4))

        left = tk.Frame(main, width=600)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        editor_title = tk.Label(left, text="Your editor -- type here (simulated)",
                                font=FONT_TITLE, bg="#ffffff")
        editor_title.pack(anchor="w", pady=(2, 2))

        self.editor = tk.Text(left, font=FONT, wrap="word", undo=True,
                              bg="#ffffff", height=14)
        self.editor.pack(fill="both", expand=True, padx=4, pady=2)
        self.editor.focus()
        self.editor.bind("<KeyRelease>", self.on_key_release)
        self.editor.bind("<Control-z>", lambda e: self.undo_last_fix())

        # "Did you mean X?" box under the editor -- clearly styled, with Yes/No.
        self.ask_frame = tk.Frame(left, bg="#fff8e1",
                                  highlightbackground=COLOR_AMBER,
                                  highlightthickness=2, highlightcolor=COLOR_AMBER,
                                  padx=8, pady=6)
        self.ask_label = tk.Label(self.ask_frame, text="", font=("Segoe UI", 10, "bold"))
        self.ask_label.pack(side="left", fill="x", expand=True)
        self.ask_yes = tk.Button(self.ask_frame, text="Yes", font=FONT,
                                 command=self.on_ask_yes, bg=COLOR_GREEN, fg="white")
        self.ask_yes.pack(side="left", padx=2)
        self.ask_no = tk.Button(self.ask_frame, text="No", font=FONT,
                                command=self.on_ask_no, bg=COLOR_GREY, fg="white")
        self.ask_no.pack(side="left", padx=2)
        self.ask_frame.pack(fill="x", pady=(2, 2))
        self.hide_prompt()

        editor_note = tk.Label(
            left,
            text="Tacit checks the last word as you type a Space or punctuation "
                 "after it.  Shortcut: Ctrl+Z undoes the last fix.",
            font=FONT_NOTE, bg="#ffffff", fg=COLOR_GREY)
        editor_note.pack(anchor="w", pady=(0, 2))

        right = tk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        tree_title = tk.Label(right, text="What Tacit has learned (memory: tacit_memory.json)",
                              font=FONT_TITLE, bg="#ffffff")
        tree_title.pack(anchor="w", pady=(2, 2))

        cols = ["Mistake", "Correction", "Accepted", "Undone", "Confidence %", "Action"]
        self.learned_tree = ttk.Treeview(right, columns=cols, show="headings", height=10)
        for c in cols:
            self.learned_tree.heading(c, text=c)
        self.learned_tree.column("Mistake", width=115, anchor="center")
        self.learned_tree.column("Correction", width=120, anchor="center")
        self.learned_tree.column("Accepted", width=80, anchor="center")
        self.learned_tree.column("Undone", width=80, anchor="center")
        self.learned_tree.column("Confidence %", width=105, anchor="center")
        self.learned_tree.column("Action", width=80, anchor="center")
        self.learned_tree.pack(fill="both", expand=True, padx=4)

        # ---- bottom bar: note + buttons ----
        bottom = tk.Frame(self.root, bg="#ffffff")
        bottom.pack(side="bottom", fill="x", padx=8, pady=(2, 6))

        self.note_label = tk.Label(bottom, text="", bg="#ffffff", font=FONT_SMALL,
                                   fg="#555555")
        self.note_label.pack(side="left", fill="x", expand=True)

        btn_row = tk.Frame(bottom, bg="#ffffff")
        btn_row.pack(side="right")
        for text, cmd in [
            ("Undo last fix", self.undo_last_fix),
            ("Load demo history (accelerated)", self.load_demo_history),
            ("Reset", self.reset),
        ]:
            tk.Button(btn_row, text=text, font=FONT, command=cmd).pack(side="left", padx=3)

        footer = tk.Label(
            self.root,
            text="Footer: simulated editor -- Tacit watches the text box; "
                 "it does not hook your real keyboard.",
            bg="#ffffff", font=FONT_SMALL, fg="#888888")
        footer.pack(side="bottom", fill="x", padx=8, pady=(0, 2))

    # ---------------- helpers ----------------

    def note_set(self, msg):
        self.note_label.config(text=msg)

    def after(self, ms, func):
        self.root.after(int(ms), func)

    def after_idle(self, func):
        self.root.after_idle(func)

    def set_stage(self):
        stage = self.memory.stage()
        self.stage_frame.config(bg=STAGE_COLORS[stage])
        self.stage_label.config(text="Stage: " + stage, bg=STAGE_COLORS[stage])
        return stage

    def set_confidence(self, conf):
        try:
            conf = max(0.0, min(100.0, float(conf)))
            w = int(round(conf / 100.0 * CONF_BAR_W))
            self.conf_canvas.delete("tacit_bar")
            self.conf_canvas.create_rectangle(0, 0, w, 8,
                                              fill=COLOR_GREY, outline="")
        except tk.TclError:
            pass
        self.conf_label.config(text="Confidence (last word): {:.0f}%".format(conf))

    def show_prompt(self, mistake, corr):
        self.ask_pair = (mistake, corr)
        self.ask_label.config(text='Did you mean "{}"?'.format(corr))
        self.ask_frame.pack(fill="x", pady=(2, 2))

    def hide_prompt(self):
        self.ask_frame.pack_forget()
        self.ask_pair = None

    def on_ask_yes(self):
        if self.ask_pair:
            self.accept_correction(*self.ask_pair)

    def on_ask_no(self):
        if self.ask_pair:
            self.decline_correction(*self.ask_pair)

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
        try:
            self.editor.tag_add("tacit_flash", start, end)
            self.editor.tag_config("tacit_flash", bg=color)
            self.after(FLASH_MS,
                       lambda: self.editor.tag_remove("tacit_flash", start, end))
        except tk.TclError:
            pass

    def refresh_table(self):
        tree = self.learned_tree
        tree.delete(*tree.get_children())
        for mistake in sorted(self.memory.data):
            for corr in sorted(self.memory.data[mistake]):
                s = self.memory.data[mistake][corr]
                conf = self.memory.stats_to_conf(s)
                action = self.memory.action(mistake, corr)
                tree.insert("", "end", values=(mistake, corr, s["accepted"],
                                               s["undone"],
                                               "{:.0f}%".format(conf), action))

    # ---------------- keyboard ----------------

    def on_key_release(self, event):
        ch = event.char
        if ch and ch in " .,!?:":
            self.handle_completed_word()

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
        self.hide_prompt()
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
        # Runs on the main thread (via after_idle).
        try:
            # Highlight the mistake this request was deciding about.
            if corr:
                fr = self.word_range_last(word)
                if fr:
                    self.flash(fr[0], fr[1], COLOR_AMBER)
            self._apply_word(word, corr, engine, rng)
            # Process the next queued word, if any.
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
                self.flash(rng[0], rng[1], COLOR_GREY)
        elif corr and stage == "Suggest":
            conf = self.memory.confidence(word, corr)
            action = self.memory.action(word, corr)
            if action == "Ask" and conf >= CONF_ASK_MIN:
                self.show_prompt(word, corr)
                self.flash(rng[0], rng[1], COLOR_AMBER)

        if corr:
            self.memory.pair(word, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(word, corr) if corr else 0.0)

    def update_engine_label(self, engine, corr):
        self.engine_label.config(
            text="Engine: " + str(engine) if engine else "Engine: none needed")

    def auto_correct(self, word, corr, rng):
        s, e = rng
        self.editor.replace(s, e, corr)
        fr = self.word_range_last(corr)
        if fr:
            self.flash(fr[0], fr[1], COLOR_GREEN)
        self.last_fix = (word, corr)
        self.memory.record_accept(word, corr)

    # ---------------- ask box ----------------

    def accept_correction(self, mistake, corr):
        rng = self.word_range_last(mistake)
        if rng:
            self.editor.replace(rng[0], rng[1], corr)
            fr = self.word_range_last(corr)
            if fr:
                self.flash(fr[0], fr[1], COLOR_GREEN)
        self.hide_prompt()
        self.last_fix = (mistake, corr)
        self.memory.record_accept(mistake, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(mistake, corr))

    def decline_correction(self, mistake, corr):
        rng = self.word_range_last(mistake)
        if rng:
            self.flash(rng[0], rng[1], COLOR_GREY)
        self.hide_prompt()
        self.memory.record_kept(mistake, corr)
        self.set_stage()
        self.refresh_table()
        self.set_confidence(self.memory.confidence(mistake, corr))

    # ---------------- buttons ----------------

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
                self.flash(fr[0], fr[1], COLOR_GREY)
        self.last_fix = None
        self.memory.record_undo(mistake, corr)
        self.set_stage()
        self.refresh_table()
        conf = self.memory.confidence(mistake, corr)
        self.set_confidence(conf)
        self.note_set('Undid the last fix of "{}" -> "{}". '
                      'Confidence lowered to {:.0f}%.'
                      .format(corr, mistake, conf))

    def load_demo_history(self):
        self.memory.seed({
            "teh": {"the": {"accepted": 3, "undone": 0, "kept": 0}},
            "recieve": {"receive": {"accepted": 1, "undone": 0, "kept": 0}},
            "daksh": {"dash": {"accepted": 0, "undone": 0, "kept": 2}},
            "argv_v2": {"argv": {"accepted": 0, "undone": 0, "kept": 2}},
        })
        self.hide_prompt()
        self.last_fix = None
        self.refresh_table()
        self.set_stage()
        self.set_confidence(self.memory.confidence("teh", "the"))
        self.note_set("Demo history loaded. Stage: {} (Teh->the is Correct at 75%; "
                      "recieve->receive is Ask at 50%; Daksh and argv_v2 are "
                      "Leave).".format(self.memory.stage()))

    def reset(self):
        self.memory.clear()
        self.pending_words = []
        self.ollama_busy = False
        self.editor.delete("1.0", "end")
        self.hide_prompt()
        self.last_fix = None
        self.refresh_table()
        self.set_stage()
        self.set_confidence(0.0)
        self.note_set("Reset: memory cleared, starting from stage Observe.")

    def on_close(self):
        try:
            if self.memory is not None:
                self.memory.save()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = TacitApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
