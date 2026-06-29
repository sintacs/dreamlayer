from memoscape.simulator import scenarios
from memoscape.memory.privacy import PrivacyGate

def test_pause_blocks_capture():
    orch, blocked = scenarios.privacy_pause()
    assert orch.privacy.paused is True
    assert blocked is None

def test_gate_logic():
    g = PrivacyGate()
    assert g.allow_capture() is True
    g.pause(); assert g.allow_capture() is False
    g.resume(); assert g.allow_capture() is True

def test_paused_card_renders():
    orch, _ = scenarios.privacy_pause()
    assert orch.bridge.last_card["type"] == "PrivacyPausedCard"

def test_paused_card_text():
    orch, _ = scenarios.privacy_pause()
    c = orch.bridge.last_card
    assert c["primary"] == "Memory paused"
    assert "Nothing is being captured" in c["lines"]

def test_resume_allows_capture_again():
    orch, blocked, saved = scenarios.resume_after_pause()
    assert blocked is None
    assert saved is not None

def test_emulator_refuses_content_while_paused():
    from memoscape.bridge.emulator_bridge import EmulatorBridge
    b = EmulatorBridge(); b.connect()
    b.inject_event("privacy_pause")
    b.send_card({"type": "ObjectRecallCard", "primary": "Keys"})
    assert b.last_card["type"] == "PrivacyPausedCard"
