#!/usr/bin/env python3
"""Regenerate real HUD-card store shots for the first-party *card* plugins,
rendered through the actual device renderer (dreamlayer.sdk.render_card).

A maintainer utility: run it to refresh the auto-generated previews. It writes
to --out (default landing/plugin-shots/generated/) and never overwrites the
curated marketing art in landing/plugin-shots/. Provider-only plugins
(currency, open-food-facts) have no card and are skipped.

    python scripts/gen_plugin_shots.py --shot
"""
from __future__ import annotations

import argparse
from pathlib import Path

# (registry name, factory import path, a sample card that shows it off)
CARD_PLUGINS = [
    ("filler-word-counter", "dreamlayer.plugins.filler:filler_plugin",
     {"type": "FillerCard", "count": 7}),
    ("hud-reactions", "dreamlayer.plugins.reactions:reactions_plugin",
     {"type": "ReactionCard", "emoji": "🔥"}),
    ("face-synth", "dreamlayer.plugins.face_synth:face_synth_plugin",
     {"type": "FaceSynthCard", "note": "C4"}),
    ("air-drums", "dreamlayer.plugins.air_drums:air_drums_plugin",
     {"type": "AirDrumCard", "drum": "kick"}),
]


def _factory(path: str):
    import importlib
    mod, _, attr = path.partition(":")
    return getattr(importlib.import_module(mod), attr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="landing/plugin-shots/generated",
                    help="output directory (default: landing/plugin-shots/generated)")
    ap.add_argument("--shot", action="store_true",
                    help="compose 640×340 store banners instead of 256px cards")
    args = ap.parse_args()

    from dreamlayer.sdk import render_card
    from dreamlayer.cli import _store_banner

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, path, card in CARD_PLUGINS:
        img = render_card(_factory(path)(), card)
        if args.shot:
            img = _store_banner(img)
        dest = out / f"{name}.png"
        img.save(dest)
        print(f"✓ {name} → {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
