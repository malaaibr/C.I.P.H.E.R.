"""TraceNodeCard — QGraphicsObject rendered as a HUD-style node card."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsObject,
    QStyleOptionGraphicsItem,
    QWidget,
)

from core.trace_model import NodeKind

# Card geometry
CARD_W = 180
CARD_H = 56

_KIND_ACCENT: dict[NodeKind, str] = {
    NodeKind.HLD:  "#00c8ff",
    NodeKind.LLD:  "#00ff9d",
    NodeKind.CODE: "#ffb700",
    NodeKind.TEST: "#8b5cf6",
    NodeKind.UTD:  "#ff3a8a",
}

_BG_COLOR    = QColor("#041624")
_MUTED_COLOR = QColor("#2d5f7a")


class TraceNodeCard(QGraphicsObject):
    """
    Custom-painted 180×56 px node card for the Trace Graph canvas.

    Signals:
        node_clicked(str)        — emitted on left single-click
        node_double_clicked(str) — emitted on left double-click (→ open source)
    """

    node_clicked        = pyqtSignal(str)
    node_double_clicked = pyqtSignal(str)

    def __init__(
        self,
        node_id:  str,
        kind:     NodeKind,
        label:    str,
        sublabel: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._node_id  = node_id
        self._kind     = kind
        self._label    = label
        self._sublabel = sublabel

        self._hovered  = False
        self._selected = False
        self._dimmed   = False

        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setToolTip(node_id)

        self._shadow = QGraphicsDropShadowEffect()
        self._shadow.setOffset(0, 0)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(QColor(_KIND_ACCENT[kind]))
        self.setGraphicsEffect(self._shadow)

    # ── QGraphicsItem protocol ────────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, CARD_W, CARD_H)

    def paint(
        self,
        painter: QPainter,
        option:  QStyleOptionGraphicsItem,
        widget:  Optional[QWidget] = None,
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        accent = QColor(_KIND_ACCENT[self._kind])
        painter.setOpacity(0.18 if self._dimmed else 1.0)

        # Background fill
        card_rect = QRectF(0, 0, CARD_W, CARD_H)
        path = QPainterPath()
        path.addRoundedRect(card_rect, 4, 4)
        painter.fillPath(path, _BG_COLOR)
        overlay = QColor(accent)
        overlay.setAlphaF(0.04)
        painter.fillPath(path, overlay)

        # Border
        border_w = 2.0 if self._selected else 1.0
        border_a = 1.0 if (self._hovered or self._selected) else 0.55
        pen_col  = QColor(accent)
        pen_col.setAlphaF(border_a)
        pen = QPen(pen_col, border_w)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        # Sublabel — top line, muted
        font_sub = QFont("monospace")
        font_sub.setPointSizeF(7.0)
        painter.setFont(font_sub)
        painter.setPen(_MUTED_COLOR)
        painter.drawText(
            QRectF(8, 5, CARD_W - 16, 18),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._sublabel,
        )

        # Label — main line, accent color, bold
        font_lbl = QFont("monospace")
        font_lbl.setPointSizeF(9.0)
        font_lbl.setBold(True)
        painter.setFont(font_lbl)
        lbl_col = QColor(accent)
        lbl_col.setAlphaF(0.18 if self._dimmed else 1.0)
        painter.setPen(lbl_col)
        painter.drawText(
            QRectF(8, 26, CARD_W - 16, 24),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._label,
        )

    # ── Hover / click events ──────────────────────────────────────────────────

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self._shadow.setBlurRadius(14)
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self._shadow.setBlurRadius(18 if self._selected else 0)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.node_clicked.emit(self._node_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.node_double_clicked.emit(self._node_id)
        super().mouseDoubleClickEvent(event)

    # ── State setters (driven by canvas) ─────────────────────────────────────

    def set_selected(self, selected: bool) -> None:
        """Toggle selection highlight + glow."""
        self._selected = selected
        self._shadow.setBlurRadius(18 if selected else (14 if self._hovered else 0))
        self.update()

    def set_dimmed(self, dimmed: bool) -> None:
        """Dim the card (filter excludes this kind)."""
        self._dimmed = dimmed
        self.update()

    # ── Anchor points used by edge routing ───────────────────────────────────

    def right_anchor(self) -> QPointF:
        p = self.pos()
        return QPointF(p.x() + CARD_W, p.y() + CARD_H / 2)

    def left_anchor(self) -> QPointF:
        p = self.pos()
        return QPointF(p.x(), p.y() + CARD_H / 2)

    # ── Properties ───────────────────────────────────────────────────────────

    @property
    def node_id(self) -> str:
        return self._node_id

    @property
    def kind(self) -> NodeKind:
        return self._kind
