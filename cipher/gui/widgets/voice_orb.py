"""VoiceOrbWidget — pulsing orb for voice state indication (PyQt6)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget


class VoiceOrbWidget(QWidget):
    """Animated concentric pulse orb indicating voice state."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pulse = 0
        self._listening = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)

    def set_listening(self, value: bool) -> None:
        self._listening = value
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 1) % 20
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        center = QPointF(rect.center())
        base_color = QColor("#00ffe5" if self._listening else "#00c8ff")
        pen = QPen(base_color, 2)
        p.setPen(pen)
        r = rect.width() * 0.35
        p.drawEllipse(center, r, r)
        pulse_r = r + (self._pulse if self._listening else 0)
        pen2 = QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 80), 1)
        p.setPen(pen2)
        p.drawEllipse(center, pulse_r, pulse_r)
        p.end()
