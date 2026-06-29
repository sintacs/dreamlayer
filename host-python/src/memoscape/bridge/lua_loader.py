from __future__ import annotations
import os
def collect_lua(lua_root: str) -> dict[str, str]:
    bundle: dict[str, str] = {}
    for root, _, files in os.walk(lua_root):
        for f in files:
            if f.endswith(".lua"):
                full = os.path.join(root, f)
                mod  = os.path.relpath(full, lua_root)
                bundle[mod] = open(full).read()
    if "main.lua" not in bundle:
        raise FileNotFoundError("main.lua missing — Halo requires it to autorun")
    return bundle
