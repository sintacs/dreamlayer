"""Glass Desk — the zero-hardware devkit (INNOVATION_SESSION 1.1).

Watch a plugin directory and re-render its HUD card through the *real* 256×256
device renderer the moment you save — the same pixels the glasses draw, with the
112px safe-radius circle overlaid, no hardware and no flashing. Reuses the render
path (sdk.render_card) and the folder watcher (orchestrator/fs_watch); `--once`
renders a single frame for CI.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

# The device display: 256×256, center (128,128), safe drawing radius 112px.
DISPLAY = 256
CENTER = 128
SAFE_RADIUS = 112


def render_glass(plugin_dir: str | Path, out_path: str | Path | None = None,
                 card: Optional[dict] = None):
    """Render the plugin's card through the real renderer, overlay the safe-radius
    circle, and write a PNG. Returns the output Path."""
    from PIL import ImageDraw

    from ..sdk import package_from_dir, render_card

    d = Path(plugin_dir)
    pkg = package_from_dir(d)
    img = render_card(pkg, card).convert("RGB")

    draw = ImageDraw.Draw(img)
    # the safe-radius ring the design system holds content inside
    draw.ellipse([CENTER - SAFE_RADIUS, CENTER - SAFE_RADIUS,
                  CENTER + SAFE_RADIUS, CENTER + SAFE_RADIUS],
                 outline=(48, 64, 84))

    out = Path(out_path) if out_path else d / ".glass" / "glass.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def watch(plugin_dir: str | Path, out_path: str | Path | None = None,
          card: Optional[dict] = None, interval: float = 1.0,
          once: bool = False, log: Callable[[str], None] = print) -> Path:
    """Render now, then re-render on every save until interrupted. Uses the
    watchdog folder watcher when present, else polls plugin.py/plugin.json."""
    d = Path(plugin_dir)
    out = Path(out_path) if out_path else d / ".glass" / "glass.png"

    def _render() -> None:
        try:
            p = render_glass(d, out, card)
            log(f"✓ glass rendered → {p}")
        except Exception as exc:                       # keep the loop alive
            log(f"✗ {exc}")

    _render()
    if once:
        return out

    log(f"◐ watching {d} — save plugin.py/plugin.json to re-render (Ctrl-C to stop)")
    try:
        from ..orchestrator.fs_watch import FolderWatcher
        fw = FolderWatcher(str(d), lambda *_: _render())
        if fw.start():
            try:
                while True:
                    time.sleep(0.5)
            finally:
                fw.stop()
            return out
    except Exception:
        pass  # fall through to polling

    # polling fallback — mtimes of the two source files
    watched = [d / "plugin.py", d / "plugin.json"]

    def _sig():
        return tuple(f.stat().st_mtime if f.exists() else 0 for f in watched)

    last = _sig()
    while True:
        time.sleep(max(0.1, interval))
        cur = _sig()
        if cur != last:
            last = cur
            _render()
    return out
