#!/usr/bin/env python3
"""
DnD Offline Pro — Desktop GUI (PyQt6)
Run:     python src/dnd_desktop.py [--model PATH] [--scenario dungeon|tavern|wilderness]
Install: pip install PyQt6
"""

import sys
import os
import time
import textwrap
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QProgressBar,
    QFrame, QSplitter, QStackedWidget, QFormLayout, QComboBox, QSpinBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

from dnd_offline import (
    CHARACTER_CLASSES, DEFAULT_HP, SCENARIOS,
    build_prompt, generate_memory, load_pipeline,
    save_session, format_duration, MEMORY_INTERVAL,
)

# ── Palette ───────────────────────────────────────────────────────────────────

DARK_BG  = "#0a0a0f"
PANEL_BG = "#14120c"
GOLD     = "#c9a227"
CREAM    = "#e8d5b7"
BORDER   = "#3d2f1a"
RED_HP   = "#8b0000"
AMBER_HP = "#8b6914"
GREEN_HP = "#2d5a27"
BLUE_PLR = "#4a6a8e"
DIM_TEXT = "#6b5c3e"

STYLESHEET = f"""
* {{ font-family: Georgia, serif; color: {CREAM}; }}

QMainWindow, QWidget, QStackedWidget {{ background-color: {DARK_BG}; }}

QFrame {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
}}

QTextEdit {{
    background-color: {PANEL_BG};
    border: none;
    font-size: 14px;
    padding: 16px;
}}

QLineEdit {{
    background-color: {PANEL_BG};
    border: 2px solid {BORDER};
    border-radius: 3px;
    font-family: Consolas, "Courier New", monospace;
    font-size: 13px;
    padding: 6px 10px;
    color: {CREAM};
}}
QLineEdit:focus {{ border-color: {GOLD}; }}

QPushButton {{
    background-color: {GOLD};
    color: {DARK_BG};
    border: none;
    font-weight: bold;
    letter-spacing: 2px;
    padding: 8px 18px;
    border-radius: 3px;
    font-size: 12px;
}}
QPushButton:hover  {{ background-color: #d4aa33; }}
QPushButton:disabled {{ background-color: #3d2f1a; color: {DIM_TEXT}; }}

QLabel {{ background: transparent; border: none; color: {CREAM}; }}

QComboBox, QSpinBox {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 4px 8px;
    color: {CREAM};
    min-height: 28px;
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL_BG};
    selection-background-color: {BORDER};
    color: {CREAM};
    border: 1px solid {BORDER};
}}

QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 3px;
    background-color: {DARK_BG};
    max-height: 10px;
    text-align: center;
    font-size: 0px;
}}
QProgressBar::chunk {{ border-radius: 2px; }}

QSplitter::handle {{ background-color: {BORDER}; }}
QScrollBar:vertical {{
    background: {DARK_BG}; width: 6px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 3px; min-height: 20px;
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{ height: 0px; }}
"""


# ── Worker threads ─────────────────────────────────────────────────────────────

class ModelLoader(QThread):
    loaded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, model_dir: str):
        super().__init__()
        self.model_dir = model_dir

    def run(self):
        try:
            gen = load_pipeline(self.model_dir)
            self.loaded.emit(gen)
        except Exception as exc:
            self.failed.emit(str(exc))


class InferenceThread(QThread):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, generator, prompt: str, kwargs: dict):
        super().__init__()
        self.generator = generator
        self.prompt    = prompt
        self.kwargs    = kwargs

    def run(self):
        try:
            text = self.generator(self.prompt, **self.kwargs)[0]["generated_text"].strip()
            self.done.emit(text)
        except Exception as exc:
            self.error.emit(str(exc))


class MemoryThread(QThread):
    done = pyqtSignal(str)

    def __init__(self, generator, history: list):
        super().__init__()
        self.generator = generator
        self.history   = history

    def run(self):
        try:
            result = generate_memory(self.generator, self.history)
            self.done.emit(result)
        except Exception:
            self.done.emit("")


# ── Story text widget ──────────────────────────────────────────────────────────

class StoryWidget(QTextEdit):

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Georgia", 14))
        self._timer    = QTimer(self)
        self._buf      = ""
        self._buf_pos  = 0
        self._timer.setInterval(14)
        self._timer.timeout.connect(self._tick)

    def _fmt_narrator(self) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(CREAM))
        return f

    def _fmt_player(self) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(BLUE_PLR))
        f.setFontItalic(True)
        return f

    def _insert(self, text: str, fmt: QTextCharFormat):
        c = self.textCursor()
        c.movePosition(QTextCursor.MoveOperation.End)
        c.insertText(text, fmt)
        self.setTextCursor(c)
        self.ensureCursorVisible()

    def append_narrator(self, text: str, animate: bool = True):
        self._insert("\n\n", self._fmt_narrator())
        if animate:
            self._buf     = text
            self._buf_pos = 0
            self._timer.start()
        else:
            self._insert(text, self._fmt_narrator())

    def append_player(self, text: str):
        self._insert(f"\n\n> {text}", self._fmt_player())

    def _tick(self):
        if self._buf_pos >= len(self._buf):
            self._timer.stop()
            return
        self._insert(self._buf[self._buf_pos], self._fmt_narrator())
        self._buf_pos += 1

    def is_animating(self) -> bool:
        return self._timer.isActive()

    def skip_animation(self):
        if self._timer.isActive():
            self._timer.stop()
            remaining = self._buf[self._buf_pos:]
            if remaining:
                self._insert(remaining, self._fmt_narrator())
            self._buf_pos = len(self._buf)


# ── Character sheet panel ──────────────────────────────────────────────────────

class CharacterPanel(QFrame):

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(180)
        self.setMaximumWidth(260)

        v = QVBoxLayout(self)
        v.setSpacing(6)
        v.setContentsMargins(14, 14, 14, 14)

        def lbl(text="", style="") -> QLabel:
            l = QLabel(text)
            if style:
                l.setStyleSheet(style)
            return l

        self.name_lbl  = lbl(style=f"font-size:15px;font-weight:bold;color:{GOLD};letter-spacing:2px;")
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_lbl = lbl(style=f"font-size:11px;font-style:italic;color:{CREAM};")
        self.class_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"background:{BORDER};border:none;max-height:1px;")

        self.hp_bar = QProgressBar()
        self.hp_bar.setFixedHeight(10)
        self.hp_bar.setTextVisible(False)

        self.hp_lbl   = lbl(style=f"font-size:11px;color:{CREAM};")
        self.diff_lbl = lbl(style=f"font-size:10px;color:{DIM_TEXT};")
        self.stat_lbl = lbl(style=f"font-size:10px;color:{DIM_TEXT};")

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"background:{BORDER};border:none;max-height:1px;")

        inv_head = lbl("INVENTORY", f"font-size:9px;color:{GOLD};letter-spacing:2px;font-weight:bold;")
        self.inv_lbl = QLabel("(empty)")
        self.inv_lbl.setStyleSheet(f"font-size:11px;color:{CREAM};")
        self.inv_lbl.setWordWrap(True)
        self.inv_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.fx_head = lbl("EFFECTS", f"font-size:9px;color:{GOLD};letter-spacing:2px;font-weight:bold;")
        self.fx_head.setVisible(False)
        self.fx_lbl = QLabel("")
        self.fx_lbl.setStyleSheet(f"font-size:11px;color:{RED_HP};")
        self.fx_lbl.setWordWrap(True)
        self.fx_lbl.setVisible(False)

        for w in (self.name_lbl, self.class_lbl, sep1, self.hp_bar, self.hp_lbl,
                  self.diff_lbl, self.stat_lbl, sep2, inv_head, self.inv_lbl,
                  self.fx_head, self.fx_lbl):
            v.addWidget(w)
        v.addStretch()

    def refresh_character(self, character: dict, turn: int, elapsed: str):
        self.name_lbl.setText(character.get("name", "Adventurer").upper())
        self.class_lbl.setText(character.get("class", "Fighter"))

        hp_c = character.get("hp_current", 10)
        hp_m = character.get("hp_max", 10)
        self.hp_bar.setMaximum(max(1, hp_m))
        self.hp_bar.setValue(max(0, hp_c))
        self.hp_lbl.setText(f"HP  {hp_c} / {hp_m}")

        ratio = hp_c / hp_m if hp_m > 0 else 0
        color = GREEN_HP if ratio > 0.5 else (AMBER_HP if ratio > 0.25 else RED_HP)
        self.hp_bar.setStyleSheet(
            f"QProgressBar {{ background:{DARK_BG}; border:1px solid {BORDER}; border-radius:3px; }}"
            f"QProgressBar::chunk {{ background:{color}; border-radius:2px; }}"
        )

        diff = character.get("difficulty", "normal").capitalize()
        self.diff_lbl.setText(f"Difficulty: {diff}")
        self.stat_lbl.setText(f"Turn {turn}  ·  {elapsed}")

        inv = character.get("inventory", [])
        self.inv_lbl.setText("\n".join(f"· {i}" for i in inv) if inv else "(empty)")

        fx = character.get("effects", [])
        has_fx = bool(fx)
        self.fx_head.setVisible(has_fx)
        self.fx_lbl.setVisible(has_fx)
        if has_fx:
            self.fx_lbl.setText("\n".join(f"· {e}" for e in fx))


# ── Setup screen ───────────────────────────────────────────────────────────────

class SetupPanel(QWidget):
    begin = pyqtSignal(dict, str)   # character dict, scenario key

    def __init__(self):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setContentsMargins(40, 40, 40, 40)

        card = QFrame()
        card.setMaximumWidth(500)
        card.setStyleSheet(
            f"QFrame {{ background:{PANEL_BG}; border:1px solid {BORDER}; border-radius:6px; }}"
        )
        v = QVBoxLayout(card)
        v.setSpacing(14)
        v.setContentsMargins(40, 36, 40, 36)

        title = QLabel("DnD Offline Pro")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size:28px;font-weight:bold;color:{GOLD};letter-spacing:4px;"
            f"border:none;background:transparent;"
        )

        sub = QLabel("Fully local · No network required · Runs on CPU")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"font-size:11px;color:{DIM_TEXT};border:none;background:transparent;")

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def flbl(text: str) -> QLabel:
            l = QLabel(text)
            l.setStyleSheet(
                f"color:{GOLD};font-size:11px;letter-spacing:1px;border:none;background:transparent;"
            )
            return l

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Sable")

        self.class_combo = QComboBox()
        self.class_combo.addItems(list(CHARACTER_CLASSES.keys()))
        self.class_combo.currentTextChanged.connect(
            lambda cls: self.hp_spin.setValue(DEFAULT_HP.get(cls, 10))
        )

        self.hp_spin = QSpinBox()
        self.hp_spin.setRange(1, 30)
        self.hp_spin.setValue(DEFAULT_HP["Fighter"])

        self.scenario_combo = QComboBox()
        self.scenario_combo.addItems([s.capitalize() for s in SCENARIOS.keys()])

        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Easy", "Normal", "Hard"])
        self.diff_combo.setCurrentText("Normal")

        form.addRow(flbl("Name"),        self.name_input)
        form.addRow(flbl("Class"),       self.class_combo)
        form.addRow(flbl("Starting HP"), self.hp_spin)
        form.addRow(flbl("Scenario"),    self.scenario_combo)
        form.addRow(flbl("Difficulty"),  self.diff_combo)

        self.status_lbl = QLabel("Loading model…")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(
            f"font-size:11px;color:{DIM_TEXT};border:none;background:transparent;"
        )

        self.begin_btn = QPushButton("BEGIN ADVENTURE")
        self.begin_btn.setEnabled(False)
        self.begin_btn.setFixedHeight(44)
        self.begin_btn.clicked.connect(self._on_begin)

        v.addWidget(title)
        v.addWidget(sub)
        v.addSpacing(8)
        v.addLayout(form)
        v.addSpacing(6)
        v.addWidget(self.status_lbl)
        v.addWidget(self.begin_btn)

        outer.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)

    def mark_ready(self):
        self.status_lbl.setText("Model ready.")
        self.begin_btn.setEnabled(True)

    def mark_error(self, msg: str):
        self.status_lbl.setText(f"Error: {msg}")
        self.status_lbl.setStyleSheet(
            "font-size:11px;color:#8b0000;border:none;background:transparent;"
        )

    def _on_begin(self):
        name     = self.name_input.text().strip() or "Adventurer"
        cls      = self.class_combo.currentText()
        hp       = self.hp_spin.value()
        scenario = self.scenario_combo.currentText().lower()
        diff     = self.diff_combo.currentText().lower()
        character = {
            "name": name, "class": cls,
            "hp_max": hp, "hp_current": hp,
            "inventory": [], "effects": [],
            "difficulty": diff, "memory": "",
        }
        self.begin.emit(character, scenario)


# ── Game screen ────────────────────────────────────────────────────────────────

class GamePanel(QWidget):

    def __init__(self):
        super().__init__()
        self.character     = {}
        self.history       = []
        self.generator     = None
        self.turn          = 0
        self.session_start = time.time()
        self._last_action  = ""
        self._inf_thread   = None
        self._mem_thread   = None

        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._tick_clock)
        self._clock.start()

        self._build_ui()

    def _build_ui(self):
        h = QHBoxLayout(self)
        h.setSpacing(0)
        h.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── Left column ───────────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet(f"background:{DARK_BG};border:none;")
        lv = QVBoxLayout(left)
        lv.setSpacing(0)
        lv.setContentsMargins(0, 0, 0, 0)

        title_bar = QFrame()
        title_bar.setFixedHeight(38)
        title_bar.setStyleSheet(
            f"QFrame {{ background:{PANEL_BG}; border:none; border-bottom:1px solid {BORDER}; }}"
        )
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(16, 0, 16, 0)
        app_lbl = QLabel("DnD Offline Pro")
        app_lbl.setStyleSheet(
            f"font-size:13px;font-weight:bold;color:{GOLD};letter-spacing:3px;"
            f"border:none;background:transparent;"
        )
        self.turn_lbl = QLabel("Turn 0")
        self.turn_lbl.setStyleSheet(
            f"font-size:10px;color:{DIM_TEXT};border:none;background:transparent;"
        )
        tb.addWidget(app_lbl)
        tb.addStretch()
        tb.addWidget(self.turn_lbl)

        self.story = StoryWidget()

        input_bar = QFrame()
        input_bar.setFixedHeight(56)
        input_bar.setStyleSheet(
            f"QFrame {{ background:{PANEL_BG}; border:none; border-top:1px solid {BORDER}; }}"
        )
        ib = QHBoxLayout(input_bar)
        ib.setContentsMargins(12, 8, 12, 8)
        ib.setSpacing(8)

        self.action_input = QLineEdit()
        self.action_input.setPlaceholderText("Speak your intent…")
        self.action_input.returnPressed.connect(self._on_submit)

        self.proceed_btn = QPushButton("PROCEED")
        self.proceed_btn.setFixedWidth(100)
        self.proceed_btn.clicked.connect(self._on_submit)

        ib.addWidget(self.action_input)
        ib.addWidget(self.proceed_btn)

        lv.addWidget(title_bar)
        lv.addWidget(self.story, 1)
        lv.addWidget(input_bar)

        # ── Right column ──────────────────────────────────────────────────────
        self.char_panel = CharacterPanel()

        splitter.addWidget(left)
        splitter.addWidget(self.char_panel)
        splitter.setSizes([800, 220])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        h.addWidget(splitter)

    def start(self, generator, character: dict, opening: str, history: list):
        self.generator     = generator
        self.character     = character
        self.history       = history
        self.session_start = time.time()
        self.turn          = 0

        intro = f"*{character['name']} the {character['class']} steps forth…*\n\n{opening}"
        self.story.append_narrator(intro, animate=True)
        self._refresh()
        self.action_input.setFocus()

    def _tick_clock(self):
        self._refresh()

    def _refresh(self):
        elapsed = format_duration(time.time() - self.session_start)
        self.char_panel.refresh_character(self.character, self.turn, elapsed)
        self.turn_lbl.setText(f"Turn {self.turn}")

    def _on_submit(self):
        if self.story.is_animating():
            self.story.skip_animation()
            return

        action = self.action_input.text().strip()
        if not action or not self.generator:
            return

        self._last_action = action
        self.action_input.clear()
        self.proceed_btn.setEnabled(False)
        self.action_input.setEnabled(False)
        self.proceed_btn.setText("…")

        self.story.append_player(action)

        prompt = build_prompt(
            self.generator.tokenizer, self.history, action, self.character
        )
        kwargs = dict(
            max_new_tokens=240, do_sample=True, temperature=0.85, top_p=0.92,
            repetition_penalty=1.05,
            eos_token_id=self.generator.tokenizer.eos_token_id,
            pad_token_id=self.generator.tokenizer.eos_token_id,
            num_return_sequences=1, return_full_text=False,
        )
        self._inf_thread = InferenceThread(self.generator, prompt, kwargs)
        self._inf_thread.done.connect(self._on_response)
        self._inf_thread.error.connect(self._on_error)
        self._inf_thread.start()

    def _on_response(self, text: str):
        response = textwrap.fill(text, width=100)

        self.history.append({"role": "user",      "content": self._last_action})
        self.history.append({"role": "assistant",  "content": response})
        if len(self.history) > 8:
            self.history = self.history[-8:]

        self.turn += 1
        self.story.append_narrator(response)
        self._refresh()

        if self.turn % MEMORY_INTERVAL == 0:
            self._mem_thread = MemoryThread(self.generator, self.history)
            self._mem_thread.done.connect(
                lambda s: self.character.update({"memory": s})
            )
            self._mem_thread.start()

        self.proceed_btn.setText("PROCEED")
        self.proceed_btn.setEnabled(True)
        self.action_input.setEnabled(True)
        self.action_input.setFocus()

    def _on_error(self, msg: str):
        self.story.append_narrator(f"[An error occurred: {msg}]", animate=False)
        self.proceed_btn.setText("PROCEED")
        self.proceed_btn.setEnabled(True)
        self.action_input.setEnabled(True)


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):

    def __init__(self, model_dir: str):
        super().__init__()
        self.setWindowTitle("DnD Offline Pro")
        self.setMinimumSize(900, 600)
        self.resize(1100, 720)
        self.setStyleSheet(STYLESHEET)

        self.stack = QStackedWidget()
        self.setup = SetupPanel()
        self.game  = GamePanel()
        self.stack.addWidget(self.setup)
        self.stack.addWidget(self.game)
        self.setCentralWidget(self.stack)

        self.setup.begin.connect(self._start_game)

        self._generator = None
        self._loader = ModelLoader(model_dir)
        self._loader.loaded.connect(self._on_model_ready)
        self._loader.failed.connect(self.setup.mark_error)
        self._loader.start()

    def _on_model_ready(self, gen):
        self._generator = gen
        self.setup.mark_ready()

    def _start_game(self, character: dict, scenario: str):
        opening = SCENARIOS.get(scenario, SCENARIOS["dungeon"])
        history = [{"role": "assistant", "content": opening}]
        self.game.start(self._generator, character, opening, history)
        self.stack.setCurrentWidget(self.game)


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="DnD Offline Pro — Desktop GUI (PyQt6)")
    p.add_argument("--model",    default=None,
                   help="Path to local model dir (default: models/qwen2_5_0_5b_instruct)")
    p.add_argument("--scenario", default="dungeon",
                   help="dungeon (default), tavern, wilderness")
    return p.parse_args()


def main():
    args      = parse_args()
    app_dir   = os.path.dirname(os.path.abspath(__file__))
    model_dir = args.model or os.path.join(app_dir, "..", "models", "qwen2_5_0_5b_instruct")

    app = QApplication(sys.argv)
    app.setApplicationName("DnD Offline Pro")

    window = MainWindow(model_dir)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
