"""Application-wide constants for the DevNex PyQt6 GUI — adapted from Int_Agent."""

from __future__ import annotations

APP_NAME      = "DevNex Assistant"
APP_VERSION   = "v1.0.0-MVP"
APP_SUBTITLE  = "V-Cycle Engine"

WIN_WIDTH,     WIN_HEIGHT     = 1320, 860
WIN_MIN_WIDTH, WIN_MIN_HEIGHT = 1100, 700

SIDEBAR_W = 240

STEP_LABELS = [
    "S1 LLD Gen",
    "S2 Code Link",
    "S3 LLD→Code",
    "S4 LLD→HLD",
    "S5 Full DS",
    "S6 Test Gen",
    "S7 UTD Gen",
    "S8 UTD→LLD",
    "S9 Full TR",
]

NAV_WORKFLOW = "Workflow"
NAV_TRACE    = "Trace"
NAV_OUTPUT   = "Output"
NAV_CONFIG   = "Config"
NAV_ITEMS    = [NAV_WORKFLOW, NAV_TRACE, NAV_OUTPUT, NAV_CONFIG]

ALL_NODE_IDS = [
    "S1N1", "S1N2", "S1N3", "S1N4",
    "S2N1", "S2N2",
    "S3N1", "S4N1", "S5N1",
    "S6N1", "S7N1", "S8N1", "S9N1",
]
