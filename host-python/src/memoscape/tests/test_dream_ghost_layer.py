"""Tests for GhostLayer place anchor → WorldAnchorCard."""
import time
import pytest
from memoscape.app.dream.ghost_layer import GhostLayer, GHOST_COOLDOWN_S
from memoscape.app.recall_context import RecallContext


def make_ctx(anchors=None, place="gym_001"):
    ctx = RecallContext()
    ctx.world_anchors = anchors
    ctx.place_signature = place
    return ctx


def test_no_output_without_anchors():
    gl = GhostLayer()
    ctx = make_ctx(anchors=None)
    assert gl.tick(ctx) is None


def test_no_output_with_empty_anchors():
    gl = GhostLayer()
    ctx = make_ctx(anchors=[])
    assert gl.tick(ctx) is None


def test_emits_world_anchor_card():
    gl = GhostLayer()
    ctx = make_ctx(anchors=[{"id": "a1", "summary": "Keys here", "place": "Gym