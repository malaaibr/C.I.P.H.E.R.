"""Web interface — non-Qt event bus + FastAPI adapters for the VSCode VSIX surface."""

from cipher.interfaces.web.event_bridge import EventBridge, get_event_bridge

__all__ = ["EventBridge", "get_event_bridge"]
