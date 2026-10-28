from __future__ import annotations


LIGHT_THEME = """
QMainWindow, QDialog { background: #f5f7fb; color: #1d2433; }
QWidget { font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 13px; color: #1d2433; }
QFrame#sidebar { background: #ffffff; border: 1px solid #e5e9f0; border-radius: 16px; }
QFrame#topbar, QFrame#content { background: transparent; }
QLabel#brand { font-size: 22px; font-weight: 700; color: #172033; }
QLabel#subtitle, QLabel#muted { color: #7b8495; }
QLineEdit#search { background: #ffffff; border: 1px solid #e1e6ef; border-radius: 12px; padding: 10px 14px; min-height: 20px; }
QLineEdit#search:focus { border: 1px solid #6b7cff; }
QPushButton { border: none; border-radius: 9px; padding: 9px 14px; background: #e9edf5; }
QPushButton:hover { background: #dfe5f1; }
QPushButton#primary { background: #536dfe; color: #ffffff; font-weight: 600; }
QPushButton#primary:hover { background: #4059e8; }
QPushButton#quiet { background: transparent; color: #657086; }
QPushButton#quiet:hover { background: #edf0f6; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget#categories::item { padding: 10px 12px; margin: 2px 0; border-radius: 9px; color: #667085; }
QListWidget#categories::item:selected { background: #e8ecff; color: #4059e8; font-weight: 600; }
QListWidget#items { background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #cbd2df; border-radius: 4px; min-height: 40px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; }
QFrame#item_card { background: #ffffff; border: 1px solid #e5e9f0; border-radius: 14px; }
QFrame#item_card:hover { border: 1px solid #abb7ff; background: #fbfcff; }
QLabel#item_name { font-weight: 600; color: #222b3f; }
QLabel#item_path { color: #8a93a3; font-size: 11px; }
QToolButton { border: none; background: transparent; color: #a2aabb; padding: 2px; }
QToolButton:hover { color: #536dfe; background: #edf0ff; border-radius: 6px; }
QStatusBar { color: #7b8495; background: transparent; }
QComboBox, QSpinBox { border: 1px solid #dfe4ed; border-radius: 8px; padding: 7px; background: #ffffff; }
QCheckBox { spacing: 8px; }
"""


DARK_THEME = """
QMainWindow, QDialog { background: #161a23; color: #edf1f7; }
QWidget { font-family: 'Microsoft YaHei UI', 'Segoe UI'; font-size: 13px; color: #edf1f7; }
QFrame#sidebar { background: #1d222d; border: 1px solid #2a3140; border-radius: 16px; }
QFrame#topbar, QFrame#content { background: transparent; }
QLabel#brand { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#subtitle, QLabel#muted { color: #8e98aa; }
QLineEdit#search { background: #202633; border: 1px solid #30394a; border-radius: 12px; padding: 10px 14px; min-height: 20px; color: #f2f4f8; }
QLineEdit#search:focus { border: 1px solid #7181ff; }
QPushButton { border: none; border-radius: 9px; padding: 9px 14px; background: #2c3443; color: #e9edf5; }
QPushButton:hover { background: #364154; }
QPushButton#primary { background: #6174ff; color: #ffffff; font-weight: 600; }
QPushButton#primary:hover { background: #7181ff; }
QPushButton#quiet { background: transparent; color: #9ba5b7; }
QPushButton#quiet:hover { background: #272e3c; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget#categories::item { padding: 10px 12px; margin: 2px 0; border-radius: 9px; color: #a3acbc; }
QListWidget#categories::item:selected { background: #2d3762; color: #aeb8ff; font-weight: 600; }
QListWidget#items { background: transparent; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #3b4557; border-radius: 4px; min-height: 40px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; }
QFrame#item_card { background: #202633; border: 1px solid #2d3748; border-radius: 14px; }
QFrame#item_card:hover { border: 1px solid #7181ff; background: #242c3b; }
QLabel#item_name { font-weight: 600; color: #f1f4f9; }
QLabel#item_path { color: #8e98aa; font-size: 11px; }
QToolButton { border: none; background: transparent; color: #7e899c; padding: 2px; }
QToolButton:hover { color: #aeb8ff; background: #2d3762; border-radius: 6px; }
QStatusBar { color: #8e98aa; background: transparent; }
QComboBox, QSpinBox { border: 1px solid #30394a; border-radius: 8px; padding: 7px; background: #202633; color: #eef1f7; }
QCheckBox { spacing: 8px; }
"""


def stylesheet(dark: bool) -> str:
    return DARK_THEME if dark else LIGHT_THEME

