"""QPainter-based horizontal V-cycle step progress indicator — adapted from Int_Agent."""

from __future__ import annotations

import math
from enum import Enum
from typing import Callable

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QFontMetrics

from interfaces.gui.constants import STEP_LABELS
from interfaces.gui.styles import palette


class StepState(Enum):
    PENDING  = "pending"
    ACTIVE   = "active"
    COMPLETE = "complete"
    ERROR    = "error"


_STATE_FILL: dict[StepState, str] = {
    StepState.PENDING:  palette.BG_INPUT,
    StepState.ACTIVE:   palette.STEP_ACTIVE,
    StepState.COMPLETE: palette.STEP_DONE,
    StepState.ERROR:    palette.STEP_ERR,
}

_STATE_TEXT: dict[StepState, str] = {
    StepState.PENDING:  palette.TEXT3,
    StepState.ACTIVE:   palette.TEXT1,
    StepState.COMPLETE: palette.TEXT1,
    StepState.ERROR:    palette.TEXT1,
}

_PULSE_MS   = 50
_PULSE_STEP = 0.05


class StepIndicator(QWidget):
    """72-px tall V-cycle step indicator with pulsing active node, QPainter drawn."""

    step_clicked = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._states: list[StepState] = [StepState.PENDING] * len(STEP_LABELS)
        self._pulse_phase: float = 0.0
        self._on_step_click: Callable[[int], None] | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(_PULSE_MS)
        self._timer.timeout.connect(self._tick_pulse)
        self._timer.start()

    def update_step(self, idx: int, state: StepState) -> None:
        if 0 <= idx < len(self._states):
            self._states[idx] = state
            self.update()

    def set_step_state(self, step_index: int, state: StepState) -> None:
        self.update_step(step_index, state)

    def set_active_step(self, step_index: int) -> None:
        for i in range(len(self._states)):
            if i < step_index:
                self._states[i] = StepState.COMPLETE
            elif i == step_index:
                self._states[i] = StepState.ACTIVE
            else:
                self._states[i] = StepState.PENDING
        self.update()

    def reset_all(self) -> None:
        self._states = [StepState.PENDING] * len(STEP_LABELS)
        self.update()

    def set_on_click(self, callback: Callable[[int], None]) -> None:
        self._on_step_click = callback
        self.step_clicked.connect(callback)

    def _tick_pulse(self) -> None:
        if any(s is StepState.ACTIVE for s in self._states):
            self._pulse_phase = (self._pulse_phase + _PULSE_STEP) % (2 * math.pi)
            self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(palette.BG_APP))

        n = len(STEP_LABELS)
        if n == 0:
            return

        pad      = 28
        r        = 10
        y_circle = 24
        y_label  = 52
        spacing  = max(1, (w - 2 * pad) / max(1, n - 1))
        centers  = [pad + spacing * i for i in range(n)]

        pen = QPen(QColor(palette.BORDER), 2)
        painter.setPen(pen)
        for i in range(n - 1):
            painter.drawLine(int(centers[i]), y_circle, int(centers[i + 1]), y_circle)

        small_font = QFont()
        small_font.setPointSize(7)
        label_font = QFont()
        label_font.setPointSize(6)

        for i, cx in enumerate(centers):
            cx_i  = int(cx)
            state = self._states[i]

            if state is StepState.ACTIVE:
                alpha = int(60 + 60 * math.sin(self._pulse_phase))
                glow  = QColor(palette.STEP_ACTIVE)
                glow.setAlpha(alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(QPoint(cx_i, y_circle), r + 6, r + 6)

            fill_color = QColor(_STATE_FILL[state])
            if state is StepState.PENDING:
                painter.setPen(QPen(QColor(palette.BORDER), 2))
                painter.setBrush(QColor(palette.BG_APP))
            else:
                painter.setPen(QPen(fill_color, 2))
                painter.setBrush(fill_color)
            painter.drawEllipse(QPoint(cx_i, y_circle), r, r)

            painter.setPen(QColor(_STATE_TEXT[state]))
            small_font.setBold(state in (StepState.ACTIVE, StepState.COMPLETE))
            painter.setFont(small_font)
            marker = "✓" if state is StepState.COMPLETE else ("✗" if state is StepState.ERROR else str(i + 1))
            fm = QFontMetrics(small_font)
            painter.drawText(cx_i - fm.horizontalAdvance(marker) // 2, y_circle + fm.ascent() // 2 - 1, marker)

            label = STEP_LABELS[i]
            painter.setFont(label_font)
            painter.setPen(QColor(_STATE_TEXT[state]))
            painter.drawText(
                QRect(cx_i - 40, y_label - 10, 80, 22),
                Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                label,
            )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        idx = self._find_step_at(event.pos().x())
        if idx is not None and self._states[idx] is StepState.COMPLETE:
            self.step_clicked.emit(idx)
            if self._on_step_click is not None:
                self._on_step_click(idx)

    def _find_step_at(self, x: float) -> int | None:
        n = len(STEP_LABELS)
        if n == 0:
            return None
        pad     = 28
        spacing = max(1, (self.width() - 2 * pad) / max(1, n - 1))
        centers = [pad + spacing * i for i in range(n)]
        nearest = min(range(n), key=lambda i: abs(centers[i] - x))
        return nearest if abs(centers[nearest] - x) <= 18 else None
