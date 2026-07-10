"""test_figment_events.py — the figment event grammar (INNOVATION_SESSION 5.1).
`_valid_event` is the predicate budgets.verify() enforces (budgets.py:174), so
these govern what transitions a figment may declare and still pass the gate."""
from __future__ import annotations

from dreamlayer.reality_compiler.v2.figment import _valid_event


def test_place_events():
    assert _valid_event("place:enter")
    assert _valid_event("place:exit")
    assert not _valid_event("place:teleport")


def test_bond_presence_events():
    assert _valid_event("bond:near")
    assert not _valid_event("bond:far")


def test_bond_tag_events():
    assert _valid_event("bond:tag:dinner")
    assert _valid_event("bond:tag:pom")
    assert not _valid_event("bond:tag:")               # empty tag
    assert not _valid_event("bond:tag:with space")     # non-alnum
    assert not _valid_event("bond:tag:" + "x" * 17)    # too long


def test_gesture_and_base_events_still_valid():
    for e in ("single", "double", "long", "ble:5", "imu:nod",
              "text", "battery_low"):
        assert _valid_event(e), e


def test_unknown_prefix_rejected():
    assert not _valid_event("gps:enter")
    assert not _valid_event("place:")
    assert not _valid_event("bond:")
