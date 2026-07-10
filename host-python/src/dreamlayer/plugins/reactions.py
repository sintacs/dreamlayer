"""plugins/reactions.py — HUD Reactions (cards + mesh).

Tap to throw a reaction — 🎉 👏 ❤️ 🔥 — onto your HUD, and if you're in a
GhostMode circle, everyone in it sees it too. Only the tiny symbol crosses the
mesh (never who, never where), so it stays within the "only feeling travels"
contract.

Demonstrates: a custom HUD card renderer + the `mesh` capability (emit/receive
a small gossip packet).
"""
from __future__ import annotations

from typing import Optional


# the closed set of reactions — a small symbol is all that crosses the wire
REACTIONS = {"party": "🎉", "clap": "👏", "love": "❤️", "fire": "🔥",
             "laugh": "😂", "wow": "😮"}
_MESH_KIND = "reaction"


def reaction_body(name: str) -> dict:
    """The mesh packet body for a reaction — just the symbol key."""
    key = name if name in REACTIONS else "party"
    return {"r": key}


def read_reaction(body: dict) -> Optional[str]:
    """The emoji from a received reaction packet, or None if unrecognised."""
    key = str((body or {}).get("r", ""))
    return REACTIONS.get(key)


class Reactions:
    """Live helper stashed on ctx.config so the host can fire reactions. Uses
    ctx.mesh lazily — nothing touches the mesh until you actually react."""

    def __init__(self, ctx):
        self._ctx = ctx

    def throw(self, name: str) -> dict:
        """Show a reaction locally and gossip it to the circle. Returns the HUD
        card (the host draws it); the mesh emit is best-effort."""
        emoji = REACTIONS.get(name, REACTIONS["party"])
        mesh = self._ctx.mesh
        if mesh is not None:
            try:
                mesh.emit(_MESH_KIND, reaction_body(name))
            except Exception:
                pass
        return {"type": "ReactionCard", "dismiss_ms": 1500, "emoji": emoji,
                "lines": [emoji], "mine": True}

    def received(self, wire: dict) -> Optional[dict]:
        """Fold in a peer's reaction (authenticated by the mesh) → a HUD card."""
        mesh = self._ctx.mesh
        if mesh is None:
            return None
        member = mesh.receive(wire)
        if member is None:
            return None
        emoji = read_reaction(wire.get("body", {}))
        if emoji is None:
            return None
        return {"type": "ReactionCard", "dismiss_ms": 1500, "emoji": emoji,
                "lines": [emoji], "mine": False}


def _draw_reaction_card(draw, card) -> None:
    """fn(draw, card): the emoji, large and centred."""
    try:
        draw.text((128, 128), str(card.get("emoji", "🎉")), anchor="mm",
                  fill=(255, 255, 255))
    except Exception:
        pass


class ReactionsPlugin:
    """API v2 plugin (lifecycle + events). register() wires the card + helper as
    v1; on receipt of a ``mesh`` event it folds a peer's reaction into a pending
    queue the host drains — reacting to a host moment through the supported event
    surface instead of the host having to poll the helper. Dogfoods on_event."""
    name = "hud-reactions"
    version = "0.1.0"
    requires = ("cards", "mesh")

    def __init__(self):
        self.helper: Optional[Reactions] = None
        self.pending: list = []            # received-reaction cards, host-drained

    def register(self, ctx):
        self.helper = Reactions(ctx)
        ctx.config["reactions"] = self.helper
        ctx.add_card_renderer("ReactionCard", _draw_reaction_card)

    def start(self, ctx):
        self.pending.clear()

    def stop(self):
        self.pending.clear()

    def on_event(self, kind: str, payload: dict) -> None:
        # a mesh packet arrived — if it's a reaction, queue a card for the host
        if kind != "mesh" or self.helper is None:
            return
        card = self.helper.received(payload or {})
        if card is not None:
            self.pending.append(card)


def reactions_plugin():
    """HUD Reactions as an API v2 plugin (lifecycle + events).
    requires=('cards','mesh')."""
    return ReactionsPlugin()
