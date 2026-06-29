
"""cards.py — Python card payload constructors."""
from __future__ import annotations
from . import themes as T


def _d(data, key, alt_keys=(), default=""):
    if isinstance(data, dict):
        for k in (key, *alt_keys):
            if k in data and data[k] is not None:
                return data[k]
    return default


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
    data,
    place: str = "",
    detail: str = "",
    last_seen: str = "",
    confidence: float | None = None,
) -> dict:
    if isinstance(data, dict):
        object_name = _d(data, "object", ("name", "summary"))
        place       = _d(data, "place", ("location",), place)
        detail      = _d(data, "detail", ("near",), detail)
        last_seen   = _d(data, "last_seen", ("footer",), last_seen)
        confidence  = data.get("confidence", confidence)
    else:
        object_name = data

    if len(detail) > 18:
        detail = detail[:17] + "\u2026"

    return {
        "type":       "ObjectRecallCard",
        "dismiss_ms": 3500,
        "object":     object_name,
        "primary":    object_name,
        "place":      place,
        "detail":     detail,
        "last_seen":  last_seen,
        "footer":     last_seen,
        "confidence": confidence,
        "conf_color": T.conf_color(confidence),
        "lines":      [object_name, place, detail, last_seen],
        "layout": {
            "eyebrow":   {"x": 128, "y": 72,  "size": "sm",   "color": T.ACCENT_MEMORY, "tracking": 2},
            "separator": {"x1": 48, "x2": 208, "y": 86},
            "vbar":      {"x": 20, "y1": 98, "y2": 130, "w": 2, "color": T.MEMORY_RAIL},
            "primary":   {"x": 128, "y": 114, "size": "hero", "color": T.TEXT_PRIMARY},
            "detail":    {"x": 128, "y": 146, "size": "md",   "color": T.TEXT_SECONDARY},
            "footer":    {"x": 128, "y": 170, "size": "sm",   "color": T.TEXT_GHOST},
            "conf_dot":  {"x": 128, "y": 192, "r": 3},
        },
    }


def commitment_recall(
    data,
    task: str = "",
    due: str = "",
    confidence: float | None = None,
) -> dict:
    if isinstance(data, dict):
        person     = _d(data, "person")
        task       = _d(data, "task", ("primary",), task)
        due        = _d(data, "due", ("footer",), due)
        confidence = data.get("confidence", confidence)
    else:
        person = data

    return {
        "type":       "CommitmentRecallCard",
        "dismiss_ms": 4000,
        "person":     person,
        "primary":    task,
        "eyebrow":    f"You promised {person}",
        "due":        due,
        "footer":     due,
        "confidence": confidence,
        "conf_color": T.conf_color(confidence),
        "lines":      [f"You promised {person}", task, due],
    }


def proactive_memory(
    data,
    person: str | None = None,
    confidence: float | None = None,
) -> dict:
    if isinstance(data, dict):
        summary    = _d(data, "summary", ("primary",))
        person     = data.get("person", person)
        confidence = data.get("confidence", confidence)
    else:
        summary = data

    footer = f"With {person}" if person else None
    payload: dict = {
        "type":       "ProactiveMemoryCard",
        "dismiss_ms": 3500,
        "primary":    summary,
        "person":     person,
        "confidence": confidence,
        "lines":      ["Last time here", summary, *([f"With {person}"] if person else [])],
    }
    if footer is not None:
        payload["footer"] = footer
    return payload


def person_context(person: str, headline: str = "", detail: str = "") -> dict:
    return {
        "type":     "PersonContextCard",
        "dismiss_ms": 3500,
        "primary":  person,
        "headline": headline,
        "detail":   detail,
        "lines":    [person, headline, detail],
    }


def privacy_paused() -> dict:
    return {
        "type":     "PrivacyPausedCard",
        "dismiss_ms": 0,
        "primary":  "Memory paused",
        "lines":    ["Memory paused", "Nothing is being captured"],
    }


def error_card(msg: str = "Try again") -> dict:
    return {
        "type":       "ErrorCard",
        "dismiss_ms": 4000,
        "primary":    msg,
        "lines":      ["Connection issue", msg],
    }


error = error_card


def low_confidence() -> dict:
    return {
        "type":       "LowConfidenceCard",
        "dismiss_ms": 3000,
        "primary":    "Not sure",
        "confidence": 0.0,
        "lines":      ["Not sure", "Try rephrasing"],
    }


ALL_SAMPLES: dict[str, dict] = {
    "ready":             ready(),
    "saved_memory":      saved_memory("House keys"),
    "query_listening":   query_listening(),
    "loading":           loading(),
    "object_recall":     object_recall({
        "object":     "Keys",
        "place":      "Kitchen table",
        "detail":     "Beside blue notebook",
        "last_seen":  "Last seen 7:42 PM",
        "confidence": 0.88,
    }),
    "commitment_recall": commitment_recall({
        "person":     "Jordan",
        "task":       "Send the invoice",
        "due":        "Tomorrow before noon",
        "confidence": 0.72,
    }),
    "proactive_memory":  proactive_memory({
        "summary":    "You discussed the invoice",
        "person":     "Jordan",
        "confidence": 0.70,
    }),
    "person_context":    person_context(
        "Jordan", headline="Sent invoice Wed", detail="Last seen today"
    ),
    "privacy_paused":    privacy_paused(),
    "error":             error_card("BLE timeout"),
    "low_confidence":    low_confidence(),
}
