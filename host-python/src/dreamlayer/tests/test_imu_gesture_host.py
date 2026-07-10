"""test_imu_gesture_host.py — Nod to Remember, host half. The on-glass IMU
classifier fires a gesture; the host turns your neck into the save button
(NOD_SAVE pins the newest sighting; SHAKE_DISMISS feeds the dismissal trust
signal). Nothing is filmed — a pinned memory is one text row."""
from __future__ import annotations

from dreamlayer.main import build
from dreamlayer.pipelines.ingest import MemoryEvent


def _pinned(orch):
    return orch.db.conn.execute(
        "SELECT summary FROM memories WHERE json_extract(meta,'$.pinned')=1"
    ).fetchall()


def test_nod_save_pins_the_newest_ring_memory():
    orch = build(":memory:")
    orch.ring.append(MemoryEvent(kind="object", summary="keys on kitchen counter",
                                 confidence=0.8))
    orch._on_event("imu_gesture", {"gesture": "NOD_SAVE", "confidence": 0.9})
    rows = _pinned(orch)
    assert len(rows) == 1 and "keys" in rows[0][0]


def test_nod_save_with_empty_ring_is_safe():
    orch = build(":memory:")
    assert orch.on_imu_gesture("NOD_SAVE")["pinned"] is False
    assert _pinned(orch) == []


def test_shake_dismiss_feeds_the_trust_signal():
    orch = build(":memory:")
    seen = []
    orch.maturity.observe_card = lambda dismissed, now=None: seen.append(dismissed)
    out = orch.on_imu_gesture("SHAKE_DISMISS")
    assert out["dismissed"] is True and seen == [True]


def test_peek_and_double_nod_surface_as_intents():
    orch = build(":memory:")
    assert orch.on_imu_gesture("GLANCE_PEEK")["gesture"] == "GLANCE_PEEK"
    assert orch.on_imu_gesture("DOUBLE_NOD")["gesture"] == "DOUBLE_NOD"


def test_unknown_gesture_is_ignored_not_crashed():
    orch = build(":memory:")
    assert orch.on_imu_gesture("WOBBLE")["ignored"] is True


# --- figment grammar: scenes may transition on IMU gestures (5.1 #1) ---------

def test_figment_grammar_accepts_imu_gesture_events():
    from dreamlayer.reality_compiler.v2.figment import _valid_event
    for g in ("nod", "shake", "peek", "tilt", "double_nod"):
        assert _valid_event(f"imu:{g}") is True
    assert _valid_event("imu:bogus") is False
    assert _valid_event("imu:") is False
