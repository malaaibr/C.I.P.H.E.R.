"""Workflow panel — animated V-cycle SDLC canvas + node sidebar + detail strip."""

from __future__ import annotations

import math

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QDialog, QDialogButtonBox, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath,
    QLinearGradient, QFont, QFontMetrics, QRadialGradient,
)

from interfaces.gui.styles import palette
from interfaces.gui.constants import ALL_NODE_IDS

# ── SDLC phase definitions ────────────────────────────────────────────────────
_PHASES: dict[str, dict] = {
    "REQ":    {"label": "Requirements",     "color": "#3ce8c8"},
    "ARCH":   {"label": "Architecture",     "color": "#5b8fff"},
    "DESIGN": {"label": "Detailed Design",  "color": "#a78bfa"},
    "IMPL":   {"label": "Implementation",   "color": "#f472b6"},
    "CODE":   {"label": "Coding / UT Prep", "color": "#ff6b35"},
    "UNIT":   {"label": "Unit Test",        "color": "#f5a623"},
    "INTEG":  {"label": "Integration Test", "color": "#4ade80"},
    "SYS":    {"label": "System Test",      "color": "#fb7185"},
    "ACCEPT": {"label": "Acceptance",       "color": "#38bdf8"},
}

# ── Node definitions (phase, output, review, tracesTo) ───────────────────────
_NODES: list[dict] = [
    # ── Left arm — definition ─────────────────────────────────────────────────
    {"id": "S1N1", "phase": "REQ",    "tracesTo": "ACCEPT",
     "label": "Input Collection & LLD Gen",   "output": "[SWC]_TEMP_LLD.csv",            "review": False},
    {"id": "S1N2", "phase": "REQ",    "tracesTo": "ACCEPT",
     "label": "Upload to Req Mgmt Tool",       "output": "LLD with unique IDs",           "review": True},
    {"id": "S1N3", "phase": "REQ",    "tracesTo": "ACCEPT",
     "label": "Extract IDs from Req Tool",     "output": "Updated LLD CSV with IDs",      "review": True},
    {"id": "S1N4", "phase": "ARCH",   "tracesTo": "SYS",
     "label": "Categorize Requirements",       "output": "[SWC]_FUNC_req.csv",            "review": False},
    {"id": "S2N1", "phase": "ARCH",   "tracesTo": "SYS",
     "label": "Embed LLD in Source Code",      "output": "updated_[SWC].c",               "review": False},
    {"id": "S2N2", "phase": "DESIGN", "tracesTo": "INTEG",
     "label": "Await Developer Review",        "output": "Approved linked code",          "review": True},
    {"id": "S4N1", "phase": "DESIGN", "tracesTo": "INTEG",
     "label": "Link LLD to HLD",               "output": "HLD_LLD_Links.json",            "review": False},
    {"id": "S3N1", "phase": "IMPL",   "tracesTo": "UNIT",
     "label": "Generate Traceability Report",  "output": "LLD_Code_Trace_Report.csv",     "review": False},
    # ── Bottom node — conceptual, non-runnable ────────────────────────────────
    {"id": "BOT",  "phase": "CODE",   "tracesTo": None,
     "label": "Coding / Unit Test Prep",       "output": "[SWC].c  ·  test.bat",          "review": False},
    # ── Right arm — verification (stored bottom-to-top) ───────────────────────
    {"id": "S6N1", "phase": "UNIT",   "tracesTo": "IMPL",
     "label": "Prepare Test Artifacts",        "output": "[SWC].tst",                     "review": True},
    {"id": "S5N1", "phase": "INTEG",  "tracesTo": "DESIGN",
     "label": "Full Downstream Trace",         "output": "HLD_LLD_Code_Trace_Matrix.csv", "review": False},
    {"id": "S7N1", "phase": "SYS",    "tracesTo": "ARCH",
     "label": "Parse .TST & Generate UTD",     "output": "[SWC]_UTD.md",                  "review": False},
    {"id": "S8N1", "phase": "SYS",    "tracesTo": "ARCH",
     "label": "Link UTD to LLD",               "output": "UTD_LLD_Links.json",            "review": False},
    {"id": "S9N1", "phase": "ACCEPT", "tracesTo": "REQ",
     "label": "Build Full Traceability Matrix","output": "Full_Traceability_Matrix.csv",   "review": False},
]

_NODE_BY_ID: dict[str, dict] = {n["id"]: n for n in _NODES}

_LEFT_ORDER  = ["S1N1", "S1N2", "S1N3", "S1N4", "S2N1", "S2N2", "S4N1", "S3N1"]
_BOT_ID      = "BOT"
_RIGHT_ORDER = ["S6N1", "S5N1", "S7N1", "S8N1", "S9N1"]

_BRIDGES: list[dict] = [
    {"l": "S1N1", "r": "S9N1", "label": "Full Traceability",   "color": "#3ce8c8"},
    {"l": "S1N4", "r": "S7N1", "label": "System Verification", "color": "#5b8fff"},
    {"l": "S2N2", "r": "S5N1", "label": "Integration Trace",   "color": "#a78bfa"},
    {"l": "S4N1", "r": "S5N1", "label": "Design Verification", "color": "#a78bfa"},
    {"l": "S3N1", "r": "S6N1", "label": "Unit Test Trace",     "color": "#f5a623"},
]

_LEFT_ZONES: list[dict] = [
    {"ids": ["S1N1", "S1N2", "S1N3"], "phase": "REQ"},
    {"ids": ["S1N4", "S2N1"],         "phase": "ARCH"},
    {"ids": ["S2N2", "S4N1"],         "phase": "DESIGN"},
    {"ids": ["S3N1"],                 "phase": "IMPL"},
]
_RIGHT_ZONES: list[dict] = [
    {"ids": ["S6N1"],          "phase": "UNIT"},
    {"ids": ["S5N1"],          "phase": "INTEG"},
    {"ids": ["S7N1", "S8N1"],  "phase": "SYS"},
    {"ids": ["S9N1"],          "phase": "ACCEPT"},
]

_SIDEBAR_GROUPS: list[dict] = [
    {"label": "S1 — LLD Generation",     "ids": ["S1N1", "S1N2", "S1N3", "S1N4"]},
    {"label": "S2 — LLD→Code Linking",   "ids": ["S2N1", "S2N2"]},
    {"label": "S4 — LLD→HLD Linking",    "ids": ["S4N1"]},
    {"label": "S3 — LLD→Code Trace",     "ids": ["S3N1"]},
    {"label": "S6 — Unit Test AI Tool",  "ids": ["S6N1"]},
    {"label": "S5 — Full Trace Matrix",  "ids": ["S5N1"]},
    {"label": "S7 — UTD Generation",     "ids": ["S7N1"]},
    {"label": "S8 — UTD→LLD Linking",    "ids": ["S8N1"]},
    {"label": "S9 — Full Traceability",  "ids": ["S9N1"]},
]

# Kept for backward-compatibility with any code that imports STAGES
STAGES: list[dict] = [
    {
        "id": "S1", "label": "Stage 1", "name": "LLD Generation",
        "nodes": [
            {"id": "S1N1", "label": "N1 — Input Collection & LLD Gen",  "human_review": False},
            {"id": "S1N2", "label": "N2 — Upload to Req. Mgmt Tool",     "human_review": True,
             "review_msg": "Upload the generated LLD to your Requirements Management tool.\nOnce unique IDs are assigned, click Continue."},
            {"id": "S1N3", "label": "N3 — Extract IDs from Req Tool",    "human_review": True,
             "review_msg": "Extract the updated requirements with new IDs from your Req Mgmt tool.\nSave locally, then click Continue."},
            {"id": "S1N4", "label": "N4 — Categorize Requirements",      "human_review": False},
        ],
    },
    {
        "id": "S2", "label": "Stage 2", "name": "LLD → Code Linking",
        "nodes": [
            {"id": "S2N1", "label": "N1 — Embed LLD in Source Code",     "human_review": False},
            {"id": "S2N2", "label": "N2 — Await Developer Review",        "human_review": True,
             "review_msg": "Review the LLD-annotated source code.\nVerify requirement references before continuing."},
        ],
    },
    {"id": "S3", "label": "Stage 3", "name": "LLD→Code Traceability",
     "nodes": [{"id": "S3N1", "label": "N1 — Generate Traceability Report", "human_review": False}]},
    {"id": "S4", "label": "Stage 4", "name": "LLD → HLD Linking",
     "nodes": [{"id": "S4N1", "label": "N1 — Link LLD to HLD",              "human_review": False}]},
    {"id": "S5", "label": "Stage 5", "name": "Code→LLD→HLD TR Gen",
     "nodes": [{"id": "S5N1", "label": "N1 — Full Downstream Trace",        "human_review": False}]},
    {"id": "S6", "label": "Stage 6", "name": "UT AI Tool",
     "nodes": [{"id": "S6N1", "label": "N1 — Prepare Test Artifacts",       "human_review": True,
                "review_msg": "Run VectorCAST/Tessy with the generated test.bat.\nClick Continue once .TST files are available."}]},
    {"id": "S7", "label": "Stage 7", "name": "UT Document Gen",
     "nodes": [{"id": "S7N1", "label": "N1 — Parse .TST & Generate UTD",   "human_review": False}]},
    {"id": "S8", "label": "Stage 8", "name": "UTD → LLD Linking",
     "nodes": [{"id": "S8N1", "label": "N1 — Link UTD to LLD",              "human_review": False}]},
    {"id": "S9", "label": "Stage 9", "name": "Full Traceability Report",
     "nodes": [{"id": "S9N1", "label": "N1 — Build Full Matrix",            "human_review": False}]},
]


# ─────────────────────────────────────────────────────────────────────────────
# V-Cycle Canvas
# ─────────────────────────────────────────────────────────────────────────────

class VCycleCanvas(QWidget):
    """Custom-painted animated V-cycle SDLC visualization."""

    node_selected = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(600, 380)
        self._statuses: dict[str, str] = {n["id"]: "idle" for n in _NODES}
        self._selected_id: str | None = None
        self._anim_phase  = 0.0   # 0..1, drives traveling dots
        self._pulse_phase = 0.0   # 0..1, drives pulsing glow on running nodes
        self._node_rects: dict[str, QRectF] = {}

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(50)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._anim_phase  = (self._anim_phase  + 0.022) % 1.0
        self._pulse_phase = (self._pulse_phase + 0.045) % 1.0
        self.update()

    def set_node_status(self, node_id: str, status: str) -> None:
        self._statuses[node_id] = status
        self.update()

    def select_node(self, node_id: str) -> None:
        self._selected_id = node_id
        self.update()

    def _mono(self, px: int, bold: bool = False) -> QFont:
        f = QFont()
        try:
            f.setFamilies(["JetBrains Mono", "Cascadia Code", "Consolas"])
        except AttributeError:
            f.setFamily("Consolas")
        f.setPixelSize(px)
        if bold:
            f.setBold(True)
        return f

    def _get_positions(self) -> tuple[dict[str, QPointF], float]:
        W, H = self.width(), self.height()
        PAD_X, PAD_Y = 106, 44
        usable_h = H - PAD_Y * 2
        CX = W / 2.0

        pos: dict[str, QPointF] = {}

        n_left = len(_LEFT_ORDER)
        for i, nid in enumerate(_LEFT_ORDER):
            t = i / n_left
            x = PAD_X + (CX - PAD_X - 28) * t
            y = PAD_Y + (usable_h - 56) * t
            pos[nid] = QPointF(x, y)

        pos[_BOT_ID] = QPointF(CX, H - PAD_Y - 8)

        n_right = len(_RIGHT_ORDER)
        for i, nid in enumerate(_RIGHT_ORDER):
            t = (i + 1) / (n_right + 1)
            x = (CX + 28) + (W - PAD_X - CX - 28) * t
            y = (H - PAD_Y - 56) - (usable_h - 56) * t
            pos[nid] = QPointF(x, y)

        return pos, CX

    # ── paintEvent ────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        pos, CX = self._get_positions()

        self._draw_bg(p, W, H, CX)
        self._draw_grid(p, W, H)
        self._draw_backbone_glow(p, pos)
        self._draw_bridges(p, pos)
        self._draw_segments(p, pos)
        self._draw_direction_labels(p, W, H)
        self._draw_phase_labels(p, pos)

        self._node_rects = {}
        for n in _NODES:
            if n["id"] in pos:
                self._draw_node_card(p, n, pos[n["id"]])

        p.end()

    def _draw_bg(self, p: QPainter, W: int, H: int, CX: float) -> None:
        p.fillRect(self.rect(), QColor("#070a0f"))
        grad = QRadialGradient(CX, H * 0.65, max(W, H) * 0.55)
        grad.setColorAt(0.0, QColor(255, 107, 53, 10))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), QBrush(grad))

    def _draw_grid(self, p: QPainter, W: int, H: int) -> None:
        pen = QPen(QColor(35, 48, 68, 70))
        pen.setWidth(1)
        p.setPen(pen)
        step = 40
        for x in range(0, W + step, step):
            p.drawLine(x, 0, x, H)
        for y in range(0, H + step, step):
            p.drawLine(0, y, W, y)

    def _draw_backbone_glow(self, p: QPainter, pos: dict) -> None:
        def glow_path(ids: list[str], rgba: tuple) -> None:
            path = QPainterPath()
            pts = [pos[i] for i in ids if i in pos]
            if not pts:
                return
            path.moveTo(pts[0])
            for pt in pts[1:]:
                path.lineTo(pt)
            pen = QPen(QColor(*rgba))
            pen.setWidthF(14)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)

        glow_path(_LEFT_ORDER + [_BOT_ID], (60, 232, 200, 9))
        glow_path([_BOT_ID] + _RIGHT_ORDER, (167, 139, 250, 9))

    def _draw_segments(self, p: QPainter, pos: dict) -> None:
        all_left  = _LEFT_ORDER + [_BOT_ID]
        all_right = [_BOT_ID] + _RIGHT_ORDER

        def seg(a_id: str, b_id: str, hex_color: str, active: bool) -> None:
            a, b = pos.get(a_id), pos.get(b_id)
            if not a or not b:
                return
            col = QColor(hex_color)
            if active:
                pen = QPen(col, 1.8)
            else:
                fade = QColor(hex_color)
                fade.setAlpha(70)
                pen = QPen(fade, 1.0, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(a, b)

            if active:
                self._draw_arrowhead(p, a, b, hex_color)
                t = self._anim_phase
                dx = b.x() - a.x()
                dy = b.y() - a.y()
                dot = QPointF(a.x() + dx * t, a.y() + dy * t)
                dot_col = QColor(hex_color)
                dot_col.setAlpha(210)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(dot_col))
                p.drawEllipse(dot, 3.5, 3.5)

        for i in range(len(all_left) - 1):
            a_id, b_id = all_left[i], all_left[i + 1]
            active = (
                self._statuses.get(a_id, "idle") == "done" and
                self._statuses.get(b_id, "idle") in ("running", "done", "waiting")
            )
            seg(a_id, b_id, "#3ce8c8", active)

        for i in range(len(all_right) - 1):
            a_id, b_id = all_right[i], all_right[i + 1]
            active = (
                self._statuses.get(a_id, "idle") == "done" and
                self._statuses.get(b_id, "idle") in ("running", "done", "waiting")
            )
            seg(a_id, b_id, "#a78bfa", active)

    def _draw_arrowhead(self, p: QPainter, a: QPointF, b: QPointF, hex_color: str) -> None:
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        tip_x = b.x() - ux * 8
        tip_y = b.y() - uy * 8
        perp_x, perp_y = -uy * 4, ux * 4
        path = QPainterPath()
        path.moveTo(b.x(), b.y())
        path.lineTo(tip_x + perp_x, tip_y + perp_y)
        path.lineTo(tip_x - perp_x, tip_y - perp_y)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(hex_color)))
        p.drawPath(path)

    def _draw_bridges(self, p: QPainter, pos: dict) -> None:
        font = self._mono(9)
        p.setFont(font)
        fm = QFontMetrics(font)
        for br in _BRIDGES:
            a, b = pos.get(br["l"]), pos.get(br["r"])
            if not a or not b:
                continue
            both_done = (
                self._statuses.get(br["l"]) in ("done", "complete") and
                self._statuses.get(br["r"]) in ("done", "complete")
            )
            col = QColor(br["color"])
            col.setAlpha(160 if both_done else 40)
            pen = QPen(col, 0.9, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(a, b)

            # Bridge label — pill with opaque background for readability
            mid = QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)
            lbl = br["label"]
            tw = fm.horizontalAdvance(lbl)
            th = fm.height()
            pw, ph2 = tw + 16, th + 6
            lrx, lry = mid.x() - pw / 2, mid.y() - ph2 / 2 - 2

            bg_col = QColor(7, 10, 15, 220)
            p.setBrush(QBrush(bg_col))
            border_col = QColor(br["color"])
            border_col.setAlpha(100 if both_done else 55)
            p.setPen(QPen(border_col, 0.8))
            p.drawRoundedRect(QRectF(lrx, lry, pw, ph2), 3, 3)

            text_col = QColor(br["color"])
            text_col.setAlpha(230 if both_done else 160)
            p.setPen(text_col)
            p.drawText(QRectF(lrx, lry, pw, ph2), Qt.AlignmentFlag.AlignCenter, lbl)

            if both_done:
                for pt in (a, b):
                    ring_col = QColor(br["color"])
                    ring_col.setAlpha(120)
                    p.setPen(QPen(ring_col, 1))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawEllipse(pt, 5, 5)

    def _draw_phase_labels(self, p: QPainter, pos: dict) -> None:
        for zone in _LEFT_ZONES:
            pts = [pos[nid] for nid in zone["ids"] if nid in pos]
            if not pts:
                continue
            avg_x = sum(pt.x() for pt in pts) / len(pts) - 104
            avg_y = sum(pt.y() for pt in pts) / len(pts)
            self._draw_phase_pill(p, avg_x, avg_y, zone["phase"])

        for zone in _RIGHT_ZONES:
            pts = [pos[nid] for nid in zone["ids"] if nid in pos]
            if not pts:
                continue
            avg_x = sum(pt.x() for pt in pts) / len(pts) + 104
            avg_y = sum(pt.y() for pt in pts) / len(pts)
            self._draw_phase_pill(p, avg_x, avg_y, zone["phase"])

        if _BOT_ID in pos:
            bp = pos[_BOT_ID]
            self._draw_phase_pill(p, bp.x(), bp.y() + 34, "CODE")

    def _draw_phase_pill(self, p: QPainter, cx: float, cy: float, phase_key: str) -> None:
        ph = _PHASES.get(phase_key)
        if not ph:
            return
        label = ph["label"].upper()
        font = self._mono(10, bold=True)
        p.setFont(font)
        fm = QFontMetrics(font)
        tw = fm.horizontalAdvance(label)
        pw, ph_h = tw + 26, 20
        rx, ry = cx - pw / 2, cy - ph_h / 2

        # Solid dark background so pill stands out against the grid/lines
        bg = QColor(7, 10, 15, 235)
        p.setBrush(QBrush(bg))
        border = QColor(ph["color"])
        border.setAlpha(160)
        p.setPen(QPen(border, 1.2))
        p.drawRoundedRect(QRectF(rx, ry, pw, ph_h), 4, 4)

        # Colored dot
        dot_col = QColor(ph["color"])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(dot_col))
        p.drawEllipse(QPointF(rx + 10, cy), 3.5, 3.5)

        # Label text — full brightness
        text_col = QColor(ph["color"])
        p.setPen(text_col)
        p.drawText(QRectF(rx + 18, ry, pw - 18, ph_h), Qt.AlignmentFlag.AlignVCenter, label)

    def _draw_direction_labels(self, p: QPainter, W: int, H: int) -> None:
        font = self._mono(9, bold=True)
        p.setFont(font)
        fm = QFontMetrics(font)

        for text, x_pivot, angle, rgba in (
            ("↓  DEFINITION",   14,     -90, (60, 232, 200, 120)),
            ("VERIFICATION  ▶", W - 14,  90, (167, 139, 250, 120)),
        ):
            p.save()
            p.translate(x_pivot, H / 2)
            p.rotate(angle)
            tw = fm.horizontalAdvance(text)
            p.setPen(QColor(*rgba))
            p.drawText(QRectF(-tw / 2, -8, tw, 16), Qt.AlignmentFlag.AlignCenter, text)
            p.restore()

    # ── Node card ─────────────────────────────────────────────────────────────

    def _draw_node_card(self, p: QPainter, node: dict, center: QPointF) -> None:
        nid    = node["id"]
        status = self._statuses.get(nid, "idle")
        is_bot = nid == _BOT_ID
        ph_col = QColor(_PHASES[node["phase"]]["color"])

        CW, CH = (130, 46) if is_bot else (150, 74)
        rx = center.x() - CW / 2
        ry = center.y() - CH / 2
        rect = QRectF(rx, ry, CW, CH)
        if not is_bot:
            self._node_rects[nid] = rect

        # ── card background ───────────────────────────────────────────────
        if status in ("done", "complete"):
            bg = QColor(74, 222, 128, 8)
        elif status == "error":
            bg = QColor(240, 80, 96, 8)
        elif status in ("running", "waiting"):
            bg = QColor(245, 166, 35, 10)
        else:
            bg = QColor(19, 26, 36, 230)
        p.setBrush(QBrush(bg))

        # ── border ────────────────────────────────────────────────────────
        if status == "running":
            alpha = int(160 + 95 * math.sin(self._pulse_phase * 2 * math.pi))
            border = QColor(245, 166, 35, alpha)
            bw = 1.5
        elif status in ("done", "complete"):
            border = QColor(74, 222, 128, 100)
            bw = 1.2
        elif status == "error":
            border = QColor(240, 80, 96, 100)
            bw = 1.2
        elif status == "waiting":
            border = QColor(91, 143, 255, 120)
            bw = 1.2
        elif self._selected_id == nid:
            border = QColor(_PHASES[node["phase"]]["color"])
            bw = 1.5
        else:
            border = QColor(35, 48, 68)
            bw = 1.0
        p.setPen(QPen(border, bw))
        p.drawRoundedRect(rect, 7, 7)

        if is_bot:
            # Minimal pill for the bottom "virtual" node
            p.setFont(self._mono(8, bold=True))
            p.setPen(ph_col)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, node["label"])
            return

        pad = 9

        # ── phase-colored ID ──────────────────────────────────────────────
        p.setFont(self._mono(9, bold=True))
        p.setPen(ph_col)
        p.drawText(QRectF(rx + pad, ry + pad, CW - pad * 2 - 14, 13),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, nid)

        # ── status dot (top-right) ────────────────────────────────────────
        if status == "running":
            da = int(160 + 95 * math.sin(self._pulse_phase * 2 * math.pi))
            dot_col = QColor(245, 166, 35, da)
        elif status in ("done", "complete"):
            dot_col = QColor(74, 222, 128)
        elif status == "error":
            dot_col = QColor(240, 80, 96)
        elif status == "waiting":
            dot_col = QColor(91, 143, 255)
        else:
            dot_col = QColor(53, 77, 102)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(dot_col))
        p.drawEllipse(QPointF(rx + CW - pad - 4, ry + pad + 7), 4, 4)

        # ── short label (1-2 lines) ───────────────────────────────────────
        lbl = node["label"]
        if len(lbl) > 26:
            lbl = lbl[:23] + "…"
        p.setFont(self._mono(8))
        p.setPen(QColor(168, 188, 212))
        p.drawText(QRectF(rx + pad, ry + 24, CW - pad * 2, 22),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
                   | Qt.TextFlag.TextWordWrap, lbl)

        # ── output artifact ───────────────────────────────────────────────
        out = node["output"]
        if len(out) > 24:
            out = out[:21] + "…"
        out_col = QColor(74, 222, 128) if status in ("done", "complete") else QColor(53, 77, 102)
        p.setFont(self._mono(7))
        p.setPen(out_col)
        p.drawText(QRectF(rx + pad, ry + CH - 18, CW - pad * 2, 11),
                   Qt.AlignmentFlag.AlignLeft, out)

        # ── REVIEW badge ──────────────────────────────────────────────────
        if node.get("review") and status not in ("done", "complete"):
            bfont = self._mono(6)
            p.setFont(bfont)
            bfm = QFontMetrics(bfont)
            btxt = "REVIEW"
            bw2  = bfm.horizontalAdvance(btxt) + 8
            bh2  = 10
            bx2  = rx + CW - pad - bw2
            by2  = ry + CH - 18
            p.setBrush(QBrush(QColor(245, 166, 35, 26)))
            p.setPen(QPen(QColor(245, 166, 35, 90), 0.8))
            p.drawRoundedRect(QRectF(bx2, by2, bw2, bh2), 2, 2)
            p.setPen(QColor(245, 166, 35))
            p.drawText(QRectF(bx2, by2, bw2, bh2), Qt.AlignmentFlag.AlignCenter, btxt)

        # ── progress bar (bottom strip) ───────────────────────────────────
        bar_y = ry + CH - 4
        bar_w = CW - pad * 2
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(33, 45, 63)))
        p.drawRoundedRect(QRectF(rx + pad, bar_y, bar_w, 2.5), 1, 1)
        if status in ("done", "complete"):
            p.setBrush(QBrush(ph_col))
            p.drawRoundedRect(QRectF(rx + pad, bar_y, bar_w, 2.5), 1, 1)
        elif status == "running":
            p.setBrush(QBrush(QColor(245, 166, 35)))
            p.drawRoundedRect(QRectF(rx + pad, bar_y, bar_w * 0.55, 2.5), 1, 1)

    # ── Mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pt = QPointF(event.position())
            for nid, rect in self._node_rects.items():
                if rect.contains(pt):
                    self._selected_id = nid
                    self.node_selected.emit(nid)
                    self.update()
                    return

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            pt = QPointF(event.position())
            for nid, rect in self._node_rects.items():
                if rect.contains(pt) and nid != _BOT_ID:
                    self.node_selected.emit(nid)
                    return


# ─────────────────────────────────────────────────────────────────────────────
# WorkflowPanel — main panel composing sidebar + canvas + detail strip
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowPanel(QWidget):
    """
    @brief V-cycle SDLC workflow panel.

    Layout:  [Left sidebar 260px] | [VCycleCanvas (flex)] / [Detail strip 64px]

    Signals
    -------
    node_run_requested(str)  — emitted when user clicks a sidebar row
    run_all_requested()      — emitted when "RUN ALL" is clicked
    reset_requested()        — emitted when reset button is clicked
    """

    node_run_requested = pyqtSignal(str)
    run_all_requested  = pyqtSignal()
    reset_requested    = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._node_statuses: dict[str, str] = {}
        self._sidebar_dots:  dict[str, QLabel]  = {}
        self._sidebar_rows:  dict[str, QWidget] = {}
        self._detail_labels: dict[str, QLabel]  = {}
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        self._canvas = VCycleCanvas()
        self._canvas.node_selected.connect(self._on_canvas_select)
        rl.addWidget(self._canvas, stretch=1)
        rl.addWidget(self._build_detail_strip())
        root.addWidget(right, stretch=1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(
            f"background-color: {palette.BG_SIDEBAR}; "
            f"border-right: 1px solid {palette.BORDER};"
        )
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Action buttons
        btn_area = QWidget()
        btn_area.setStyleSheet(f"background: {palette.BG_SIDEBAR};")
        bl = QHBoxLayout(btn_area)
        bl.setContentsMargins(10, 10, 10, 8)
        bl.setSpacing(7)

        self._run_all_btn = QPushButton("▶  RUN ALL")
        self._run_all_btn.setFixedHeight(30)
        self._run_all_btn.setStyleSheet(self._run_btn_style(False))
        self._run_all_btn.clicked.connect(self.run_all_requested)
        bl.addWidget(self._run_all_btn, stretch=1)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedSize(30, 30)
        reset_btn.setStyleSheet(
            f"QPushButton {{ background: {palette.BG_CARD}; border: 1px solid {palette.BORDER}; "
            f"color: {palette.TEXT2}; font-size: 14px; border-radius: 4px; }}"
            f"QPushButton:hover {{ border-color: {palette.BORDER_BRIGHT}; color: {palette.TEXT1}; }}"
        )
        reset_btn.clicked.connect(self.reset_requested)
        bl.addWidget(reset_btn)
        sl.addWidget(btn_area)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {palette.BORDER};")
        sep.setFixedHeight(1)
        sl.addWidget(sep)

        # Node list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            f"QScrollBar:vertical {{ width: 3px; background: {palette.BG_APP}; border: none; }}"
            f"QScrollBar::handle:vertical {{ background: {palette.BORDER}; border-radius: 1px; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )

        content = QWidget()
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content.setStyleSheet(f"QWidget {{ background: {palette.BG_SIDEBAR}; }}")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 6, 0, 6)
        cl.setSpacing(0)

        for group in _SIDEBAR_GROUPS:
            first_n = _NODE_BY_ID.get(group["ids"][0])
            ph_color = _PHASES[first_n["phase"]]["color"] if first_n else "#607490"

            hdr = QWidget()
            hdr.setFixedHeight(22)
            hdr.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            hdr.setStyleSheet(f"QWidget {{ background: {palette.BG_SIDEBAR}; }}")
            hl = QHBoxLayout(hdr)
            hl.setContentsMargins(10, 0, 10, 0)
            hl.setSpacing(8)

            dot_w = QWidget()
            dot_w.setFixedSize(6, 6)
            dot_w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            dot_w.setStyleSheet(f"QWidget {{ background: {ph_color}; border-radius: 3px; }}")
            hl.addWidget(dot_w)

            lbl = QLabel(group["label"])
            lbl.setStyleSheet(
                f"color: {palette.TEXT3}; font-size: 8px; font-family: monospace; "
                f"letter-spacing: 2.5px; background: transparent;"
            )
            hl.addWidget(lbl, stretch=1)
            cl.addWidget(hdr)

            for nid in group["ids"]:
                n = _NODE_BY_ID.get(nid)
                if not n:
                    continue
                row = self._make_node_row(nid, n)
                self._sidebar_rows[nid] = row
                cl.addWidget(row)

        cl.addStretch()
        scroll.setWidget(content)
        sl.addWidget(scroll, stretch=1)
        return sidebar

    def _make_node_row(self, nid: str, node: dict) -> QWidget:
        ph_col = _PHASES[node["phase"]]["color"]
        obj = f"nr_{nid}"

        row = QWidget()
        row.setObjectName(obj)
        row.setFixedHeight(30)
        row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row.setStyleSheet(
            f"QWidget#{obj} {{ background: transparent; "
            f"border-left: 2px solid transparent; }}"
        )
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 0, 10, 0)
        rl.setSpacing(8)

        status_dot = QLabel("●")
        status_dot.setFixedWidth(8)
        status_dot.setStyleSheet(
            f"color: {palette.TEXT3}; font-size: 7px; background: transparent;"
        )
        self._sidebar_dots[nid] = status_dot
        rl.addWidget(status_dot)

        id_lbl = QLabel(nid)
        id_lbl.setFixedWidth(32)
        id_lbl.setStyleSheet(
            f"color: {ph_col}; font-size: 9px; font-family: monospace; "
            f"font-weight: bold; background: transparent;"
        )
        rl.addWidget(id_lbl)

        short = node["label"]
        if len(short) > 21:
            short = short[:19] + "…"
        name_lbl = QLabel(short)
        name_lbl.setStyleSheet(
            f"color: {palette.TEXT1}; font-size: 10px; font-family: monospace; "
            f"background: transparent;"
        )
        rl.addWidget(name_lbl, stretch=1)

        if node.get("review"):
            rev = QLabel("HITL")
            rev.setStyleSheet(
                f"background: rgba(245,166,35,0.12); color: {palette.WARNING}; "
                f"font-size: 7px; padding: 1px 4px; border-radius: 2px; "
                f"border: 1px solid rgba(245,166,35,0.35);"
            )
            rl.addWidget(rev)

        nid_cap = nid  # capture for lambda
        row.mousePressEvent = lambda e, _n=nid_cap: self.node_run_requested.emit(_n)
        return row

    def _build_detail_strip(self) -> QWidget:
        strip = QWidget()
        strip.setFixedHeight(64)
        strip.setStyleSheet(
            f"background: {palette.BG_SIDEBAR}; border-top: 1px solid {palette.BORDER};"
        )
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        cells = [
            ("NODE",       "dcN",  palette.ACCENT),
            ("SDLC PHASE", "dcPh", "#5b8fff"),
            ("TRACES TO",  "dcTr", palette.TEXT1),
            ("PROGRESS",   "dcPg", palette.SUCCESS),
            ("OUTPUT",     "dcOt", palette.TEXT1),
            ("STATUS",     "dcSt", palette.WARNING),
        ]

        for i, (title_txt, key, val_col) in enumerate(cells):
            cell = QWidget()
            cell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            border_r = f"border-right: 1px solid {palette.BORDER};" if i < len(cells) - 1 else ""
            cell.setStyleSheet(f"QWidget {{ background: transparent; {border_r} }}")
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(14, 8, 14, 8)
            cl.setSpacing(3)

            title = QLabel(title_txt)
            title.setStyleSheet(
                f"color: {palette.TEXT3}; font-size: 8px; font-family: monospace; "
                f"letter-spacing: 1.5px; background: transparent;"
            )
            cl.addWidget(title)

            val = QLabel("—")
            val.setStyleSheet(
                f"color: {val_col}; font-size: 11px; font-family: monospace; "
                f"background: transparent;"
            )
            self._detail_labels[key] = val
            cl.addWidget(val)
            sl.addWidget(cell, stretch=1)

        return strip

    # ── Internal handlers ─────────────────────────────────────────────────────

    def _on_canvas_select(self, node_id: str) -> None:
        n = _NODE_BY_ID.get(node_id)
        if not n:
            return
        phase     = _PHASES.get(n["phase"], {})
        traces_to = n.get("tracesTo")
        traces_label = _PHASES.get(traces_to, {}).get("label", "—") if traces_to else "—"
        status    = self._node_statuses.get(node_id, "idle")
        done_cnt  = sum(1 for s in self._node_statuses.values() if s in ("done", "complete"))
        out_txt   = n["output"]
        if len(out_txt) > 28:
            out_txt = out_txt[:25] + "…"

        self._detail_labels["dcN"].setText(node_id)
        self._detail_labels["dcPh"].setText(phase.get("label", "—"))
        self._detail_labels["dcTr"].setText(traces_label)
        self._detail_labels["dcPg"].setText(f"{done_cnt} / {len(ALL_NODE_IDS)}")
        self._detail_labels["dcOt"].setText(out_txt)
        self._detail_labels["dcSt"].setText(status.upper())

        for nid2, row in self._sidebar_rows.items():
            obj = f"nr_{nid2}"
            if nid2 == node_id:
                row.setStyleSheet(
                    f"QWidget#{obj} {{ background: rgba(60,232,200,0.05); "
                    f"border-left: 2px solid {palette.ACCENT}; }}"
                )
            else:
                row.setStyleSheet(
                    f"QWidget#{obj} {{ background: transparent; "
                    f"border-left: 2px solid transparent; }}"
                )

        self._canvas.select_node(node_id)

    # ── Public API (identical surface as original panel) ──────────────────────

    def set_node_status(self, node_id: str, status: str) -> None:
        self._node_statuses[node_id] = status
        self._canvas.set_node_status(node_id, status)

        dot = self._sidebar_dots.get(node_id)
        if dot:
            col = {
                "idle":     palette.TEXT3,
                "running":  palette.WARNING,
                "done":     palette.SUCCESS,
                "complete": palette.SUCCESS,
                "error":    palette.ERROR,
                "waiting":  "#5b8fff",
            }.get(status, palette.TEXT3)
            dot.setStyleSheet(f"color: {col}; font-size: 7px; background: transparent;")

        done_cnt = sum(1 for s in self._node_statuses.values() if s in ("done", "complete"))
        self._detail_labels["dcPg"].setText(f"{done_cnt} / {len(ALL_NODE_IDS)}")

    def set_running(self, running: bool) -> None:
        self._run_all_btn.setEnabled(not running)
        if running:
            self._run_all_btn.setText("⏸  RUNNING…")
            self._run_all_btn.setStyleSheet(self._run_btn_style(True))
        else:
            self._run_all_btn.setText("▶  RUN ALL")
            self._run_all_btn.setStyleSheet(self._run_btn_style(False))

    def show_node_detail(self, node_id: str, status: str, artifacts: list[str]) -> None:
        self._on_canvas_select(node_id)
        if status:
            self._detail_labels["dcSt"].setText(status.upper())

    # ── Style helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _run_btn_style(running: bool) -> str:
        if running:
            return (
                f"QPushButton {{ background: rgba(245,166,35,0.08); "
                f"border: 1px solid rgba(245,166,35,0.4); color: {palette.WARNING}; "
                f"font-family: monospace; font-size: 10px; font-weight: bold; "
                f"letter-spacing: 2px; border-radius: 4px; }}"
            )
        return (
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 rgba(60,232,200,0.12),stop:1 rgba(91,143,255,0.08)); "
            f"border: 1px solid rgba(60,232,200,0.35); color: {palette.ACCENT}; "
            f"font-family: monospace; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 2px; border-radius: 4px; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 rgba(60,232,200,0.22),stop:1 rgba(91,143,255,0.16)); }}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ReviewDialog — human review gate (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

class ReviewDialog(QDialog):
    """@brief Modal human review gate dialog."""

    def __init__(self, node_id: str, message: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Human Review Required — {node_id}")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(
            f"QDialog {{ background: {palette.BG_APP}; color: {palette.TEXT1}; }}"
        )
        self._flash_on = True
        self._build_ui(node_id, message)
        self._start_flash()

    def _build_ui(self, node_id: str, message: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(12)

        hdr_row = QHBoxLayout()
        self._flash_title = QLabel("HUMAN REVIEW REQUIRED")
        self._flash_title.setStyleSheet(
            f"color: {palette.ERROR}; font-size: 13px; font-weight: bold; "
            f"letter-spacing: 2px; font-family: monospace;"
        )
        hdr_row.addWidget(self._flash_title)
        hdr_row.addStretch()
        layout.addLayout(hdr_row)

        node_lbl = QLabel(node_id)
        node_lbl.setStyleSheet(
            f"background: rgba(60,232,200,0.06); color: {palette.ACCENT}; "
            f"font-family: monospace; font-size: 11px; padding: 7px 12px; "
            f"border-radius: 4px; border-left: 3px solid {palette.ACCENT};"
        )
        layout.addWidget(node_lbl)

        msg_area = QTextEdit()
        msg_area.setReadOnly(True)
        msg_area.setPlainText(message)
        msg_area.setFixedHeight(90)
        msg_area.setStyleSheet(
            f"background: {palette.BG_SIDEBAR}; color: {palette.TEXT1}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 5px; "
            f"font-size: 11px; font-family: monospace;"
        )
        layout.addWidget(msg_area)

        inst = QLabel("Complete the required action, then click Continue to resume the pipeline.")
        inst.setStyleSheet(
            f"color: {palette.TEXT2}; font-size: 10px; font-family: monospace; "
            f"padding: 8px; background: {palette.BG_SIDEBAR}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 4px;"
        )
        inst.setWordWrap(True)
        layout.addWidget(inst)

        buttons = QDialogButtonBox()
        cont_btn = QPushButton("✓  Continue")
        cont_btn.setStyleSheet(
            f"QPushButton {{ background: {palette.ACCENT}; color: #000; border: none; "
            f"border-radius: 5px; padding: 8px 20px; font-weight: bold; "
            f"font-family: monospace; font-size: 10px; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ background: #5af5d8; }}"
        )
        abort_btn = QPushButton("✗  Abort")
        abort_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {palette.TEXT2}; "
            f"border: 1px solid {palette.BORDER}; border-radius: 5px; "
            f"padding: 8px 16px; font-family: monospace; font-size: 10px; }}"
            f"QPushButton:hover {{ color: {palette.TEXT1}; border-color: {palette.BORDER_BRIGHT}; }}"
        )
        buttons.addButton(cont_btn,  QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(abort_btn, QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _start_flash(self) -> None:
        self._flash_timer = QTimer(self)
        self._flash_timer.timeout.connect(self._tick_flash)
        self._flash_timer.start(600)

    def _tick_flash(self) -> None:
        self._flash_on = not self._flash_on
        color = palette.ERROR if self._flash_on else palette.TEXT3
        self._flash_title.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold; "
            f"letter-spacing: 2px; font-family: monospace;"
        )
