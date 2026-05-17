"""VoicePanel — JARVIS-style voice interface with orb + waveform + transcript."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from cipher.gui.widgets.arc_reactor import ArcReactorWidget
from cipher.gui.widgets.voice_orb import VoiceOrbWidget
from cipher.gui.widgets.waveform import WaveformWidget

_BG = "#010a15"
_PANEL = "#041624"
_ACCENT = "#00c8ff"
_CYAN = "#00ffe5"
_GREEN = "#00ff9d"
_MUTED = "#2d5f7a"


class VoicePanel(QWidget):
    """Full voice interface panel: reactor orb + waveform + transcript log."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._listening = False
        self._build_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(16)

        # Left: reactor + orb + waveform
        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._reactor = ArcReactorWidget(size=130)
        self._reactor.set_state(ArcReactorWidget.IDLE)
        left.addWidget(self._reactor, alignment=Qt.AlignmentFlag.AlignCenter)
        left.addSpacing(12)

        self._state_label = QLabel("VOICE: IDLE")
        self._state_label.setStyleSheet(f"color:{_CYAN};font-size:10pt;letter-spacing:2px;")
        self._state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self._state_label)
        left.addSpacing(8)

        self._orb = VoiceOrbWidget()
        self._orb.setFixedSize(100, 100)
        left.addWidget(self._orb, alignment=Qt.AlignmentFlag.AlignCenter)
        left.addSpacing(8)

        self._waveform = WaveformWidget()
        left.addWidget(self._waveform)
        left.addSpacing(16)

        # Buttons
        btn_row = QHBoxLayout()
        self._start_btn = QPushButton("START LISTENING")
        self._start_btn.setStyleSheet(
            f"QPushButton{{background:rgba(0,255,229,0.12);border:1px solid {_CYAN};"
            f"color:{_CYAN};padding:8px 16px;}}"
        )
        self._start_btn.clicked.connect(self._toggle_listening)
        self._stop_btn = QPushButton("STOP")
        self._stop_btn.setStyleSheet(
            "QPushButton{background:rgba(255,58,58,0.1);border:1px solid #ff3a3a;"
            "color:#ff3a3a;padding:8px 16px;}"
        )
        self._stop_btn.clicked.connect(self._stop_listening)
        btn_row.addWidget(self._start_btn)
        btn_row.addWidget(self._stop_btn)
        left.addLayout(btn_row)
        left.addStretch()

        left_frame = QFrame()
        left_frame.setFixedWidth(280)
        left_frame.setStyleSheet(
            f"QFrame{{background:{_PANEL};border:1px solid rgba(0,200,255,0.18);border-radius:4px;}}"
        )
        left_frame.setLayout(left)
        root.addWidget(left_frame)

        # Right: transcript + command input
        right = QVBoxLayout()
        right.setSpacing(8)

        header = QLabel("TRANSCRIPT")
        header.setStyleSheet(f"color:{_MUTED};font-size:8pt;letter-spacing:2px;")
        right.addWidget(header)

        self._transcript = QTextEdit()
        self._transcript.setReadOnly(True)
        self._transcript.setStyleSheet(
            f"background:{_PANEL};border:1px solid rgba(0,200,255,0.18);"
            f"color:{_ACCENT};font-size:9pt;"
        )
        right.addWidget(self._transcript, stretch=1)

        # Command input
        cmd_row = QHBoxLayout()
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText('Type command or say "Hey C.I.P.H.E.R"...')
        self._cmd_input.returnPressed.connect(self._on_command)
        cmd_row.addWidget(self._cmd_input, stretch=1)
        send_btn = QPushButton("SEND")
        send_btn.clicked.connect(self._on_command)
        cmd_row.addWidget(send_btn)
        right.addLayout(cmd_row)

        # Wake phrase reminder
        hint = QLabel('Wake phrase: "Hey C.I.P.H.E.R" + your command')
        hint.setStyleSheet(f"color:{_MUTED};font-size:8pt;")
        right.addWidget(hint)

        root.addLayout(right, stretch=1)

    def _toggle_listening(self) -> None:
        self._listening = not self._listening
        self._apply_state("listening" if self._listening else "idle")

    def _stop_listening(self) -> None:
        self._listening = False
        self._apply_state("idle")

    def _apply_state(self, state: str) -> None:
        labels = {"idle": "VOICE: IDLE", "listening": "VOICE: LISTENING",
                  "processing": "VOICE: THINKING", "speaking": "VOICE: SPEAKING"}
        reactor_map = {"idle": ArcReactorWidget.IDLE, "listening": ArcReactorWidget.LISTENING,
                       "processing": ArcReactorWidget.PROCESSING, "speaking": ArcReactorWidget.SPEAKING}
        self._state_label.setText(labels.get(state, "VOICE: IDLE"))
        self._reactor.set_state(reactor_map.get(state, ArcReactorWidget.IDLE))
        self._orb.set_listening(state == "listening")
        self._waveform.set_active(state in ("listening", "speaking"))

    def _on_command(self) -> None:
        text = self._cmd_input.text().strip()
        if text:
            self._add_entry("ENGINEER", text)
            self._cmd_input.clear()
            self._add_entry("C.I.P.H.E.R", f'Processing: "{text}"')

    def _add_entry(self, speaker: str, text: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        color = _GREEN if speaker == "C.I.P.H.E.R" else _CYAN
        self._transcript.append(
            f'<span style="color:{_MUTED}">[{ts}]</span> '
            f'<span style="color:{color}">{speaker}:</span> '
            f'<span style="color:#b8e8ff">{text}</span>'
        )

    def set_state(self, state: str) -> None:
        self._apply_state(state)
