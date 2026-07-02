"""test_commitment_drift.py — tests for CommitmentDriftEngine."""
from __future__ import annotations
import time
import pytest
from dreamlayer.orchestrator.commitment_drift import CommitmentDriftEngine, _classify, _parse_due
from dreamlayer.memory.ring_buffer import SemanticRingBuffer
from dreamlayer.pipelines.ingest import MemoryEvent


def _ring_with_task(
    summary: str = "call dentist",
    confidence: float = 0.85,
    due: str = "2h",
    ts: float | None = None,
) -> SemanticRingBuffer:
    ring = SemanticRingBuffer(capacity=50)
    ts = ts if ts is not None else time.time()
    ring.append(
        MemoryEvent(
            kind="task",
            summary=summary,
            confidence=confidence,
            meta={"person": "Jordan", "task": summary, "due": due},
            source="passive",
            db_id=1,
        ),
        ts=ts,
    )
    return ring


class TestClassify:
    def test_blooming(self):  assert _classify(0.10) == "blooming"
    def test_healthy(self):   assert _classify(0.35) == "healthy"
    def test_drifting(self):  assert _classify(0.60) == "drifting"
    def test_cracking(self):  assert _classify(0.85) == "cracking"
    def test_shattered(self): assert _classify(1.00) == "shattered"


class TestParseDue:
    def test_hours(self):
        base = 0.0
        assert _parse_due("in 3h", base) == 3 * 3600

    def test_days(self):
        base = 0.0
        assert _parse_due("2d from now", base) == 2 * 86400

    def test_tomorrow(self):
        base = 0.0
        assert _parse_due("tomorrow morning", base) == 86400

    def test_none_returns_none(self):
        assert _parse_due(None, 0.0) is None
        assert _parse_due("", 0.0) is None


class TestDriftEngine:
    def test_no_alerts_before_threshold(self):
        base_ts = 1000.0
        ring = _ring_with_task(due="2h", ts=base_ts)
        engine = CommitmentDriftEngine(ring)
        # tick 30 s after creation — decay ~0.004, state=blooming
        alerts = engine.tick(now=base_ts + 30)
        assert alerts == []

    def test_cracking_fires_alert(self):
        base_ts = 1000.0
        ring = _ring_with_task(due="2h", ts=base_ts)
        engine = CommitmentDriftEngine(ring)
        # tick at 80% of the 2-h window → decay=0.80, state=cracking
        alerts = engine.tick(now=base_ts + 0.80 * 2 * 3600)
        assert len(alerts) == 1
        assert alerts[0].state == "cracking"

    def test_alert_fires_only_once(self):
        base_ts = 1000.0
        ring = _ring_with_task(due="2h", ts=base_ts)
        engine = CommitmentDriftEngine(ring)
        engine.tick(now=base_ts + 0.80 * 2 * 3600)  # first tick — fires
        alerts2 = engine.tick(now=base_ts + 0.90 * 2 * 3600)  # second tick — already surfaced
        assert alerts2 == []

    def test_shattered_uses_fallback_lifetime(self):
        """Without a due date, decay uses the 48-h fallback lifetime."""
        base_ts = 1000.0
        ring = _ring_with_task(due="", ts=base_ts)
        engine = CommitmentDriftEngine(ring)
        alerts = engine.tick(now=base_ts + 49 * 3600)  # past 48 h → shattered
        assert any(a.state == "shattered" for a in alerts)


class TestBehaviorDimension:
    """The other half of 'behavior and time': progress heals, keep blooms,
    break shatters, and neglect lets time pressure return."""

    def _cracking(self, base=1000.0):
        ring = _ring_with_task(summary="call dentist", due="2h", ts=base)
        eng = CommitmentDriftEngine(ring)
        eng.tick(now=base + 0.80 * 2 * 3600)     # decay 0.80 → cracking
        return ring, eng, base

    def test_nudge_heals_toward_bloom(self):
        _, eng, base = self._cracking()
        now = base + 0.80 * 2 * 3600
        eng.nudge("dentist", credit=0.5, now=now)
        eng.tick(now=now)
        rec = eng.all_records()[0]
        assert rec.decay == pytest.approx(0.30, abs=1e-6)   # 0.80 - 0.50
        assert rec.state == "healthy"                       # bloomed down

    def test_keep_blooms_and_pins(self):
        _, eng, base = self._cracking()
        eng.keep("dentist", now=base + 0.80 * 2 * 3600)
        # even far past the due date it stays kept, never shatters
        eng.tick(now=base + 10 * 3600)
        rec = eng.all_records()[0]
        assert rec.resolved == "kept"
        assert rec.state == "blooming" and rec.decay == 0.0

    def test_break_shatters_and_pins(self):
        _, eng, base = self._cracking()
        eng.break_("dentist", now=base + 0.30 * 2 * 3600)
        eng.tick(now=base + 0.31 * 2 * 3600)     # early, but broken is broken
        rec = eng.all_records()[0]
        assert rec.resolved == "broken" and rec.state == "shattered"

    def test_neglected_heal_credit_relaxes(self):
        """A nudge blooms it; stop tending and time pressure returns."""
        ring = _ring_with_task(summary="call dentist", due="6h", ts=1000.0)
        eng = CommitmentDriftEngine(ring)
        t_nudge = 1000.0 + 0.5 * 6 * 3600          # halfway → decay 0.50
        eng.nudge("dentist", credit=0.4, now=t_nudge)
        eng.tick(now=t_nudge)
        healed = eng.all_records()[0].decay        # 0.50 - 0.40 = 0.10
        # one half-life later, credit ~halves and the clock has advanced
        eng.tick(now=t_nudge + 6 * 3600)
        slipped = eng.all_records()[0].decay
        assert healed < 0.20                        # bloomed after the nudge
        assert slipped > healed                     # momentum bled away

    def test_re_alert_after_healing_then_slipping(self):
        ring = _ring_with_task(summary="call dentist", due="4h", ts=1000.0)
        eng = CommitmentDriftEngine(ring)
        crack_t = 1000.0 + 0.80 * 4 * 3600
        assert eng.tick(now=crack_t)                # first crack: alert fires
        eng.nudge("dentist", credit=0.5, now=crack_t)
        assert eng.tick(now=crack_t) == []          # healed out of alert
        # credit relaxes over the half-life while the deadline passes → it
        # slips back into an alert state and surfaces again
        again = eng.tick(now=1000.0 + 10 * 3600)
        assert any(a.state in ("cracking", "shattered") for a in again)

    def test_ambient_progress_from_the_stream(self):
        base = 1000.0
        ring = _ring_with_task(summary="send Marcus the contract",
                               due="2h", ts=base)
        # living near the promise: an event that plainly refers to it
        ring.append(MemoryEvent(kind="memory",
                                summary="emailed Marcus about the contract",
                                confidence=0.8),
                    ts=base + 600)
        eng = CommitmentDriftEngine(ring)
        eng.tick(now=base + 0.80 * 2 * 3600)
        rec = eng.all_records()[0]
        assert rec.progress > 0.0                   # the stream tended it
        assert rec.decay < 0.80                     # so it did not fully crack

    def test_private_events_are_never_observed(self):
        base = 1000.0
        ring = _ring_with_task(summary="send Marcus the contract",
                               due="2h", ts=base)
        ring.append(MemoryEvent(kind="memory",
                                summary="emailed Marcus about the contract",
                                confidence=0.8, meta={"private": True}),
                    ts=base + 600)
        eng = CommitmentDriftEngine(ring)
        eng.tick(now=base + 0.80 * 2 * 3600)
        assert eng.all_records()[0].progress == 0.0  # privacy is silence
