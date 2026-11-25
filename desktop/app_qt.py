"""Tacit -- the PyQt interface: autocorrect that learns you.

A dark, minimal rewrite of the Tkinter window, with the behaviour the browser
phone demo gained:

  * Correct / Ask / Leave per mistake-correction pair, driven by confidence
  * the Observe -> Suggest -> Act stages
  * learning from corrections the user types by hand (mngo -> mango)
  * a Standard / Tacit mode switch, so the two can be compared side by side
  * an activity log and an "undos needed" count for each mode

Behaviour lives in memory.py (learning), engine.py (candidates)
and edits.py (judging a hand edit); this module is the interface only.
"""

import os
import sys
import threading


def _ensure_qt_plugin_path():
    """Let Qt find its platform plugin.

    Anaconda ships its own Qt and leaves QT_PLUGIN_PATH empty, which stops
    PyQt6 loading the "cocoa"/"windows" plugin and the app dies at start-up
    with "no Qt platform plugin could be initialized".  Point Qt at the copy
    that came with PyQt6, unless the environment already names one.
    """
    try:
        import PyQt6
    except ImportError:
        return
    plugins = os.path.join(os.path.dirname(PyQt6.__file__), "Qt6", "plugins")
    if not os.path.isdir(plugins):
        return
    if not os.environ.get("QT_PLUGIN_PATH"):
        os.environ["QT_PLUGIN_PATH"] = plugins
    platforms = os.path.join(plugins, "platforms")
    if not os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH") and os.path.isdir(platforms):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = platforms


_ensure_qt_plugin_path()

from PyQt6.QtCore import Qt, QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QListWidget, QMainWindow, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from memory import TacitMemory, CONF_CORRECT, LEAVE_KEPT_MIN, OBSERVE_UNTIL_EVENTS
from engine import (TacitEngine, BUILTIN_CORRECTIONS, is_dictionary_word,
                    ensure_ollama_server)
from edits import classify_edit, word_at
import theme as T

DELIMS = " .,!?:;"
LOG_LIMIT = 40


# ----------------------------------------------------------------- editor ---
class Editor(QTextEdit):
    """Plain-text editor that reports finished words and caret moves."""

    wordFinished = pyqtSignal()
    caretMoved = pyqtSignal(bool)      # True when the move came from typing

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Editor")
        self.setAcceptRichText(False)
        self.setPlaceholderText("Start typing -- Tacit watches this box.")
        self.cursorPositionChanged.connect(lambda: self.caretMoved.emit(False))

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        ch = event.text()
        if ch and ch in DELIMS:
            self.wordFinished.emit()
        if ch:
            self.caretMoved.emit(True)

    def caret(self):
        return self.textCursor().position()

    def set_caret(self, pos):
        cur = self.textCursor()
        cur.setPosition(max(0, min(pos, len(self.toPlainText()))))
        self.setTextCursor(cur)

    def replace_range(self, start, end, text):
        cur = self.textCursor()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        cur.insertText(text)

    def tint(self, start, end, rgba, msec=T.HIGHLIGHT_MS):
        """Briefly colour a range, then clear it again."""
        self._apply_format(start, end, QColor(*rgba))
        if msec:
            QTimer.singleShot(msec, lambda: self._clear_format(start, end))

    def _apply_format(self, start, end, colour):
        cur = self.textCursor()
        pos = cur.position()
        cur.setPosition(start)
        cur.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        fmt = QTextCharFormat()
        fmt.setBackground(colour)
        cur.mergeCharFormat(fmt)
        cur.setPosition(pos)
        self.setTextCursor(cur)

    def _clear_format(self, start, end):
        text_len = len(self.toPlainText())
        if start >= text_len:
            return
        self._apply_format(start, min(end, text_len), QColor(0, 0, 0, 0))


# ----------------------------------------------------------------- worker ---
class EngineWorker(QObject):
    """Runs engine lookups off the UI thread; Ollama can take a second."""

    done = pyqtSignal(str, object, object)      # word, correction, engine name

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def check(self, word, context):
        def run():
            try:
                out = self.engine.check(word, context)
                corr, name = (out + (None,))[:2] if isinstance(out, tuple) else (out, None)
            except Exception:
                corr, name = None, None
            self.done.emit(word, corr, name)

        threading.Thread(target=run, daemon=True).start()


# -------------------------------------------------------------- small bits ---
def card(title=None):
    frame = QFrame()
    frame.setObjectName("Card")
    box = QVBoxLayout(frame)
    box.setContentsMargins(16, 14, 16, 14)
    box.setSpacing(8)
    if title:
        lbl = QLabel(title.upper())
        lbl.setObjectName("CardTitle")
        box.addWidget(lbl)
    return frame, box


class Stat(QFrame):
    """One small number + label tile."""

    def __init__(self, label, value="--", note="", colour=T.TEXT):
        super().__init__()
        self.setObjectName("Card")
        box = QVBoxLayout(self)
        box.setContentsMargins(14, 10, 14, 10)
        box.setSpacing(2)
        self.label = QLabel(label.upper())
        self.label.setObjectName("StatLabel")
        self.value = QLabel(value)
        self.value.setObjectName("StatValue")
        self.value.setStyleSheet(f"color: {colour};")
        self.note = QLabel(note)
        self.note.setObjectName("StatNote")
        self.note.setWordWrap(True)
        box.addWidget(self.label)
        box.addWidget(self.value)
        box.addWidget(self.note)

    def set(self, value=None, note=None, colour=None):
        if value is not None:
            self.value.setText(str(value))
        if note is not None:
            self.note.setText(note)
        if colour is not None:
            self.value.setStyleSheet(f"color: {colour};")


class Meter(QWidget):
    """Thin confidence bar with the 40% and 75% thresholds marked."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(6)
        self.setMinimumWidth(150)
        self._value = 0.0
        self._colour = QColor(T.GREY)

    def set_value(self, pct, colour):
        self._value = max(0.0, min(100.0, pct))
        self._colour = QColor(colour)
        self.update()

    def paintEvent(self, _event):
        from PyQt6.QtGui import QPainter
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(T.LINE))
        p.drawRoundedRect(0, 0, w, h, h / 2, h / 2)
        if self._value > 0:
            p.setBrush(self._colour)
            p.drawRoundedRect(0, 0, int(w * self._value / 100), h, h / 2, h / 2)
        p.setBrush(QColor(T.FAINT))
        for mark in (40, 75):
            p.drawRect(int(w * mark / 100), 0, 1, h)
        p.end()


# -------------------------------------------------------------------- app ---
class TacitWindow(QMainWindow):
    """The window: editor on the left, what Tacit has learned on the right."""

    def __init__(self, memory=None, engine=None):
        super().__init__()
        self.memory = TacitMemory() if memory is None else memory
        self.worker = EngineWorker(TacitEngine() if engine is None else engine)
        self.worker.done.connect(self._engine_done)

        self.mode = "tacit"            # "tacit" or "standard"
        self.last_fix = None           # (mistake, correction, start) of the last auto-fix
        self.last_pair = None
        self.undos = {"tacit": 0, "standard": 0}
        self.pending = []              # words waiting while a check is in flight
        self.busy = False
        self.ask = None                # the pair currently being asked about
        self.edit_session = None       # a word the user went back into
        self.edit_timer = QTimer(self)
        self.edit_timer.setSingleShot(True)
        self.edit_timer.timeout.connect(lambda: self._commit_edit(final=False))

        self.setWindowTitle("Tacit -- Autocorrect That Learns You")
        self.resize(1180, 760)
        self.setMinimumSize(980, 640)
        self._build()
        self._refresh_all()

    # ---------------- layout ----------------

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(18, 16, 18, 14)
        outer.setSpacing(14)
        outer.addLayout(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_editor_card(), 3)
        body.addWidget(self._build_side_panel(), 2)
        outer.addLayout(body)
        outer.addLayout(self._build_footer())

    def _build_header(self):
        row = QHBoxLayout()
        row.setSpacing(14)

        name = QVBoxLayout()
        name.setSpacing(0)
        wordmark = QLabel("TACIT")
        wordmark.setObjectName("Wordmark")
        tagline = QLabel("autocorrect that learns you")
        tagline.setObjectName("Tagline")
        name.addWidget(wordmark)
        name.addWidget(tagline)
        row.addLayout(name)
        row.addSpacing(10)

        # stage pills
        self.stage_pills = {}
        pills = QHBoxLayout()
        pills.setSpacing(6)
        for st in ("Observe", "Suggest", "Act"):
            pill = QLabel(st)
            pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pill.setFixedHeight(24)
            pill.setMinimumWidth(74)
            self.stage_pills[st] = pill
            pills.addWidget(pill)
        row.addLayout(pills)
        row.addStretch(1)

        meter_box = QVBoxLayout()
        meter_box.setSpacing(3)
        self.conf_caption = QLabel("confidence --")
        self.conf_caption.setObjectName("Engine")
        self.meter = Meter()
        meter_box.addWidget(self.conf_caption)
        meter_box.addWidget(self.meter)
        row.addLayout(meter_box)

        self.engine_label = QLabel("engine: idle")
        self.engine_label.setObjectName("Engine")
        row.addWidget(self.engine_label)

        self.mode_btn = QPushButton("Keyboard: Tacit")
        self.mode_btn.setToolTip(
            "Switch between the Tacit keyboard and a standard one that never learns")
        self.mode_btn.clicked.connect(self._toggle_mode)
        row.addWidget(self.mode_btn)
        return row

    def _build_editor_card(self):
        frame, box = card("your editor  ·  simulated")
        self.editor = Editor()
        self.editor.wordFinished.connect(self._word_finished)
        self.editor.caretMoved.connect(self._caret_moved)
        box.addWidget(self.editor, 1)

        # The suggestion strip, same idea as the phone demo's.
        self.strip = QFrame()
        self.strip.setObjectName("Card")
        strip = QHBoxLayout(self.strip)
        strip.setContentsMargins(12, 8, 12, 8)
        strip.setSpacing(8)
        self.strip_dot = QLabel("●")
        self.strip_text = QLabel("Tacit is watching. Type a word and finish it with a space.")
        self.strip_text.setObjectName("StatNote")
        self.strip_yes = QPushButton("Yes, fix it")
        self.strip_yes.setObjectName("Primary")
        self.strip_no = QPushButton("Keep mine")
        self.strip_undo = QPushButton("Undo")
        self.strip_yes.clicked.connect(self._accept_ask)
        self.strip_no.clicked.connect(self._decline_ask)
        self.strip_undo.clicked.connect(self.undo_last_fix)
        strip.addWidget(self.strip_dot)
        strip.addWidget(self.strip_text, 1)
        strip.addWidget(self.strip_yes)
        strip.addWidget(self.strip_no)
        strip.addWidget(self.strip_undo)
        box.addWidget(self.strip)
        self._set_strip("idle")

        note = QLabel("Tacit checks a word when you finish it. Go back into a word, "
                      "fix the spelling yourself, and it learns that too.")
        note.setObjectName("StatNote")
        note.setWordWrap(True)
        box.addWidget(note)
        return frame

    def _build_side_panel(self):
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(14)

        stats = QGridLayout()
        stats.setSpacing(10)
        self.stat_stage = Stat("stage", "Observe", "watching only", T.GREY)
        self.stat_conf = Stat("confidence · last pair", "--",
                              "ask ≥ 40%  ·  correct ≥ 75%")
        self.stat_undo_std = Stat("undos · standard", "0", "it never learns", T.RED)
        self.stat_undo_tac = Stat("undos · tacit", "0", "each one lowers confidence",
                                  T.GREEN)
        for i, w in enumerate((self.stat_stage, self.stat_conf,
                               self.stat_undo_std, self.stat_undo_tac)):
            stats.addWidget(w, i // 2, i % 2)
        col.addLayout(stats)

        table_card, table_box = card("what tacit has learned")
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Mistake", "Correction", "✓", "✎", "↶", "Conf.", "Action"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for c in range(2, 7):
            head.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setToolTip("✓ accepted   ✎ fixed by you   ↶ undone")
        table_box.addWidget(self.table)
        self.empty_note = QLabel("Nothing yet — try typing “teh ”.")
        self.empty_note.setObjectName("StatNote")
        table_box.addWidget(self.empty_note)
        col.addWidget(table_card, 3)

        log_card, log_box = card("activity")
        self.log = QListWidget()
        self.log.setObjectName("Log")
        log_box.addWidget(self.log)
        col.addWidget(log_card, 2)
        return panel

    def _build_footer(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.note = QLabel("Everything runs on this computer. Nothing you type is sent anywhere.")
        self.note.setObjectName("StatNote")
        row.addWidget(self.note, 1)
        for text, slot, name in (
            ("Undo last fix", self.undo_last_fix, "Ghost"),
            ("Load demo history", self.load_demo_history, ""),
            ("Reset", self.reset, "Ghost"),
        ):
            b = QPushButton(text)
            if name:
                b.setObjectName(name)
            b.clicked.connect(slot)
            row.addWidget(b)
        return row

    # ---------------- strip ----------------

    def _set_strip(self, kind, **kw):
        """kind: idle | ask | undo | message"""
        colour = {"ask": T.AMBER, "undo": T.INDIGO}.get(kind, T.FAINT)
        if kind == "idle":
            colour = T.STAGE_COLOURS.get(self.memory.stage(), T.GREY) \
                if self.mode == "tacit" else T.GREY
        self.strip_dot.setStyleSheet(f"color: {colour};")
        self.strip_yes.setVisible(kind == "ask")
        self.strip_no.setVisible(kind == "ask")
        self.strip_undo.setVisible(kind == "undo")
        if kind == "ask":
            self.strip_text.setText(
                f'Did you mean “{kw["corr"]}” instead of “{kw["word"]}”?  ({kw["conf"]:.0f}%)')
        elif kind == "undo":
            self.strip_text.setText(f'Corrected “{kw["word"]}” → “{kw["corr"]}”.')
        elif kind == "message":
            self.strip_text.setText(kw["text"])
        else:
            self.strip_text.setText(
                "Tacit is watching. Finish a word with a space."
                if self.mode == "tacit" else
                "Standard keyboard: fixed rules, the same for everyone.")

    def _log(self, text):
        self.log.insertItem(0, text)
        while self.log.count() > LOG_LIMIT:
            self.log.takeItem(self.log.count() - 1)

    # ---------------- typing ----------------

    def _word_finished(self):
        self._commit_edit(final=True)
        text = self.editor.toPlainText()
        pos = self.editor.caret()
        if pos == 0 or text[pos - 1] not in DELIMS:
            return
        w = word_at(text, pos - 1)
        if not w or w[1] != pos - 1:
            return
        start, _end, word = w
        self.ask = None

        if self.mode == "standard":
            self._standard_correct(word, start)
            return

        self.memory.events += 1
        if self.busy:
            self.pending.append((word, text[-80:], start))
            return
        self.busy = True
        self.worker.check(word, text[-80:])
        self._pending_start = start

    def _standard_correct(self, word, start):
        """The comparison keyboard: always the same fix, and it never learns."""
        corr = BUILTIN_CORRECTIONS.get(word.lower())
        if not corr:
            self._set_strip("idle")
            return
        corr = self._match_case(word, corr)
        self.editor.replace_range(start, start + len(word), corr)
        self.editor.tint(start, start + len(corr), T.TINT_STANDARD)
        self.last_fix = (word, corr, start, "standard")
        self._set_strip("undo", word=word, corr=corr)
        self._log(f"Standard: corrected {word} → {corr} (always, no learning)")

    def _engine_done(self, word, corr, engine_name):
        start = getattr(self, "_pending_start", None)
        if start is not None:
            self._apply_word(word, corr, engine_name, start)
        if self.pending:
            w, ctx, st = self.pending.pop(0)
            self._pending_start = st
            self.worker.check(w, ctx)
        else:
            self.busy = False
        self._refresh_all()

    def _apply_word(self, word, corr, engine_name, start):
        if not corr:
            # Nothing from the dictionaries: use what the user taught Tacit
            # by fixing this word themselves.
            learned = self.memory.personal_fix(word)
            if learned:
                corr, engine_name = learned, "your own edits"
        self.engine_label.setText(f"engine: {engine_name or 'nothing needed'}")
        if not corr:
            self._set_strip("idle")
            return

        key = word.lower()
        stage = self.memory.stage()
        action = self.memory.action(key, corr)
        self.last_pair = (key, corr)
        end = start + len(word)

        if stage == "Observe":
            self.editor.tint(start, end, T.TINT_OBSERVE)
            self._set_strip("message", text=f'Noted “{word}” — still watching.')
            self._log(f"Observe: noticed {word} (changing nothing yet)")
        elif action == "Correct":
            shown = self._match_case(word, corr)
            self.editor.replace_range(start, end, shown)
            self.editor.tint(start, start + len(shown), T.TINT_CORRECT)
            self.memory.record_accept(key, corr)
            self.last_fix = (word, shown, start, "tacit")
            self._set_strip("undo", word=word, corr=shown)
            self._log(f"Act: corrected {word} → {shown} "
                      f"({self.memory.confidence(key, corr):.0f}%)")
        elif action == "Leave":
            self.editor.tint(start, end, T.TINT_LEAVE)
            self._set_strip("message", text=f'Left “{word}” as you wrote it.')
            self._log(f"Leave: kept {word} as you like it")
        else:
            # Ask -- from the very first sighting, as in the phone demo.
            self.editor.tint(start, end, T.TINT_ASK, msec=0)
            self.ask = (key, corr, word, start)
            self._set_strip("ask", word=word, corr=self._match_case(word, corr),
                            conf=self.memory.confidence(key, corr))
            self._log(f'Ask: "Did you mean {corr}?" '
                      f'({self.memory.confidence(key, corr):.0f}%)')
        self.memory.pair(key, corr)
        self.memory.save()

    @staticmethod
    def _match_case(word, corr):
        if len(word) > 1 and word.isupper():
            return corr.upper()
        if word[:1].isupper():
            return corr[:1].upper() + corr[1:]
        return corr

    # ---------------- answering the ask ----------------

    def _accept_ask(self):
        if not self.ask:
            return
        key, corr, word, start = self.ask
        shown = self._match_case(word, corr)
        text = self.editor.toPlainText()
        if text[start:start + len(word)] == word:
            self.editor.replace_range(start, start + len(word), shown)
            self.editor.tint(start, start + len(shown), T.TINT_CORRECT)
        self.memory.record_accept(key, corr)
        self.last_fix = (word, shown, start, "tacit")
        self.last_pair = (key, corr)
        self.ask = None
        self._set_strip("message",
                        text=f'Learned: {word} → {shown} '
                             f'({self.memory.confidence(key, corr):.0f}%)')
        self._log(f"You accepted {shown} → {self.memory.confidence(key, corr):.0f}%")
        self._refresh_all()

    def _decline_ask(self):
        if not self.ask:
            return
        key, corr, word, start = self.ask
        self.memory.record_kept(key, corr)
        self.editor.tint(start, start + len(word), T.TINT_LEAVE)
        self.last_pair = (key, corr)
        kept = self.memory.pair(key, corr)["kept"]
        self.ask = None
        self._set_strip("message",
                        text=(f'Got it — “{word}” will be left alone.'
                              if kept >= LEAVE_KEPT_MIN else f'Kept “{word}”.'))
        self._log(f"You kept {word} (kept {kept}×"
                  f"{' → now Leave' if kept >= LEAVE_KEPT_MIN else ''})")
        self._refresh_all()

    def undo_last_fix(self):
        if not self.last_fix:
            self.note.setText("Nothing to undo yet.")
            return
        word, corr, start, mode = self.last_fix
        text = self.editor.toPlainText()
        if text[start:start + len(corr)] == corr:
            self.editor.replace_range(start, start + len(corr), word)
            self.editor.tint(start, start + len(word), T.TINT_LEAVE)
        self.undos[mode] += 1
        if mode == "tacit":
            key = word.lower()
            self.memory.record_undo(key, corr.lower())
            self.last_pair = (key, corr.lower())
            conf = self.memory.confidence(key, corr.lower())
            self._set_strip("message",
                            text=f'Undone — Tacit will be careful with “{word}”.')
            self._log(f"You undid {word} → {corr}: confidence drops to {conf:.0f}%")
        else:
            self._set_strip("message",
                            text="Undone — the standard keyboard will do it again.")
            self._log(f"You undid Standard's {word} → {corr} (it does not learn)")
        self.last_fix = None
        self._refresh_all()

    # ---------------- learning from the user's own edits ----------------

    def _caret_moved(self, typing=False):
        text = self.editor.toPlainText()
        pos = self.editor.caret()

        if self.edit_session is not None:
            start = self.edit_session["start"]
            w = word_at(text, start)
            if not w or pos < w[0] or pos > w[1]:
                self._commit_edit(final=True)
            elif typing:
                self.edit_timer.start(T.EDIT_IDLE_MS)

        if self.edit_session is None and pos < len(text):
            # Only words with text after them: typing at the end is not an edit.
            w = word_at(text, pos)
            if w:
                self.edit_session = {"start": w[0], "original": w[2], "learned": None}

    def _is_known(self, word):
        if is_dictionary_word(word):
            return True
        return any(word.lower() in corrs for corrs in self.memory.data.values())

    def _apply_self_edit(self, kind, original, final, sign):
        a, b = original.lower(), final.lower()
        mistake, corr = (a, b) if kind == "fix" else (b, a)
        s = self.memory.pair(mistake, corr)
        if kind == "fix":
            s["accepted"] += sign
            s["self_fixed"] = s.get("self_fixed", 0) + sign
        else:
            s["undone"] += sign
            self.undos["tacit"] += sign
        if sign < 0:
            self.memory.forget_pair(mistake, corr)
        self.memory.save()
        return mistake, corr

    def _commit_edit(self, final=True):
        self.edit_timer.stop()
        sess = self.edit_session
        if sess is None or self.mode != "tacit":
            self.edit_session = None
            return
        if final:
            self.edit_session = None

        text = self.editor.toPlainText()
        w = word_at(text, sess["start"])
        word = w[2] if w and w[0] == sess["start"] else None

        learned = sess.get("learned")
        if learned is not None:
            if learned["final"] == word:
                return
            self._apply_self_edit(learned["kind"], sess["original"],
                                  learned["final"], -1)
            sess["learned"] = None

        kind = None
        if word:
            kind = classify_edit(sess["original"], word, self._is_known,
                                 self.memory.has_pair, require_known=not final)
        if kind is None:
            if final and word and word.lower() != sess["original"].lower():
                self._log(f"Not learned: {sess['original']} → {word} "
                          f"(too different to be a spelling fix)")
            self._refresh_all()
            return

        mistake, corr = self._apply_self_edit(kind, sess["original"], word, +1)
        if not final:
            sess["learned"] = {"kind": kind, "final": word}
        self.last_fix = None
        self.last_pair = (mistake, corr)
        conf = self.memory.confidence(mistake, corr)
        self.editor.tint(sess["start"], sess["start"] + len(word),
                         T.TINT_CORRECT if kind == "fix" else T.TINT_LEAVE)
        if kind == "fix":
            self._set_strip("message",
                            text=f'Learned from your edit: {sess["original"]} → {word}')
            self._log(f"Learned from your edit: {sess['original']} → {word} "
                      f"({conf:.0f}%)")
        else:
            self._set_strip("message",
                            text=f'Undone — Tacit will be careful with “{word}”.')
            self._log(f"You changed {sess['original']} back to {word}: "
                      f"confidence drops to {conf:.0f}%")
        self._refresh_all()

    # ---------------- mode, buttons ----------------

    def _toggle_mode(self):
        self.mode = "standard" if self.mode == "tacit" else "tacit"
        self.edit_timer.stop()
        self.edit_session = None
        self.ask = None
        self.last_fix = None
        self.mode_btn.setText("Keyboard: Tacit" if self.mode == "tacit"
                              else "Keyboard: Standard")
        self._log(f"Switched to the {self.mode.capitalize()} keyboard")
        self._set_strip("idle")
        self._refresh_all()

    def load_demo_history(self):
        self.memory.seed({
            "teh": {"the": {"accepted": 3, "undone": 0, "kept": 0}},
            "recieve": {"receive": {"accepted": 1, "undone": 0, "kept": 0}},
            "daksh": {"dash": {"accepted": 0, "undone": 0, "kept": 2}},
            "argv_v2": {"argv": {"accepted": 0, "undone": 0, "kept": 2}},
        })
        self.edit_timer.stop()
        self.edit_session = None
        self.ask = None
        self.last_fix = None
        self.last_pair = ("teh", "the")
        self._set_strip("message", text="Demo history loaded.")
        self._log(f"Loaded demo history — stage {self.memory.stage()}")
        self._refresh_all()

    def reset(self):
        self.memory.clear()
        self.edit_timer.stop()
        self.edit_session = None
        self.ask = None
        self.last_fix = None
        self.last_pair = None
        self.undos = {"tacit": 0, "standard": 0}
        self.pending = []
        self.busy = False
        self.editor.clear()
        self.log.clear()
        self._set_strip("idle")
        self.note.setText("Memory cleared — back to the Observe stage.")
        self._refresh_all()

    # ---------------- painting the state ----------------

    def _refresh_all(self):
        stage = self.memory.stage()
        for name, pill in self.stage_pills.items():
            on = (T.STAGE_COLOURS[name] if self._stage_reached(stage, name)
                  else None)
            if on and self.mode == "tacit":
                pill.setStyleSheet(
                    f"background: {on}; color: #0D1117; border-radius: 12px;"
                    f"font-size: 11px; font-weight: 600;")
            else:
                pill.setStyleSheet(
                    f"background: {T.SURFACE_2}; color: {T.FAINT};"
                    f"border-radius: 12px; font-size: 11px;")

        self.stat_stage.set(
            stage,
            {"Observe": f"words seen {self.memory.events} / {OBSERVE_UNTIL_EVENTS}",
             "Suggest": f"words seen {self.memory.events} · asking when unsure",
             "Act": f"words seen {self.memory.events} · correcting what you trust"}[stage],
            T.STAGE_COLOURS[stage])

        if self.last_pair:
            m, c = self.last_pair
            conf = self.memory.confidence(m, c)
            action = self.memory.action(m, c)
            colour = {"Correct": T.GREEN, "Ask": T.AMBER,
                      "Leave": T.GREY}[action]
            self.stat_conf.set(f"{conf:.0f}%", f"{m} → {c} · {action}", colour)
            self.meter.set_value(conf, colour)
            self.conf_caption.setText(f"confidence {conf:.0f}%")
        else:
            self.stat_conf.set("--", "ask ≥ 40%  ·  correct ≥ 75%", T.TEXT)
            self.meter.set_value(0, T.GREY)
            self.conf_caption.setText("confidence --")

        self.stat_undo_std.set(self.undos["standard"])
        self.stat_undo_tac.set(self.undos["tacit"])
        self._refresh_table()

    @staticmethod
    def _stage_reached(current, name):
        order = ["Observe", "Suggest", "Act"]
        return order.index(current) >= order.index(name)

    def _refresh_table(self):
        rows = [(m, c, s) for m in sorted(self.memory.data)
                for c, s in sorted(self.memory.data[m].items())]
        self.table.setRowCount(len(rows))
        self.empty_note.setVisible(not rows)
        mono = QFont(T.MONO_STACK.split(",")[0].strip('"'))
        mono.setPointSize(11)
        for r, (m, c, s) in enumerate(rows):
            conf = self.memory.stats_to_conf(s)
            action = self.memory.action(m, c)
            colour = {"Correct": T.GREEN, "Ask": T.AMBER, "Leave": T.GREY}[action]
            values = [m, c, str(s["accepted"]), str(s.get("self_fixed", 0)),
                      str(s["undone"]), f"{conf:.0f}%", action]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col in (0, 1):
                    item.setFont(mono)
                if col == 6:
                    item.setForeground(QColor(colour))
                self.table.setItem(r, col, item)

    def closeEvent(self, event):
        try:
            self._commit_edit(final=True)
            self.memory.save()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    # Wake the local LLM before the window opens, so the first word typed can
    # already reach it.  Harmless when Ollama is not installed.
    ensure_ollama_server()
    app = QApplication(sys.argv)
    app.setStyleSheet(T.QSS)
    win = TacitWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
