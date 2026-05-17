"""JARVIS Blue HUD Theme — PyQt6 global stylesheet."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication

COLORS = {
    "bg_primary":    "#010a15",
    "bg_panel":      "#041624",
    "bg_input":      "#020d1a",
    "bg_hover":      "#042030",
    "accent_blue":   "#00c8ff",
    "accent_cyan":   "#00ffe5",
    "accent_teal":   "#00bfaa",
    "success":       "#00ff9d",
    "warning":       "#ffb700",
    "danger":        "#ff3a3a",
    "text_primary":  "#b8e8ff",
    "text_muted":    "#2d5f7a",
    "text_dim":      "#1a3a50",
    "border":        "rgba(0,200,255,0.18)",
    "border_active": "rgba(0,200,255,0.55)",
}

JARVIS_QSS = """
/* ═══ BASE ═══ */
QMainWindow, QWidget {
    background-color: #010a15;
    color: #b8e8ff;
    font-family: 'Segoe UI', 'Exo 2', sans-serif;
    font-size: 10pt;
}

/* ═══ SCROLLBAR ═══ */
QScrollBar:vertical {
    background: #020d1a;
    width: 8px;
    border: none;
}
QScrollBar::handle:vertical {
    background: rgba(0,200,255,0.25);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #020d1a;
    height: 8px;
    border: none;
}
QScrollBar::handle:horizontal {
    background: rgba(0,200,255,0.25);
    border-radius: 4px;
    min-width: 30px;
}

/* ═══ BUTTONS ═══ */
QPushButton {
    background-color: rgba(0,50,100,0.25);
    border: 1px solid #1a5a8a;
    color: #00c8ff;
    padding: 6px 12px;
    font-size: 9pt;
    letter-spacing: 1px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: rgba(0,200,255,0.12);
    border-color: #00c8ff;
}
QPushButton:pressed {
    background-color: rgba(0,200,255,0.2);
}

/* ═══ INPUT ═══ */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #020d1a;
    border: 1px solid rgba(0,200,255,0.18);
    color: #b8e8ff;
    padding: 4px 8px;
    border-radius: 3px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: rgba(0,200,255,0.55);
}

/* ═══ LIST WIDGET ═══ */
QListWidget {
    background: transparent;
    border: none;
    color: #2d5f7a;
    font-size: 10pt;
}
QListWidget::item {
    padding: 6px 8px;
}
QListWidget::item:selected {
    color: #00c8ff;
    background: rgba(0,200,255,0.12);
}
QListWidget::item:hover {
    color: #b8e8ff;
    background: rgba(0,200,255,0.06);
}

/* ═══ PROGRESS BAR ═══ */
QProgressBar {
    background: #020d1a;
    border: 1px solid rgba(0,200,255,0.2);
    height: 6px;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk {
    background: #00c8ff;
    border-radius: 3px;
}

/* ═══ TAB WIDGET ═══ */
QTabWidget::pane {
    border: 1px solid rgba(0,200,255,0.18);
    background: #010a15;
}
QTabBar::tab {
    background: #041624;
    color: #2d5f7a;
    padding: 6px 16px;
    border: 1px solid rgba(0,200,255,0.12);
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #00c8ff;
    background: rgba(0,200,255,0.08);
    border-bottom: 2px solid #00c8ff;
}

/* ═══ FRAME ═══ */
QFrame[frameShape="4"] { /* HLine */
    color: rgba(0,200,255,0.18);
}

/* ═══ STATUS BAR ═══ */
QStatusBar {
    background: rgba(1,8,22,0.97);
    border-top: 1px solid rgba(0,200,255,0.18);
    color: #2d5f7a;
    font-size: 9pt;
}
"""


def apply_theme(app: QApplication) -> None:
    """Apply the JARVIS Blue HUD theme to the application."""
    app.setStyleSheet(JARVIS_QSS)
