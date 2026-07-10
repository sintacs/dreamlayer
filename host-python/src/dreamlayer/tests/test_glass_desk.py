"""test_glass_desk.py — the zero-hardware devkit (INNOVATION_SESSION 1.1): watch a
plugin dir and re-render its card through the real 256×256 device renderer, safe-
radius overlay included. `--once` is the CI-friendly single frame."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from dreamlayer import cli
from dreamlayer.simulator import glass_desk


def _scaffold(tmp_path):
    cli.main(["plugins", "new", "glass-demo", "--dir", str(tmp_path), "--author", "Ada"])
    return tmp_path / "glass-demo"


def test_render_glass_writes_a_256_device_png(tmp_path):
    d = _scaffold(tmp_path)
    out = glass_desk.render_glass(d)
    assert out.exists()
    assert Image.open(out).size == (256, 256)


def test_watch_once_renders_and_returns_path(tmp_path):
    d = _scaffold(tmp_path)
    out = tmp_path / "g.png"
    got = glass_desk.watch(d, out_path=str(out), once=True, log=lambda *_: None)
    assert Path(got) == out and out.exists()


def test_simulator_main_watch_once(tmp_path, capsys):
    d = _scaffold(tmp_path)
    from dreamlayer.simulator.server import main
    main(["--watch", str(d), "--once", "--out", str(tmp_path / "s.png")])
    assert (tmp_path / "s.png").exists()
    assert "Glass Desk rendered" in capsys.readouterr().out
