"""Dev Asylum splash screen — animated hex, spinning rings, glitch title, typewriter."""

from __future__ import annotations

import math
import random

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QPoint, QRect, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QLinearGradient, QPainterPath,
)

from interfaces.gui.styles import palette

# ── Boot lines for typewriter ──────────────────────────────────────────────────
_BOOT_LINES = [
    "npm install soul --save",
    "git commit -m 'it works, idk why'",
    "sudo chmod 777 /dev/brain",
    "pip install caffeine --upgrade",
    "reticulating splines...",
    "while True: ship_it()",
    "rm -rf node_modules && pray",
    "undefined is not a function (but neither am I)",
    "TODO: fix this  //  estimated: never",
    "git push --force  # you only live once",
    "Stack Overflow: question closed as duplicate of itself",
]

_STATUS_BADGES = [
    ("git",      "OK",     "#4ade80"),
    ("caffeine", "94%",    "#f5a623"),
    ("sanity",   "null",   "#ff7b72"),
    ("prod",     "live 🔥","#ff7b72"),
]

_W, _H         = 860, 560
_TOTAL_TICKS   = 180  # × 50 ms = 9 000 ms runtime
_FADE_MS       = 700
_TICK_MS       = 50


class SplashScreen(QWidget):
    """Fully animated Dev Asylum splash — runs ~2.6 s then fades out."""

    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setFixedSize(_W, _H)
        self._center()

        # ── Animation state ────────────────────────────────────────────────────
        self._tick          = 0
        self._hex_phase     = 0.0
        self._ring_angles   = [0.0, 0.0, 0.0]

        self._particles: list[dict] = [
            {"orbit": 148, "angle": 0.0,   "speed":  0.045, "color": "#3ce8c8", "size": 5},
            {"orbit": 148, "angle": 2.094, "speed":  0.045, "color": "#5b8fff", "size": 4},
            {"orbit": 148, "angle": 4.189, "speed":  0.045, "color": "#a78bfa", "size": 4},
            {"orbit": 120, "angle": 1.0,   "speed": -0.070, "color": "#f5a623", "size": 3},
            {"orbit": 120, "angle": 4.5,   "speed": -0.055, "color": "#5b8fff", "size": 3},
            {"orbit": 95,  "angle": 3.5,   "speed":  0.090, "color": "#3ce8c8", "size": 3},
        ]

        self._glitch_countdown  = 28
        self._glitch_active     = False
        self._glitch_ticks      = 0
        self._glitch_offsets: tuple[int, int] = (3, 2)

        self._tw_line_idx  = 0
        self._tw_chars     = 0
        self._tw_pause     = 0
        self._tw_text      = ""

        self._progress     = 0
        self._prog_msg     = "Initializing Dev Asylum…"
        self._prog_warned  = False
        self._fade_anim    = None   # keep reference to prevent GC

        self._timer = QTimer(self)
        self._timer.setInterval(_TICK_MS)
        self._timer.timeout.connect(self._tick_anim)
        self._timer.start()

    def _center(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                sg.x() + (sg.width()  - _W) // 2,
                sg.y() + (sg.height() - _H) // 2,
            )

    # ── Tick ──────────────────────────────────────────────────────────────────

    def _tick_anim(self) -> None:
        self._tick += 1

        self._hex_phase     += 0.042
        self._ring_angles[0] += 0.026
        self._ring_angles[1] -= 0.019
        self._ring_angles[2] += 0.013

        for p in self._particles:
            p["angle"] += p["speed"]

        # Glitch logic
        if self._glitch_active:
            self._glitch_ticks += 1
            if self._glitch_ticks >= 5:
                self._glitch_active = False
                self._glitch_ticks  = 0
        else:
            self._glitch_countdown -= 1
            if self._glitch_countdown <= 0:
                self._glitch_active    = True
                self._glitch_offsets   = (random.randint(3, 6), random.randint(2, 4))
                self._glitch_countdown = random.randint(18, 38)

        # Typewriter logic
        if self._tw_pause > 0:
            self._tw_pause -= 1
        else:
            target = _BOOT_LINES[self._tw_line_idx]
            if self._tw_chars < len(target):
                self._tw_chars += 2
            else:
                self._tw_pause    = 100  # ~5 s hold — line stays readable
                self._tw_line_idx = (self._tw_line_idx + 1) % len(_BOOT_LINES)
                self._tw_chars    = 0
            self._tw_text = target[:self._tw_chars]

        # Progress logic
        if self._tick <= _TOTAL_TICKS:
            self._progress = int(self._tick / _TOTAL_TICKS * 100)
            if self._progress >= 48 and not self._prog_warned:
                self._prog_warned = True
                self._prog_msg    = "⚠ segfault in sanity.exe — continuing anyway"
            elif self._prog_warned and self._progress >= 58:
                self._prog_msg    = "Patching reality.exe…"
            if self._progress >= 88:
                self._prog_msg    = "Almost there… probably"
            if self._progress >= 100:
                self._timer.stop()
                self._start_fade()

        self.update()

    def _start_fade(self) -> None:
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(_FADE_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InQuad)
        anim.finished.connect(self._on_fade_done)
        anim.start()
        self._fade_anim = anim

    def _on_fade_done(self) -> None:
        self.close()
        self.finished.emit()

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Dark background
        painter.fillRect(0, 0, _W, _H, QColor(palette.BG_APP))

        # Subtle scanline grid
        painter.setPen(QPen(QColor(255, 255, 255, 5), 1))
        for y in range(0, _H, 18):
            painter.drawLine(0, y, _W, y)

        cx = _W // 2
        cy = 185 + int(9 * math.sin(self._hex_phase))

        self._draw_rings(painter, cx, cy)
        self._draw_particles(painter, cx, cy)
        self._draw_hex(painter, cx, cy, 58)
        self._draw_title(painter, cx, 375)
        self._draw_subtitle(painter, cx, 406)
        self._draw_typewriter(painter, cx, 441)
        self._draw_status_badges(painter, cx, 476)
        self._draw_progress(painter, cx, 506)

    # ── Draw helpers ──────────────────────────────────────────────────────────

    def _draw_hex(self, painter: QPainter, cx: int, cy: int, r: int) -> None:
        rot = self._hex_phase * 0.14

        # Glow halos
        painter.setPen(Qt.PenStyle.NoPen)
        for extra in (38, 26, 16, 8):
            alpha = max(0, 48 - extra * 2)
            painter.setBrush(QColor(60, 232, 200, alpha))
            self._fill_hex(painter, cx, cy, r + extra, rot)

        # Gradient body
        grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
        grad.setColorAt(0.0, QColor(60, 232, 200, 210))
        grad.setColorAt(1.0, QColor(91, 143, 255, 185))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor(60, 232, 200, 220), 2))
        self._fill_hex(painter, cx, cy, r, rot)

        # </> label via path for clean rendering
        font = QFont("Cascadia Code", 19)
        font.setBold(True)
        fm  = QFontMetrics(font)
        txt = "</>"
        tw  = fm.horizontalAdvance(txt)
        path = QPainterPath()
        path.addText(cx - tw // 2, cy + fm.ascent() // 2 - 1, font, txt)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def _fill_hex(self, painter: QPainter, cx: int, cy: int, r: int, rot: float) -> None:
        path = QPainterPath()
        for i in range(6):
            a = math.radians(60 * i) + rot
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_rings(self, painter: QPainter, cx: int, cy: int) -> None:
        cfgs = [
            (98,  self._ring_angles[0], QColor(60, 232, 200, 55),  QColor(60, 232, 200, 165), 1.5),
            (124, self._ring_angles[1], QColor(91, 143, 255, 45),  QColor(91, 143, 255, 145), 1.2),
            (152, self._ring_angles[2], QColor(167, 139, 250, 35), QColor(167, 139, 250, 120), 1.0),
        ]
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for r, angle, dim, bright, width in cfgs:
            rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
            painter.setPen(QPen(dim, width))
            painter.drawEllipse(rect)
            painter.setPen(QPen(bright, width + 1.2))
            painter.drawArc(rect, int(math.degrees(angle) * 16), int(72 * 16))

    def _draw_particles(self, painter: QPainter, cx: int, cy: int) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self._particles:
            px = cx + int(p["orbit"] * math.cos(p["angle"]))
            py = cy + int(p["orbit"] * math.sin(p["angle"]))
            core = QColor(p["color"])
            glow = QColor(p["color"])
            glow.setAlpha(55)
            painter.setBrush(glow)
            painter.drawEllipse(QPoint(px, py), p["size"] + 4, p["size"] + 4)
            core.setAlpha(230)
            painter.setBrush(core)
            painter.drawEllipse(QPoint(px, py), p["size"], p["size"])

    def _draw_title(self, painter: QPainter, cx: int, y: int) -> None:
        text = "Dev Asylum"
        font = QFont("Cascadia Code", 40)
        font.setBold(True)
        fm   = QFontMetrics(font)
        tw   = fm.horizontalAdvance(text)
        x    = cx - tw // 2

        if self._glitch_active:
            ox, oy = self._glitch_offsets
            painter.setPen(QColor(255, 30, 30, 110))
            painter.setFont(font)
            painter.drawText(x + ox, y, text)
            painter.setPen(QColor(30, 30, 255, 95))
            painter.drawText(x - ox, y, text)
            painter.setPen(QColor(30, 220, 30, 75))
            painter.drawText(x, y - oy, text)

        # Gradient path text
        grad = QLinearGradient(x, y - fm.ascent(), x + tw, y)
        grad.setColorAt(0.0, QColor(palette.ACCENT))
        grad.setColorAt(1.0, QColor("#5b8fff"))
        path = QPainterPath()
        path.addText(x, y, font, text)
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

    def _draw_subtitle(self, painter: QPainter, cx: int, y: int) -> None:
        text = "where bugs are a lifestyle"
        font = QFont("Cascadia Code", 11)
        font.setItalic(True)
        fm   = QFontMetrics(font)
        tw   = fm.horizontalAdvance(text)
        painter.setFont(font)
        painter.setPen(QColor(palette.TEXT3))
        painter.drawText(cx - tw // 2, y, text)

    def _draw_typewriter(self, painter: QPainter, cx: int, y: int) -> None:
        blink = "█" if (self._tick % 14) < 8 else " "
        full  = f"> {self._tw_text}{blink}"
        font  = QFont("Cascadia Code", 11)
        fm    = QFontMetrics(font)
        tw    = fm.horizontalAdvance(full)
        painter.setFont(font)
        painter.setPen(QColor(palette.ACCENT))
        painter.drawText(cx - tw // 2, y, full)

    def _draw_status_badges(self, painter: QPainter, cx: int, y: int) -> None:
        font = QFont("Cascadia Code", 9)
        painter.setFont(font)
        fm = QFontMetrics(font)
        gap = 10
        badges = [(f"  {k}: {v}  ", c) for k, v, c in _STATUS_BADGES]
        total  = sum(fm.horizontalAdvance(t) + gap for t, _ in badges) - gap
        x = cx - total // 2

        for text, hex_col in badges:
            tw  = fm.horizontalAdvance(text)
            col = QColor(hex_col)
            bg  = QColor(hex_col)
            bg.setAlpha(22)
            rect = QRect(x, y - fm.ascent() - 4, tw + 2, fm.height() + 8)
            painter.setBrush(bg)
            painter.setPen(QPen(col, 1))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(col)
            painter.drawText(x + 1, y, text)
            x += tw + gap

    def _draw_progress(self, painter: QPainter, cx: int, y: int) -> None:
        bw, bh = 520, 4
        bx = cx - bw // 2

        # Track
        painter.setBrush(QColor(palette.BG_CARD))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRect(bx, y, bw, bh), 2, 2)

        # Fill gradient
        fw = int(bw * self._progress / 100)
        if fw > 0:
            grad = QLinearGradient(bx, 0, bx + bw, 0)
            grad.setColorAt(0.0, QColor(palette.ACCENT))
            grad.setColorAt(1.0, QColor("#5b8fff"))
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRect(bx, y, fw, bh), 2, 2)

        # Label
        font = QFont("Cascadia Code", 9)
        painter.setFont(font)
        fm    = QFontMetrics(font)
        label = f"{self._progress}%   {self._prog_msg}"
        lw    = fm.horizontalAdvance(label)
        painter.setPen(QColor(palette.TEXT3))
        painter.drawText(cx - lw // 2, y + bh + 19, label)
