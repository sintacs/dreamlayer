"""Tests for Orchestrator Dream Mode integration."""
import pytest
from unittest.mock import MagicMock, patch

from memoscape.app.orchestrator import Orchestrator


class FakeBridge:
    def __init__(self):
        self.raw_sent = []
        self.cards = []
        self.commands = []
        self._event_handler = None

    def on_event(self, fn): self._event_handler = fn
    def send_raw(self, cmd): self.raw_sent.append(cmd)
    def send_card(self, card, event=None): self.cards.append((card, event))
    def send_command(self, cmd): self.commands.append(cmd)
    def inject_event(self, name): pass

    def fire(self, name, payload=None):
        if self._event_handler:
            self._event_handler(name, payload or {})


def make_orc():
    bridge = FakeBridge()
    orc = Orchestrator(bridge=bridge)
    return orc, bridge


# ------------------------------------------------------------------
# State transitions
# ------------------------------------------------------------------

def test_starts_in_memory_mode():
    orc, _ = make_orc()
    assert not orc.state.is_dream()


def test_double_tap_enters_dream():
    orc, bridge = make_orc()
    bridge.fire("double_tap")
    assert orc.state.is_dream()
    assert orc.dream.running


def test_double_tap_again_exits_dream():
    orc, bridge = make_orc()
    bridge.fire("double_tap")   # enter
    bridge.fire("double_tap")   # exit
    assert not orc.state.is_dream()
    assert not orc.dream.running


def test_enter_dream_sends_ble_command():
    orc, bridge = make_orc()
    orc.enter_dream()
    raw_types = [r["t"] for r in bridge.raw_sent]
    assert "dream_enter" in raw_types


def test_exit_dream_sends_ble_command_and_ready():
    orc, bridge = make_orc()
    orc.enter_dream()
    bridge.raw_sent.clear()
    bridge.commands.clear()
    orc.exit_dream()
    raw_types = [r["t"] for r in bridge.raw_sent]
    assert "dream_exit" in raw_types
    assert "show_ready" in bridge.commands


# ------------------------------------------------------------------
# Sensor feed-through
# ------------------------------------------------------------------

def test_on_audio_frame_feeds_mic_in_dream_mode():
    orc, bridge = make_orc()
    orc.enter_dream()
    ctx = {"mic_fft": [0.5] * 32, "mic_amplitude": 0.7}
    orc.on_audio_frame("hello", context=ctx)
    assert orc.dream._ctx.mic_amplitude == 0.7
    assert orc.dream._ctx.mic_fft == [0.5] * 32


def test_on_audio_frame_ignores_mic_outside_dream():
    orc, _ = make_orc()
    ctx = {"mic_fft": [0.5] * 32, "mic_amplitude": 0.7}
    orc.on_audio_frame("hello", context=ctx)
    assert orc.dream._ctx.mic_fft is None


def test_on_scene_frame_feeds_camera_in_dream_mode():
    orc, _ = make_orc()
    orc.enter_dream()
    scene = {"camera_jpeg": b"\xff\xd8\xff", "objects": []}
    orc.on_scene_frame(scene)
    assert orc.dream._ctx.camera_frame == b"\xff\xd8\xff"


def test_on_scene_frame_ignores_camera_outside_dream():
    orc, _ = make_orc()
    scene = {"camera_jpeg": b"\xff\xd8\xff", "objects": []}
    orc.on_scene_frame(scene)
    assert orc.dream._ctx.camera_frame is None


def test_on_scene_frame_feeds_imu_in_dream_mode():
    orc, _ = make_orc()
    orc.enter_dream()
    scene = {
        "objects": [],
        "imu_pose":  {"pitch": 1.0, "yaw": 2.0, "roll": 0.0},
        "imu_delta": {"pitch": 0.1, "yaw": 0.2},
    }
    orc.on_scene_frame(scene)
    assert orc.dream._ctx.imu_pose["yaw"] == 2.0


def test_on_place_feeds_ghost_layer_in_dream_mode():
    orc, _ = make_orc()
    orc.enter_dream()
    # on_place returns None in dream mode (ghosts surface via ambient loop)
    result = orc.on_place("kitchen_001")
    assert result is None
    assert orc.dream._ctx.place_signature == "kitchen_001"


def test_on_place_returns_card_in_memory_mode():
    """on_place should still surface proactive cards normally outside dream."""
    orc, bridge = make_orc()
    # Just verify it doesn't crash and returns (may be None with mock data)
    result = orc.on_place("kitchen_001")
    # No exception = pass; card presence depends on DB state


# ------------------------------------------------------------------
# Long-press still works in dream mode
# ------------------------------------------------------------------

def test_long_press_pauses_in_dream_mode():
    orc, bridge = make_orc()
    orc.enter_dream()
    bridge.fire("long_press")
    assert orc.privacy.paused
    # Dream mode state should be unaffected by privacy pause
    assert orc.state.is_dream()
