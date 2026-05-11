"""DevNex hex-logo pixmap renderer — shared by window icon and ICO generator."""

from __future__ import annotations

import math

from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush,
    QFont, QFontMetrics, QLinearGradient, QPainterPath,
)
from PyQt6.QtCore import Qt


def make_hex_pixmap(size: int) -> QPixmap:
    """
    Render the DevNex </> hex logo at [size × size] pixels.
    Background is transparent — suitable for window icons and taskbar.

    Sizes < 28 px omit the text label (not legible at that scale).
    """
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))

    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    cx = cy = size // 2
    r  = max(4, int(size * 0.40))
    stroke = max(1, size // 40)

    # Dark rounded background so the icon reads on any color taskbar
    p.setPen(Qt.PenStyle.NoPen)
    pad = max(2, int(r * 0.18))
    p.setBrush(QColor(11, 14, 19, 220))
    p.drawRoundedRect(0, 0, size, size, size * 0.18, size * 0.18)

    # Glow halos
    for frac in (0.30, 0.18, 0.09):
        extra = max(1, int(r * frac))
        alpha = max(0, 55 - int(frac * 160))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(60, 232, 200, alpha))
        _hex_path(p, cx, cy, r + extra)

    # Gradient body
    grad = QLinearGradient(cx - r, cy - r, cx + r, cy + r)
    grad.setColorAt(0.0, QColor(60, 232, 200, 218))
    grad.setColorAt(1.0, QColor(91, 143, 255, 192))
    p.setBrush(QBrush(grad))
    p.setPen(QPen(QColor(60, 232, 200, 200), stroke))
    _hex_path(p, cx, cy, r)

    # </> label — only when pixels allow it to be legible
    if size >= 28:
        fs   = max(6, int(size * 0.20))
        font = QFont("Cascadia Code", fs)
        font.setBold(True)
        fm   = QFontMetrics(font)
        txt  = "</>"
        tw   = fm.horizontalAdvance(txt)
        path = QPainterPath()
        path.addText(cx - tw // 2, cy + fm.ascent() // 2 - 1, font, txt)
        p.setBrush(QColor(255, 255, 255, 242))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

    p.end()
    return pix


def _hex_path(painter: QPainter, cx: int, cy: int, r: int, rot: float = 0.0) -> None:
    path = QPainterPath()
    for i in range(6):
        a = math.radians(60 * i) + rot
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    path.closeSubpath()
    painter.drawPath(path)
