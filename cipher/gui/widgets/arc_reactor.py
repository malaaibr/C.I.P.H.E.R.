"""ArcReactorWidget — animated Iron-Man style reactor orb (PyQt6 port)."""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient
from PyQt6.QtWidgets import QWidget


class ArcReactorWidget(QWidget):
    """Circular reactor with rotating rings and state-dependent color."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

    _STATE_COLORS = {
        IDLE:       (QColor(0, 200, 255), QColor(0, 100, 180)),
        LISTENING:  (QColor(0, 255, 229), QColor(0, 180, 160)),
        PROCESSING: (QColor(139, 92, 246), QColor(80, 40, 180)),
        SPEAKING:   (QColor(0, 255, 157), QColor(0, 160, 100)),
    }

    def __init__(self, size: int = 80, parent=None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._state = self.IDLE
        self._angle = 0.0
        self._pulse = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 2.0) % 360
        self._pulse += 0.08
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self._size / 2, self._size / 2
        outer, inner = self._STATE_COLORS.get(self._state, self._STATE_COLORS[self.IDLE])

        # Glow
        pulse_factor = 0.5 + 0.5 * math.sin(self._pulse)
        glow_r = self._size * 0.42 + pulse_factor * 4
        grad = QRadialGradient(QPointF(cx, cy), glow_r)
        grad.setColorAt(0, QColor(outer.red(), outer.green(), outer.blue(), 60))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # Outer ring
        pen = QPen(QColor(outer.red(), outer.green(), outer.blue(), 180), 2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r_outer = self._size * 0.38
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # Rotating ticks
        tick_pen = QPen(QColor(outer.red(), outer.green(), outer.blue(), 140), 1.5)
        p.setPen(tick_pen)
        for i in range(12):
            angle_rad = math.radians(self._angle + i * 30)
            r1 = self._size * 0.28
            r2 = self._size * 0.34
            x1 = cx + r1 * math.cos(angle_rad)
            y1 = cy + r1 * math.sin(angle_rad)
            x2 = cx + r2 * math.cos(angle_rad)
            y2 = cy + r2 * math.sin(angle_rad)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Inner core
        core_r = self._size * 0.15
        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        core_grad.setColorAt(0, QColor(outer.red(), outer.green(), outer.blue(), 200))
        core_grad.setColorAt(0.7, QColor(inner.red(), inner.green(), inner.blue(), 120))
        core_grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(core_grad))
        p.drawEllipse(QPointF(cx, cy), core_r, core_r)

        p.end()
