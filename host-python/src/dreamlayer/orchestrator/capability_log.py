"""orchestrator/capability_log.py — the plugin capability-transparency log.

A privacy-first product should let the *wearer* see what each plugin actually
did with the capabilities it was granted — not just what it declared. This is
that log: a per-plugin record of the capability-relevant activity the host
**mediates or observes** — the grant itself, host events routed to the plugin,
and calls into an isolated (subprocess) plugin's providers.

Honest scope: an *in-process* plugin's raw `urllib`/socket/file access is not
intercepted here — the host doesn't sit in that path. That is exactly what the
subprocess and (roadmap) WASM isolation tiers add mediation for; run untrusted
plugins there and their provider/RPC activity shows up in this log. So the log
is complete for isolated plugins and mediated surfaces, and honest about the
in-process gap. Cheap (counters + a small ring), thread-safe.
"""
from __future__ import annotations

import threading
import time
from collections import deque

_RING = 12


class CapabilityLedger:
    def __init__(self, now_fn=None) -> None:
        self._now = now_fn or time.time
        self._lock = threading.Lock()
        self._grants: dict[str, tuple] = {}          # plugin -> declared caps
        self._counts: dict[str, dict] = {}           # plugin -> {action: n}
        self._recent: dict[str, deque] = {}          # plugin -> ring of events

    def grant(self, plugin: str, capabilities) -> None:
        with self._lock:
            self._grants[plugin] = tuple(capabilities or ())

    def record(self, plugin: str, action: str, detail: str = "") -> None:
        """Note that `plugin` exercised `action` (e.g. "event:mesh",
        "rpc:build", "mesh:emit"). `detail` is a short human note."""
        if not plugin:
            return
        with self._lock:
            self._counts.setdefault(plugin, {})
            self._counts[plugin][action] = self._counts[plugin].get(action, 0) + 1
            ring = self._recent.setdefault(plugin, deque(maxlen=_RING))
            ring.append({"ts": self._now(), "action": action, "detail": str(detail)[:120]})

    def summary(self, plugin: str) -> dict:
        with self._lock:
            return {
                "granted": list(self._grants.get(plugin, ())),
                "actions": dict(self._counts.get(plugin, {})),
                "recent": list(self._recent.get(plugin, ())),
            }

    def report(self) -> dict:
        """{plugin: {granted, actions, recent}} for every plugin seen."""
        with self._lock:
            names = set(self._grants) | set(self._counts)
        return {name: self.summary(name) for name in sorted(names)}
