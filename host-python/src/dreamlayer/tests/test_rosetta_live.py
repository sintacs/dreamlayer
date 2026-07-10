"""test_rosetta_live.py — Rosetta Live (INNOVATION_SESSION 4.6): the "ear" half,
offline. Someone speaks Spanish; the English fades in as one subtitle card per
utterance. Veil-gated; the offline Argos backend is wired by default."""
from __future__ import annotations

from dreamlayer.main import build
from dreamlayer.rosetta import RosettaLens


def test_translate_heard_shows_the_translation():
    orch = build(":memory:")
    orch.rosetta = RosettaLens(translate_fn=lambda t, tgt: "hello, thanks",
                               engine="test")
    card = orch.translate_heard("hola, gracias", speaker="Maya")
    assert card["type"] == "SpokenCaptionCard"
    assert "hello" in card["primary"].lower()
    assert card["speaker"] == "Maya"


def test_same_language_passes_through():
    orch = build(":memory:")
    card = orch.translate_heard("hello there")     # en detected == target
    assert "hello there" in card["primary"].lower()


def test_translate_heard_is_veil_gated():
    orch = build(":memory:")
    orch.privacy.pause()
    assert orch.translate_heard("hola, gracias") is None


def test_argos_backend_is_wired_by_default():
    orch = build(":memory:")
    # the offline backend seam is attached (identity when argos isn't installed)
    assert orch.rosetta._engine == "argos"
