"""plugins/events.py — the typed, veil-gated event surface for plugins.

v1 plugins could only *register* at load time; they had no way to react to what
the wearer does. The event bus is that missing half: the host publishes typed
moments, a plugin subscribes to the kinds it declared capability for, and every
delivery is isolated (one bad subscriber never breaks a publish) and recorded to
the HealthLedger.

The Privacy Veil wins here too: while capture is paused, only ``veil`` events
flow — a plugin learns the doors shut, and nothing else. This mirrors the gate
every capture path already honours.

Kinds and the capability each subscription requires:

    card_shown   cards     a card became active on the glasses
    glance       glance    the wearer took a deliberate look
    place        ring      a known place came into context
    dream_enter  —         Dream Mode began
    dream_exit   —         Dream Mode ended
    veil         —         the Privacy Veil changed (always delivered)
    mesh         mesh      a Confluence/GhostMode mesh packet arrived
"""
from __future__ import annotations

KINDS = frozenset({
    "card_shown", "glance", "place",
    "dream_enter", "dream_exit", "veil", "mesh",
})

# kinds that require a declared capability to subscribe to; kinds not listed
# need none (but the veil gate still applies at publish time).
REQUIRED_CAP = {
    "card_shown": "cards",
    "glance": "glance",
    "place": "ring",
    "mesh": "mesh",
}

# while the Veil is down, only these kinds are delivered.
VEIL_ALLOWED = frozenset({"veil"})


class PluginEventBus:
    """Publish/subscribe over the fixed KINDS. `veil` is an object with
    ``allow_capture()`` (the PrivacyGate); `health` is an optional
    HealthLedger for isolating and recording subscriber failures."""

    def __init__(self, veil=None, health=None, caplog=None):
        self._veil = veil
        self._health = health
        self._caplog = caplog          # CapabilityLedger — records each delivery
        self._subs: dict[str, list] = {k: [] for k in KINDS}

    # -- subscription (called via PluginContext.subscribe) -------------------

    def subscribe(self, kind: str, fn, plugin_name: str = "") -> bool:
        if kind not in KINDS:
            return False
        self._subs[kind].append((plugin_name, fn))
        return True

    def unsubscribe_plugin(self, plugin_name: str) -> None:
        """Drop every subscription a plugin holds (on stop/reload)."""
        for kind in self._subs:
            self._subs[kind] = [(n, f) for (n, f) in self._subs[kind]
                                if n != plugin_name]

    # -- publish (called by the orchestrator at each moment) -----------------

    def _veiled(self) -> bool:
        v = self._veil
        return bool(v is not None and hasattr(v, "allow_capture")
                    and not v.allow_capture())

    def publish(self, kind: str, payload: dict | None = None) -> int:
        """Deliver to every subscriber of `kind`. Returns how many ran.
        Veil-gated: while paused, only VEIL_ALLOWED kinds are delivered."""
        if kind not in self._subs:
            return 0
        if self._veiled() and kind not in VEIL_ALLOWED:
            return 0
        data = payload or {}
        n = 0
        for name, fn in list(self._subs[kind]):
            try:
                fn(kind, data)
                n += 1
                if self._caplog is not None:       # transparency: host routed a kind here
                    self._caplog.record(name, f"event:{kind}")
            except Exception as exc:               # never let a plugin break a publish
                if self._health is not None:
                    self._health.record_failure(f"plugin:{name}", exc)
        return n

    def subscriber_count(self, kind: str) -> int:
        return len(self._subs.get(kind, ()))
