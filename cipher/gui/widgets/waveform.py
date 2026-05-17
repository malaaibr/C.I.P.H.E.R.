"""WaveformWidget — animated audio bar visualizer (PyQt6)."""

from __future__ import annotations

import random

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget, QSizePolicy


class WaveformWidget(QWidget):
    """16-bar animated waveform visualizer."""

    _REST = [4, 8, 6, 14, 5, 18, 7, 22, 6, 18, 8, 14, 5, 10, 6, 8]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._heights = self._REST[:]
        self._active = False
        self._color = QColor("#00c8ff")

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(120)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def set_color(self, color: str) -> None:
        self._color = QColor(color)

    def _tick(self) -> None:
        if self._active:
            self._heights = [random.randint(4, 30) for _ in range(16)]
        else:
            self._heights = self._REST[:]
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width() / len(self._heights)
        for i, h in enumerate(self._heights):
            x = i * w + w * 0.25
            bar = QRectF(x, self.height() - h, w * 0.5, float(h))
            p.fillRect(bar, self._color)
        p.end()
