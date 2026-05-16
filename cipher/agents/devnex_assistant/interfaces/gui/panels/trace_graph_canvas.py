"""TraceGraphCanvas — QGraphicsView diagram surface for the V-cycle trace graph.

Layout: 5 columns (HLD / LLD / CODE / TEST / UTD) at fixed X positions.
Edges are cubic Bezier curves coloured by the source node's accent colour.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QPushButton,
)

from core.trace_model import NodeKind, TraceGraph
from interfaces.gui.panels.trace_node_card import CARD_H, CARD_W, TraceNodeCard

log = logging.getLogger(__name__)

# ── Visual tokens ─────────────────────────────────────────────────────────────

_BG_COLOR = QColor("#010a15")

_KIND_ACCENT: dict[NodeKind, str] = {
    NodeKind.HLD:  "#00c8ff",
    NodeKind.LLD:  "#00ff9d",
    NodeKind.CODE: "#ffb700",
    NodeKind.TEST: "#8b5cf6",
    NodeKind.UTD:  "#ff3a8a",
}

_COLUMN_LABELS: dict[NodeKind, str] = {
    NodeKind.HLD:  "HLD",
    NodeKind.LLD:  "LLD",
    NodeKind.CODE: "CODE",
    NodeKind.TEST: "TESTS",
    NodeKind.UTD:  "UTD",
}

# ── Layout constants ──────────────────────────────────────────────────────────

COLUMN_ORDER:    list[NodeKind] = [NodeKind.HLD, NodeKind.LLD, NodeKind.CODE, NodeKind.TEST, NodeKind.UTD]
COLUMN_GAP:      int            = 280          # px between column left edges
COLUMN_X_START:  int            = 80
NODE_VERT_GAP:   int            = 24           # px between node cards vertically
HEADER_Y:        int            = 24
NODES_START_Y:   int            = 64

_COLUMN_X: dict[NodeKind, int] = {
    kind: COLUMN_X_START + i * COLUMN_GAP
    for i, kind in enumerate(COLUMN_ORDER)
}

# Bezier control-point horizontal offset = 50 % of column gap
_CTRL_OFFSET = COLUMN_GAP * 0.5

ZOOM_MIN = 0.4
ZOOM_MAX = 2.5


# ── Edge item ─────────────────────────────────────────────────────────────────

class _EdgeItem(QGraphicsPathItem):
    """Cubic Bezier edge between two TraceNodeCard items."""

    def __init__(
        self,
        src_card:   TraceNodeCard,
        dst_card:   TraceNodeCard,
        edge_kind:  str   = "link",
        confidence: float = 1.0,
    ) -> None:
        super().__init__()
        self._src        = src_card
        self._dst        = dst_card
        self._edge_kind  = edge_kind
        self._confidence = confidence

        accent = QColor(_KIND_ACCENT.get(src_card.kind, "#ffffff"))
        accent.setAlpha(130)
        self._pen_normal = QPen(accent, 1.5)
        self._pen_normal.setCapStyle(Qt.PenCapStyle.RoundCap)

        dim = QColor(_KIND_ACCENT.get(src_card.kind, "#ffffff"))
        dim.setAlpha(30)
        self._pen_dim = QPen(dim, 1.0)

        self.setZValue(-1)
        self.setPen(self._pen_normal)
        self._rebuild_path()

    def _rebuild_path(self) -> None:
        src  = self._src.right_anchor()
        dst  = self._dst.left_anchor()
        mid_x = (src.x() + dst.x()) / 2

        path = QPainterPath(src)
        path.cubicTo(
            QPointF(mid_x, src.y()),
            QPointF(mid_x, dst.y()),
            dst,
        )
        self.setPath(path)

    def set_dimmed(self, dimmed: bool) -> None:
        self.setPen(self._pen_dim if dimmed else self._pen_normal)

    @property
    def src_card(self) -> TraceNodeCard:
        return self._src

    @property
    def dst_card(self) -> TraceNodeCard:
        return self._dst


# ── Canvas ────────────────────────────────────────────────────────────────────

class TraceGraphCanvas(QGraphicsView):
    """
    QGraphicsView diagram surface.

    Public API
    ----------
    set_graph(graph)       Replace the displayed graph (re-runs layout).
    set_filter(kind)       Dim nodes/edges outside *kind*; None = show all.
    focus_node(node_id)    Center + select the given node.
    selected_node_id()     Currently selected node id, or None.
    fit_view()             Fit all content into the viewport.

    Signals
    -------
    node_selected(str)     Emitted on single click (node id).
    node_activated(str)    Emitted on double click (→ open source file).
    """

    node_selected  = pyqtSignal(str)
    node_activated = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._scene = QGraphicsScene(self)
        self._scene.setBackgroundBrush(_BG_COLOR)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setOptimizationFlags(
            QGraphicsView.OptimizationFlag.DontSavePainterState
            | QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing,
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setStyleSheet("border: none; background-color: #010a15;")

        self._cards:         Dict[str, TraceNodeCard] = {}
        self._edges:         List[_EdgeItem]          = []
        self._selected_id:   Optional[str]            = None
        self._active_filter: Optional[NodeKind]       = None

        # Floating FIT button (repositioned in resizeEvent)
        self._fit_btn = QPushButton("⊞ FIT", self)
        self._fit_btn.setFixedSize(64, 24)
        self._fit_btn.setStyleSheet(
            "QPushButton { background-color: #041624; color: #2d5f7a; "
            "border: 1px solid #2d5f7a; border-radius: 4px; font-size: 8pt; }"
            "QPushButton:hover { color: #00c8ff; border-color: #00c8ff; }"
        )
        self._fit_btn.clicked.connect(self.fit_view)
        self._fit_btn.move(8, 8)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_graph(self, graph: TraceGraph) -> None:
        """Replace the current graph and re-run layout."""
        self._scene.clear()
        self._cards.clear()
        self._edges.clear()
        self._selected_id    = None
        self._active_filter  = None

        if not graph.nodes:
            self._draw_placeholder()
            return

        self._draw_column_headers()
        self._layout_nodes(graph)
        self._draw_edges(graph)
        self.fit_view()

    def set_filter(self, kind: Optional[NodeKind]) -> None:
        """Dim all nodes/edges not matching *kind*. None = show all."""
        self._active_filter = kind
        for card in self._cards.values():
            card.set_dimmed(kind is not None and card.kind != kind)
        for edge in self._edges:
            if kind is None:
                edge.set_dimmed(False)
            else:
                src_dim = self._cards.get(edge.src_card.node_id)
                dst_dim = self._cards.get(edge.dst_card.node_id)
                dimmed  = (
                    (src_dim is not None and src_dim._dimmed) or
                    (dst_dim is not None and dst_dim._dimmed)
                )
                edge.set_dimmed(dimmed)

    def focus_node(self, node_id: str) -> None:
        """Center on and select the given node."""
        card = self._cards.get(node_id)
        if card is None:
            return
        self._select(node_id)
        self.centerOn(card)

    def selected_node_id(self) -> Optional[str]:
        return self._selected_id

    def fit_view(self) -> None:
        """Fit all scene content into the viewport with padding."""
        rect = self._scene.itemsBoundingRect()
        if not rect.isEmpty():
            self.fitInView(rect.adjusted(-32, -32, 32, 32), Qt.AspectRatioMode.KeepAspectRatio)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _draw_column_headers(self) -> None:
        font = QFont("monospace")
        font.setPointSizeF(8.0)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        for kind in COLUMN_ORDER:
            item = QGraphicsSimpleTextItem(_COLUMN_LABELS[kind])
            item.setFont(font)
            item.setBrush(QColor(_KIND_ACCENT[kind]))
            item.setPos(_COLUMN_X[kind], HEADER_Y)
            self._scene.addItem(item)

    def _layout_nodes(self, graph: TraceGraph) -> None:
        for kind in COLUMN_ORDER:
            col_x = _COLUMN_X[kind]
            for row, node in enumerate(graph.by_kind(kind)):
                y    = NODES_START_Y + row * (CARD_H + NODE_VERT_GAP)
                card = TraceNodeCard(
                    node_id=node.id,
                    kind=node.kind,
                    label=node.label,
                    sublabel=node.sublabel,
                )
                card.setPos(col_x, y)
                card.node_clicked.connect(self._on_card_clicked)
                card.node_double_clicked.connect(self._on_card_double_clicked)
                self._scene.addItem(card)
                self._cards[node.id] = card

    def _draw_edges(self, graph: TraceGraph) -> None:
        for edge in graph.edges:
            src_card = self._cards.get(edge.source_id)
            dst_card = self._cards.get(edge.target_id)
            if src_card is None or dst_card is None:
                log.debug("Edge %s→%s: card missing — skipping", edge.source_id, edge.target_id)
                continue
            item = _EdgeItem(src_card, dst_card, edge.kind, edge.confidence)
            self._scene.addItem(item)
            self._edges.append(item)

    def _draw_placeholder(self) -> None:
        font = QFont("monospace")
        font.setPointSizeF(10)
        text = self._scene.addText(
            "No trace data yet.\n"
            "Run S3 / S4 / S5 to generate the trace matrix.",
            font,
        )
        text.setDefaultTextColor(QColor("#2d5f7a"))

    # ── Selection ─────────────────────────────────────────────────────────────

    def _select(self, node_id: str) -> None:
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)
        self._selected_id = node_id
        if node_id in self._cards:
            self._cards[node_id].set_selected(True)

    def _deselect_all(self) -> None:
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)
        self._selected_id = None

    def _on_card_clicked(self, node_id: str) -> None:
        self._select(node_id)
        self.node_selected.emit(node_id)

    def _on_card_double_clicked(self, node_id: str) -> None:
        self.node_activated.emit(node_id)

    # ── Mouse / keyboard events ───────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            item = self.itemAt(event.pos())
            if item is None:
                self._deselect_all()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta  = event.angleDelta().y()
            factor = 1.12 if delta > 0 else 1 / 1.12
            new_scale = self.transform().m11() * factor
            if ZOOM_MIN <= new_scale <= ZOOM_MAX:
                self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_0 and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.resetTransform()
            self.fit_view()
        elif event.key() == Qt.Key.Key_Space:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
        super().keyReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        vp = self.viewport()
        if vp:
            self._fit_btn.move(vp.width() - 76, 8)
