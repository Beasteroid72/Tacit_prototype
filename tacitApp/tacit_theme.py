"""Colours, type and stylesheet for the Qt interface.

One dark, minimal theme kept in a single place, so the look can be changed
without touching behaviour.  The three stage colours (grey / amber / green)
are the same ones the project uses everywhere else.
"""

# ---- palette ----
BG = "#0D1117"          # window
SURFACE = "#161B22"     # cards
SURFACE_2 = "#1C2333"   # inputs, chips
LINE = "#263040"        # hairline borders
TEXT = "#E6EDF3"
MUTED = "#8B949E"
FAINT = "#5B6673"

GREY = "#6E7681"        # Observe / Leave
AMBER = "#D29922"       # Suggest / Ask
GREEN = "#3FB950"       # Act / Correct
INDIGO = "#6E7BF2"      # accents
RED = "#F85149"         # the Standard keyboard's blind corrections

STAGE_COLOURS = {"Observe": GREY, "Suggest": AMBER, "Act": GREEN}

# ---- editor highlight tints (r, g, b, alpha) ----
TINT_CORRECT = (63, 185, 80, 55)
TINT_ASK = (210, 153, 34, 55)
TINT_LEAVE = (110, 118, 129, 55)
TINT_OBSERVE = (110, 118, 129, 28)
TINT_STANDARD = (248, 81, 73, 55)

# ---- type ----
FONT_STACK = '"Segoe UI", "Helvetica Neue", Arial, sans-serif'
MONO_STACK = '"Menlo", "Consolas", "Courier New", monospace'

HIGHLIGHT_MS = 2000      # how long an editor tint stays
EDIT_IDLE_MS = 1500      # a pause this long judges a hand edit early

QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: {FONT_STACK};
    font-size: 13px;
}}
/* Labels must not carry the window colour, or every one of them paints a
   dark bar across the card it sits on. */
QLabel {{ background: transparent; }}
QFrame#Card {{
    background: {SURFACE};
    border: 1px solid {LINE};
    border-radius: 14px;
}}
QLabel#Wordmark {{
    font-size: 19px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#Tagline   {{ color: {MUTED}; font-size: 11px; }}
QLabel#CardTitle {{ color: {MUTED}; font-size: 11px; font-weight: 600;
                    letter-spacing: 1px; }}
QLabel#StatValue {{ font-size: 21px; font-weight: 600; }}
QLabel#StatLabel {{ color: {MUTED}; font-size: 10px; letter-spacing: 1px; }}
QLabel#StatNote  {{ color: {FAINT}; font-size: 10px; }}
QLabel#Engine    {{ color: {FAINT}; font-size: 11px; }}

QTextEdit#Editor {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    border-radius: 10px;
    padding: 14px;
    font-size: 16px;
    selection-background-color: {INDIGO};
    selection-color: #FFFFFF;
}}

QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    border-radius: 8px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover    {{ border-color: {INDIGO}; }}
QPushButton:pressed  {{ background: {LINE}; }}
QPushButton#Primary  {{ background: {GREEN}; border: none; color: #04150A;
                        font-weight: 600; }}
QPushButton#Primary:hover {{ background: #4CC95E; }}
QPushButton#Ghost    {{ background: transparent; color: {MUTED}; }}
QPushButton#Ghost:hover {{ color: {TEXT}; border-color: {INDIGO}; }}

QTableWidget {{
    background: {SURFACE};
    border: none;
    gridline-color: transparent;
    font-size: 12px;
}}
QTableWidget::item {{ padding: 5px 2px; }}
QTableWidget::item:selected {{ background: {SURFACE_2}; color: {TEXT}; }}
QHeaderView::section {{
    background: {SURFACE};
    color: {MUTED};
    border: none;
    border-bottom: 1px solid {LINE};
    padding: 5px 2px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QListWidget#Log {{
    background: transparent;
    border: none;
    font-size: 11px;
    color: {MUTED};
}}
QListWidget#Log::item {{ padding: 3px 0; border-bottom: 1px solid #1A2130; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 4px;
                               min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QToolTip {{ background: {SURFACE_2}; color: {TEXT}; border: 1px solid {LINE};
            padding: 4px; }}
"""
