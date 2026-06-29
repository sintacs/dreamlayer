"""cards.py — Python card payload constructors.

Each function returns a plain dict that mirrors the Lua card descriptor.
The dict is serialised by real_bridge.py / emulator_bridge.py and consumed
by halo-lua/display/cards.lua on the device side.

All coordinates, sizes, and color tokens must match cards.lua exactly.
"""
from __future__ import annotations
from . import themes as T


def ready() -> dict:
    return {"type": "ReadyCard", "dismiss_ms": 0}


def saved_memory(label: str) -> dict:
    return {
        "type": "SavedMemoryCard",
        "dismiss_ms": 1200,
        "primary": label,
        "lines": [label],
    }


def query_listening() -> dict:
    return {"type": "QueryListeningCard", "dismiss_ms": 0}


def loading() -> dict:
    return {"type": "LoadingCard", "dismiss_ms": 0}


def object_recall(
    object_name: str,
    place: str,
    detail: str = "",
    last_seen: str = "",
    confidence: float | None = None,
) -> dict:
    if len(detail) > 18:
        detail = detail[:17] + "\u2026"
    return {
        "type": "ObjectRecallCard",
        "dismiss_ms": 3500,
        "primary": place,
        "object": object_name,
        "detail": detail,
        "last_seen": last_seen,
        "confidence": confidence,
        "conf_color": T.conf_color(confidence),
        # Layout spec (mirrors cards.lua pixel positions)
        "layout": {
            "eyebrow":   {"x": 128, "y": 76,  "size": "sm",   "color": T.ACCENT_MEMORY,  "tracking": 2},
            "separator": {"x1": 54, "x2": 202, "y": 92},
            "vbar":      {"x": 22, "y1": 104, "y2": 128, "w": 2, "color": T.ACCENT_MEMORY},
            "primary":   {"x": 128, "y": 116, "size": "hero", "color": T.TEXT_PRIMARY},
            "detail":    {"x": 128, "y": 148, "size": "md",   "color": T.TEXT_SECONDARY},
            "footer":    {"x": 128, "y": 173, "size": "sm",   "color": T.TEXT_GHOST},
            "conf_dot":  {"x": 128, "y": 196, "r": 3},
        },
    }


def commitment_recall(
    person: str,
    task: str,
    due: str = "",
    confidence: float | None = None,
) -> dict:
    return {
        "type": "CommitmentRecallCard",
        "dismiss_ms": 4000,
        "primary": task,
        "person": person,
        "due": due,
        "confidence": confidence,
        "conf_color": T.conf_color(confidence),
        "lines": [f"You promised {person}", task, due],
    }


def proactive_memory(
    summary: str,
    person: str | None = None,
    confidence: float | None = None,
) -> dict:
    return {
        "type": "ProactiveMemoryCard",
        "dismiss_ms": 3500,
        "primary": summary,
        "person": person,
        "confidence": confidence,
        "lines": [
            "Last time here",
            summary,
            *([f"With {person}"] if person else []),
        ],
    }


def person_context(
    person: str,
    headline: str = "",
    detail: str = "",
) -> dict:
    return {
        "type": "PersonContextCard",
        "dismiss_ms": 3500,
        "primary": person,
        "headline": headline,
        "detail": detail,
        "lines": [person, headline, detail],
    }


def privacy_paused() -> dict:
    return {
        "type": "PrivacyPausedCard",
        "dismiss_ms": 0,
        "primary": "Memory paused",
        "lines": ["Memory paused", "Nothing is being captured"],
    }


def error_card(msg: str = "Try again") -> dict:
    return {
        "type": "ErrorCard",
        "dismiss_ms": 4000,
        "primary": msg,
        "lines": ["Something went wrong", msg],
    }


def low_confidence() -> dict:
    return {
        "type": "LowConfidenceCard",
        "dismiss_ms": 3000,
        "primary": "Not sure",
        "lines": ["Not sure", "Try rephrasing"],
    }
