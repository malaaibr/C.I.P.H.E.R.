"""CIPHER Splash Screen — animated boot sequence (PyQt6, based on DevNex splash)."""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRectF, QPointF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient, QPainterPath,
)
from PyQt6.QtWidgets import QWidget, QApplication

_W, _H = 860, 560
_TOTAL_TICKS = 120
_FADE_MS = 700
_TICK_MS = 50

_ACCENT = "#00c8ff"
_GREEN = "#00ff9d"
_MUTED = "#2d5f7a"
_CYAN = "#00ffe5"
_WARN = "#ffb700"

_BOOT_LINES = [
    "[ INIT ] Reactor core — stable",
    "[ BOOT ] Loading LLM Gateway...",
    "[ OK   ] Ollama backend online",
    "[ BOOT ] Connecting A2A Server...",
    "[ OK   ] A2A Server :8100 ready",
    "[ BOOT ] Mounting infrastructure...",
    "[ OK   ] Redis / Memgraph / Qdrant / MinIO / NATS / OPA",
    "[ BOOT ] Initializing voice pipeline...",
    "[ OK   ] Voice engine ready",
    "[ BOOT ] Loading V-Cycle skill registry...",
    "[ OK   ] DevNex orchestrator online",
    "[ OK   ] All subsystems nominal — C.I.P.H.E.R ONLINE",
]


class SplashScreen(QWidget):
    """Animated CIPHER boot splash — runs ~6s then fades out."""

    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(_W, _H)
        self._center_on_screen()

        self._tick = 0
        self._particles: list[dict] = []
        self._ring_angle = 0.0
        self._log_index = 0
        self._log_lines: list[tuple[str, str]] = []
        self._fade_opacity = 1.0
        self._fading = False

        self._init_particles()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(_TICK_MS)

        self._log_timer = QTimer(self)
        self._log_timer.timeout.connect(self._next_log)
        self._log_timer.start(420)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - _W) // 2 + geo.x()
            y = (geo.height() - _H) // 2 + geo.y()
            self.move(x, y)

    def _init_particles(self) -> None:
        for _ in range(40):
            self._particles.append({
                "x": random.uniform(0, _W),
                "y": random.uniform(0, _H),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.3, 0.3),
                "r": random.uniform(0.5, 2.0),
                "a": random.uniform(0.1, 0.5),
            })

    def _step(self) -> None:
        self._tick += 1
        self._ring_angle += 1.5
        for pt in self._particles:
            pt["x"] = (pt["x"] + pt["vx"]) % _W
            pt["y"] = (pt["y"] + pt["vy"]) % _H
        self.update()

        if self._tick >= _TOTAL_TICKS and not self._fading:
            self._start_fade()

    def _next_log(self) -> None:
        if self._log_index < len(_BOOT_LINES):
            line = _BOOT_LINES[self._log_index]
            color = _GREEN if "OK" in line else (_WARN if "WARN" in line else _ACCENT)
            self._log_lines.append((line, color))
            self._log_index += 1
        else:
            self._log_timer.stop()

    def _start_fade(self) -> None:
        self._fading = True
        self._fade_timer = QTimer(self)
        self._fade_step = 0
        self._fade_timer.timeout.connect(self._fade_tick)
        self._fade_timer.start(30)

    def _fade_tick(self) -> None:
        self._fade_step += 1
        self._fade_opacity = max(0, 1.0 - self._fade_step / 25)
        self.update()
        if self._fade_opacity <= 0:
            self._fade_timer.stop()
            self._timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._fade_opacity)

        # Background
        p.fillRect(0, 0, _W, _H, QColor(1, 10, 21))

        cx, cy = _W / 2, _H / 2

        # Particles
        p.setPen(Qt.PenStyle.NoPen)
        for pt in self._particles:
            col = QColor(0, 200, 255, int(pt["a"] * 255))
            p.setBrush(QBrush(col))
            p.drawEllipse(QPointF(pt["x"], pt["y"]), pt["r"], pt["r"])

        # Rotating ring
        pen = QPen(QColor(0, 200, 255, 40), 1.5, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(cx, cy)
        p.rotate(self._ring_angle)
        p.drawEllipse(QPointF(0, 0), 180, 180)
        p.restore()

        pen2 = QPen(QColor(0, 255, 229, 30), 1, Qt.PenStyle.DashLine)
        p.setPen(pen2)
        p.save()
        p.translate(cx, cy)
        p.rotate(-self._ring_angle * 0.7)
        p.drawEllipse(QPointF(0, 0), 220, 220)
        p.restore()

        # Title
        p.setPen(QColor(_ACCENT))
        font = QFont("Segoe UI", 24, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
        p.setFont(font)
        p.drawText(QRectF(0, 80, _W, 50), Qt.AlignmentFlag.AlignCenter, "C . I . P . H . E . R")

        # Subtitle
        p.setPen(QColor(_MUTED))
        sub_font = QFont("Segoe UI", 9)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        p.setFont(sub_font)
        p.drawText(QRectF(0, 125, _W, 30), Qt.AlignmentFlag.AlignCenter,
                   "V-CYCLE INTELLIGENCE PLATFORM")

        # Boot log
        log_font = QFont("Cascadia Code", 9)
        p.setFont(log_font)
        y_start = 200
        visible = self._log_lines[-10:]
        for i, (line, color) in enumerate(visible):
            p.setPen(QColor(color))
            p.drawText(QRectF(180, y_start + i * 22, 500, 20),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, line)

        # Progress
        pct = min(100, int(self._tick / _TOTAL_TICKS * 100))
        bar_y = _H - 60
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 50, 80))
        p.drawRoundedRect(QRectF(200, bar_y, 460, 4), 2, 2)
        p.setBrush(QColor(_ACCENT))
        p.drawRoundedRect(QRectF(200, bar_y, 460 * pct / 100, 4), 2, 2)

        # Percentage
        p.setPen(QColor(_MUTED))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(QRectF(200, bar_y + 8, 460, 20), Qt.AlignmentFlag.AlignRight, f"{pct}%")

        p.end()
