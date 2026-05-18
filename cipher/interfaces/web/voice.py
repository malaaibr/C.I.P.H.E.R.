"""
Local voice backends — lightweight, no network, no model server.

TTS: pyttsx3 (Windows: SAPI5; macOS: NSSpeechSynthesizer; Linux: espeak).
     Tiny dep, no model download.

STT: faster-whisper. Pulls `tiny.en` (~75 MB) on first call into the system
     HF cache. Real local transcription; no API key.

Both are LAZY: missing package raises a 503 with the exact pip command to fix it.
"""

from __future__ import annotations

import io
import logging
import threading
from typing import Any

log = logging.getLogger(__name__)

# Module-global cached singletons (heavy init, reuse across calls).
_tts_engine_lock = threading.Lock()
_tts_engine: Any | None = None

_stt_model_lock = threading.Lock()
_stt_model: Any | None = None
_STT_MODEL_NAME = "tiny.en"  # 75MB; balance speed vs accuracy for MVP demo


class VoiceBackendUnavailable(RuntimeError):
    """Raised when an optional voice dependency is not installed."""


# ── TTS ────────────────────────────────────────────────────────────────────────

def speak(text: str) -> dict:
    """Synthesize speech and play on the host's speaker. Returns metadata only."""
    try:
        import pyttsx3  # type: ignore
    except ImportError as e:
        raise VoiceBackendUnavailable(
            "pyttsx3 not installed. Run: pip install pyttsx3"
        ) from e

    global _tts_engine
    with _tts_engine_lock:
        if _tts_engine is None:
            _tts_engine = pyttsx3.init()
        _tts_engine.say(text)
        _tts_engine.runAndWait()
    return {"ok": True, "chars": len(text), "backend": "pyttsx3"}


# ── STT ────────────────────────────────────────────────────────────────────────

def transcribe(audio_bytes: bytes, *, language: str = "en") -> dict:
    """Transcribe raw audio bytes (webm/opus, wav, mp3 — anything ffmpeg reads)."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise VoiceBackendUnavailable(
            "faster-whisper not installed. Run: pip install faster-whisper"
        ) from e

    global _stt_model
    with _stt_model_lock:
        if _stt_model is None:
            log.info("Loading faster-whisper model %s (one-time download on first run)", _STT_MODEL_NAME)
            _stt_model = WhisperModel(_STT_MODEL_NAME, device="cpu", compute_type="int8")

    # faster-whisper accepts a file-like object.
    segments, info = _stt_model.transcribe(
        io.BytesIO(audio_bytes),
        language=language,
        beam_size=1,
        vad_filter=True,
    )
    text_parts = []
    for seg in segments:
        text_parts.append(seg.text)
    full_text = " ".join(s.strip() for s in text_parts).strip()
    return {
        "ok": True,
        "text": full_text,
        "language": info.language,
        "duration_s": round(info.duration, 2),
        "backend": f"faster-whisper:{_STT_MODEL_NAME}",
    }
