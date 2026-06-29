from __future__ import annotations
import os
from .cards import ALL_SAMPLES
from .renderer import render
def export_all(out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, payload in ALL_SAMPLES.items():
        p = os.path.join(out_dir, f"{name}.png")
        render(payload).save(p)
        paths.append(p)
    return paths
