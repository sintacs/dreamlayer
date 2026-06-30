"""test_ingest_llm.py — tests for the GPT-4o-mini tier-3 extraction path.

All tests mock openai.OpenAI so no real API key or network needed in CI.
"""
from __future__ import annotations
import json
from unittest.mock import MagicMock, patch
import pytest

from memoscape.memory.db import MemoryDB
from memoscape.pipelines.ingest import IngestPipeline, MemoryEvent
from memoscape.pipelines.llm_client import LLMClient
from memoscape.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_openai_response(events: list[dict]) -> MagicMock:
    """Build a mock openai ChatCompletion response."""
    content = json.dumps({"events": events})
    choice  = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def cfg():
    c = Config()
    c.openai_api_key = "sk-test-fake-key"
    c.llm_confidence_threshold = 0.60
    c.llm_word_threshold = 40
    return c


@pytest.fixture
def db():
    return MemoryDB(":memory:")


# ---------------------------------------------------------------------------
# LLMClient unit tests
# ---------------------------------------------------------------------------

class TestLLMClient:
    def test_returns_memory_events(self, cfg):
        client = LLMClient(cfg)
        mock_resp = _make_openai_response([{
            "kind": "object",
            "summary": "Passport is in the safe",
            "confidence": 0.95,
            "meta": {"object": "passport", "place": "safe"},
        }])
        with patch("openai.OpenAI") as MockOAI:
            MockOAI.return_value.chat.completions.create.return_value = mock_resp
            events = client.extract("My passport is in the safe.")
        assert len(events) == 1
        assert events[0].kind == "object"
        assert events[0].source == "llm"
        assert events[0].confidence == 0.95

    def test_invalid_kind_skipped(self, cfg):
        client = LLMClient(cfg)
        mock_resp = _make_openai_response([{
            "kind": "nonsense",
            "summary": "Whatever",
            "confidence": 0.8,
            "meta": {},
        }])
        with patch("openai.OpenAI") as MockOAI:
            MockOAI.return_value.chat.completions.create.return_value = mock_resp
            events = client.extract("Whatever.")
        assert events == []

    def test_api_error_returns_empty(self, cfg):
        client = LLMClient(cfg)
        with patch("openai.OpenAI") as MockOAI:
            MockOAI.return_value.chat.completions.create.side_effect = RuntimeError("timeout")
            events = client.extract("Some transcript.")
        assert events == []  # fallback, no exception raised

    def test_missing_api_key_returns_empty(self):
        cfg = Config()
        cfg.openai_api_key = ""  # explicitly empty
        client = LLMClient(cfg)
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            events = client.extract("I left my glasses on the table.")
        assert events == []

    def test_context_location_sent_in_user_message(self, cfg):
        """Verify location hint is included in the user message."""
        client = LLMClient(cfg)
        captured = {}
        mock_resp = _make_openai_response([])

        def fake_create(**kwargs):
            captured["messages"] = kwargs["messages"]
            return mock_resp

        with patch("openai.OpenAI") as MockOAI:
            MockOAI.return_value.chat.completions.create.side_effect = fake_create
            client.extract("Glasses on the table.", context={"location": "bedroom"})

        user_msg = captured["messages"][1]["content"]
        assert "bedroom" in user_msg


# ---------------------------------------------------------------------------
# IngestPipeline tier-3 trigger logic
# ---------------------------------------------------------------------------

class TestTier3Trigger:
    def _pipeline_with_mock_llm(self, db, cfg, llm_events: list[dict]) -> IngestPipeline:
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.extract.return_value = [
            MemoryEvent(
                kind=e["kind"], summary=e["summary"],
                confidence=e.get("confidence", 0.80), source="llm",
                meta=e.get("meta", {}),
            )
            for e in llm_events
        ]
        return IngestPipeline(
            db=db, use_spacy=False, llm=mock_llm,
            llm_confidence_threshold=cfg.llm_confidence_threshold,
            llm_word_threshold=cfg.llm_word_threshold,
        )

    def test_llm_triggered_on_long_transcript(self, db, cfg):
        long_tx = ("word " * 45).strip()  # 45 words > threshold of 40
        pipeline = self._pipeline_with_mock_llm(db, cfg, [{
            "kind": "task", "summary": "Task: do something", "confidence": 0.80
        }])
        events = pipeline.ingest(long_tx)
        # LLM mock was called
        pipeline.llm.extract.assert_called_once()

    def test_llm_not_triggered_on_short_high_confidence(self, db, cfg):
        pipeline = self._pipeline_with_mock_llm(db, cfg, [])
        # Short transcript, tier-1 will produce high-confidence events
        pipeline.ingest("I left my keys on the kitchen counter.")
        pipeline.llm.extract.assert_not_called()

    def test_llm_triggered_when_zero_tier1_events(self, db, cfg):
        pipeline = self._pipeline_with_mock_llm(db, cfg, [{
            "kind": "task", "summary": "Task: call dentist", "confidence": 0.80
        }])
        # Transcript that tier-1 won't match but is non-trivial
        pipeline.ingest("Might be worth thinking about the dentist visit.")
        pipeline.llm.extract.assert_called_once()

    def test_llm_events_merged_and_deduped(self, db, cfg):
        # Tier-1 produces an object event; LLM returns same summary — should dedup
        llm_event = {
            "kind": "object",
            "summary": "my keys → kitchen counter",
            "confidence": 0.95,
        }
        pipeline = self._pipeline_with_mock_llm(db, cfg, [llm_event])
        events = pipeline.ingest("I left my keys on the kitchen counter.")
        obj_summaries = [e.summary for e in events if e.kind == "object"]
        # After dedup, no duplicate summaries
        assert len(obj_summaries) == len(set(obj_summaries))

    def test_all_events_have_db_id(self, db, cfg):
        pipeline = self._pipeline_with_mock_llm(db, cfg, [{
            "kind": "person",
            "summary": "Person: Jordan",
            "confidence": 0.90,
            "meta": {"person": "Jordan"},
        }])
        events = pipeline.ingest(
            "Met Jordan at the conference. I'll follow up with her by Monday."
        )
        assert events
        assert all(e.db_id > 0 for e in events)

    def test_llm_failure_falls_back_to_tier1(self, db, cfg):
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.extract.return_value = []  # simulate API failure returning empty
        pipeline = IngestPipeline(
            db=db, use_spacy=False, llm=mock_llm,
            llm_confidence_threshold=0.99,  # force trigger
            llm_word_threshold=0,
        )
        events = pipeline.ingest("I left my keys on the counter.")
        # Tier-1 object events should still be present
        assert any(e.kind == "object" for e in events)
        assert all(e.db_id > 0 for e in events)


# ---------------------------------------------------------------------------
# with_llm constructor
# ---------------------------------------------------------------------------

class TestWithLLMConstructor:
    def test_constructs_pipeline_with_llm(self, db, cfg):
        pipeline = IngestPipeline.with_llm(db, cfg, use_spacy=False)
        assert pipeline.llm is not None
        assert pipeline.llm_confidence_threshold == cfg.llm_confidence_threshold
        assert pipeline.llm_word_threshold == cfg.llm_word_threshold

    def test_config_values_propagated(self, db):
        cfg = Config()
        cfg.openai_api_key   = "sk-test"
        cfg.llm_confidence_threshold = 0.50
        cfg.llm_word_threshold       = 25
        pipeline = IngestPipeline.with_llm(db, cfg, use_spacy=False)
        assert pipeline.llm_confidence_threshold == 0.50
        assert pipeline.llm_word_threshold == 25
