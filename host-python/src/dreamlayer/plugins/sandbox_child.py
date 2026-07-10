"""plugins/sandbox_child.py — the untrusted-plugin worker process.

Run as ``python -m dreamlayer.plugins.sandbox_child`` with the package directory
on argv. This is the *other side of the jail*: an unreviewed third-party plugin
is exec'd HERE, in a child process, never in the host. The child registers the
plugin against a recording ``ProxyContext`` and then serves JSON-lines RPCs on
stdin/stdout.

Only pure request→data extension points cross the boundary — **object providers**
(``matches``/``build`` → panel rows) and **shop providers** (``fn(label, attrs)``
→ dict). Anything with host-side side effects (card renderers that draw, glance
candidates that fire actions, perceptors, brain tiers) cannot be safely proxied
across a process and is reported as *rejected* so the host can refuse the plugin
for isolated loading. That refusal is the security guarantee, not a limitation to
apologise for.

Protocol (one JSON object per line):
    parent → child   {"op":"init"}                          → {"ok",providers,shops,rejected}
                     {"op":"build","idx":i,"sighting":{…}}  → {"rows":[…]}   (matches+build)
                     {"op":"shop","idx":i,"label":…,"attrs":{…}} → {"result":{…}}
                     {"op":"ping"}                          → {"ok":true}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


class _ProxyContext:
    """Records what the untrusted plugin registers; grants only declared caps.
    Side-effecting extension points are recorded as *rejected* (they cannot be
    honoured in isolation)."""

    SAFE = {"object_provider", "shop_provider"}

    def __init__(self, capabilities):
        self._caps = frozenset(capabilities or ())
        self.object_providers: list = []
        self.shop_providers: list = []
        self.rejected: list = []
        self.config: dict = {}

    def has(self, capability: str) -> bool:
        return capability in self._caps

    @property
    def capabilities(self):
        return self._caps

    @property
    def ring(self):
        return None

    @property
    def mesh(self):
        return None

    def veiled(self) -> bool:
        return False

    def add_object_provider(self, provider):
        self.object_providers.append(provider)

    def add_shop_provider(self, fn):
        self.shop_providers.append(fn)

    # side-effecting points: recorded and refused
    def add_glance_candidate(self, *_a, **_k):
        self.rejected.append("glance_candidate")

    def add_card_renderer(self, *_a, **_k):
        self.rejected.append("card_renderer")

    def add_vision_brain(self, *_a, **_k):
        self.rejected.append("vision_brain")

    def add_knowledge_brain(self, *_a, **_k):
        self.rejected.append("knowledge_brain")

    def add_perceptor(self, *_a, **_k):
        self.rejected.append("perceptor")

    # v2 surfaces are inert in the sandbox (documented): untrusted plugins get
    # pure-data providers only.
    def subscribe(self, *_a, **_k):
        return False

    @property
    def settings(self):
        return _NullSettings()


class _NullSettings:
    def get(self, key, default=None):
        return default

    def set(self, key, value):
        pass

    def all(self):
        return {}


def _load_plugin(pkg_dir: Path):
    manifest = json.loads((pkg_dir / "manifest.json").read_text())
    module = manifest["entry"].split(":", 1)[0]
    factory = manifest["entry"].split(":", 1)[1]
    src = (pkg_dir / f"{module}.py").read_text()
    ns: dict = {"__name__": f"dreamlayer_sandbox_{manifest['name']}"}
    exec(compile(src, f"<sandbox {manifest['name']}>", "exec"), ns)
    plugin = ns[factory]()
    return plugin, tuple(manifest.get("requires", ()))


def _sighting_from(d: dict):
    from ..object_lens.schema import ObjectSighting
    return ObjectSighting(
        label=d.get("label", ""),
        confidence=float(d.get("confidence", 0.0)),
        attributes=dict(d.get("attributes") or {}),
        frame=None,                       # the raw frame never crosses the jail
    )


def _row_to_dict(r) -> dict:
    return {"label": getattr(r, "label", ""), "detail": getattr(r, "detail", ""),
            "kind": getattr(r, "kind", ""), "value": getattr(r, "value", None),
            "source": getattr(r, "source", "")}


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        sys.stdout.write(json.dumps({"ok": False, "error": "no package dir"}) + "\n")
        return 2
    pkg_dir = Path(argv[0])
    caps = json.loads(argv[1]) if len(argv) > 1 else []

    ctx = _ProxyContext(caps)
    try:
        plugin, _requires = _load_plugin(pkg_dir)
        plugin.register(ctx)
    except Exception as exc:               # a plugin that dies on load stays in the child
        sys.stdout.write(json.dumps({"ok": False, "error": repr(exc)}) + "\n")
        sys.stdout.flush()
        return 1

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except ValueError:
            continue
        op = req.get("op")
        try:
            if op == "init":
                resp = {"ok": True,
                        "providers": len(ctx.object_providers),
                        "shops": len(ctx.shop_providers),
                        "rejected": ctx.rejected}
            elif op == "ping":
                resp = {"ok": True}
            elif op == "build":
                prov = ctx.object_providers[req["idx"]]
                sighting = _sighting_from(req.get("sighting") or {})
                rows = []
                if prov.matches(sighting):
                    rows = [_row_to_dict(r) for r in (prov.build(sighting) or [])]
                resp = {"ok": True, "rows": rows,
                        "facet": getattr(prov, "facet", "own"),
                        "name": getattr(prov, "name", "provider")}
            elif op == "shop":
                fn = ctx.shop_providers[req["idx"]]
                out = fn(req.get("label", ""), dict(req.get("attrs") or {}))
                resp = {"ok": True, "result": out if isinstance(out, dict) else {}}
            elif op == "meta":
                resp = {"ok": True,
                        "providers": [{"facet": getattr(p, "facet", "own"),
                                       "name": getattr(p, "name", "provider")}
                                      for p in ctx.object_providers]}
            else:
                resp = {"ok": False, "error": f"unknown op {op!r}"}
        except Exception as exc:
            resp = {"ok": False, "error": repr(exc)}
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
