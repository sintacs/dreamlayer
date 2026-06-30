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


# ------------------------------------------------------------------ new cards

def commitment_drift(
    data,
    task: str = "",
    person: str = "",
    drift_state: str = "healthy",
    decay: float = 0.0,
    due: str = "",
    confidence: float | None = None,
) -> dict:
    """Card for an aging commitment with physics decay state."""
    if isinstance(data, dict):
        task        = _d(data, "task", ("summary", "primary"), task)
        person      = _d(data, "person", default=person)
        drift_state = data.get("drift_state", drift_state)
        decay       = data.get("decay", decay)
        due         = _d(data, "due", ("footer",), due)
        confidence  = data.get("confidence", confidence)

    _STATE_COLORS = {
        "blooming":  T.ACCENT_SUCCESS,
        "healthy":   T.ACCENT_MEMORY,
        "drifting":  T.CONFIDENCE_MED,
        "cracking":  T.WARNING_AMBER,
        "shattered": T.ACCENT_ERROR,
    }
    state_color = _STATE_COLORS.get(drift_state, T.TEXT_SECONDARY)

    return {
        "type":        "CommitmentDriftCard",
        "dismiss_ms":  4500,
        "task":        task,
        "person":      person,
        "drift_state": drift_state,
        "decay":       round(decay, 3),
        "due":         due,
        "primary":     task,
        "eyebrow":     drift_state.upper(),
        "footer":      due,
        "confidence":  confidence,
        "conf_color":  T.conf_color(confidence),
        "state_color": state_color,
        "lines":       [drift_state.upper(), task, due],
        "layout": {
            "eyebrow":    {"x": 128, "y": 64,  "size": "sm",   "color": state_color, "tracking": 3},
            "separator":  {"x1": 48, "x2": 208, "y": 80},
            "primary":    {"x": 128, "y": 112, "size": "hero", "color": T.TEXT_PRIMARY},
            "decay_bar":  {"x": 128, "y": 148, "fill": round(decay, 3), "color": state_color},
            "footer":     {"x": 128, "y": 168, "size": "sm",   "color": T.TEXT_GHOST},
        },
    }


def time_scrub_node(
    summary: str = "",
    kind: str = "object",
    ts_label: str = "",
    index: int = 0,
    total: int = 1,
    confidence: float | None = None,
) -> dict:
    """Card for a single node in the Time-Scrub Halo timeline."""
    return {
        "type":       "TimeScrubNodeCard",
        "dismiss_ms": 0,
        "index":      index,
        "total":      total,
        "kind":       kind,
        "summary":    summary,
        "primary":    summary,
        "ts_label":   ts_label,
        "footer":     ts_label,
        "confidence": confidence,
        "lines":      [summary, ts_label],
        "layout": {
            "progress": {"value": index / max(total - 1, 1)},
            "eyebrow":  {"x": 128, "y": 56,  "size": "sm",   "color": T.ACCENT_MEMORY, "tracking": 2},
            "primary":  {"x": 128, "y": 100, "size": "hero", "color": T.TEXT_PRIMARY},
            "footer":   {"x": 128, "y": 148, "size": "sm",   "color": T.TEXT_GHOST},
        },
    }


def deviation_alert(
    prior_summary: str = "",
    new_summary: str = "",
    score: float = 0.0,
    prior_confidence: float = 0.0,
    new_confidence: float = 0.0,
) -> dict:
    """Card surfaced by TellEngine when a transcript contradicts a promise baseline."""
    return {
        "type":             "DeviationAlertCard",
        "dismiss_ms":       5000,
        "score":            round(score, 3),
        "prior_summary":    prior_summary,
        "prior_confidence": prior_confidence,
        "new_summary":      new_summary,
        "new_confidence":   new_confidence,
        "primary":          new_summary,
        "eyebrow":          "Sounds different\u2026",
        "footer":           prior_summary,
        "lines":            ["Sounds different\u2026", new_summary, prior_summary],
        "layout": {
            "eyebrow":   {"x": 128, "y": 64,  "size": "sm",   "color": T.WARNING_AMBER, "tracking": 2},
            "separator": {"x1": 48, "x2": 208, "y": 80},
            "primary":   {"x": 128, "y": 108, "size": "md",   "color": T.TEXT_PRIMARY},
            "divider":   {"x1": 80, "x2": 176, "y": 132},
            "footer":    {"x": 128, "y": 156, "size": "sm",   "color": T.TEXT_GHOST},
            "score_dot": {"x": 128, "y": 178, "r": 4,         "color": T.ACCENT_ATTENTION},
        },
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
    "commitment_drift":  commitment_drift({
        "task":        "Send invoice",
        "person":      "Jordan",
        "drift_state": "cracking",
        "decay":       0.82,
        "due":         "Tomorrow before noon",
        "confidence":  0.78,
    }),
    "time_scrub_node":   time_scrub_node(
        summary="Keys at kitchen counter",
        kind="object",
        ts_label="09:42",
        index=2,
        total=7,
        confidence=0.91,
    ),
    "deviation_alert":   deviation_alert(
        prior_summary="I'll send the invoice tomorrow",
        new_summary="I never said I'd send anything",
        score=0.71,
        prior_confidence=0.80,
        new_confidence=0.85,
    ),
}
