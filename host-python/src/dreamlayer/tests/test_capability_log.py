"""test_capability_log.py — the plugin capability-transparency log.

What each plugin was granted and what it actually did with it (host events
routed to it, isolated-provider calls) — a record the wearer can read.
"""
from __future__ import annotations

from dreamlayer.orchestrator.capability_log import CapabilityLedger
from dreamlayer.orchestrator.orchestrator import Orchestrator
from dreamlayer.plugins import make_plugin
from dreamlayer.tests.test_integration_dream_suite import FakeBridge


def _subscriber(kind="glance", cap="glance"):
    # a plugin that subscribes to a veil-gated host moment via the event bus
    return make_plugin("sub", lambda ctx: ctx.subscribe(kind, lambda k, p: None),
                       requires=(cap,))


class TestLedger:
    def test_grant_and_record(self):
        log = CapabilityLedger()
        log.grant("p", ["network", "cards"])
        log.record("p", "event:mesh")
        log.record("p", "event:mesh")
        log.record("p", "rpc:build")
        s = log.summary("p")
        assert s["granted"] == ["network", "cards"]
        assert s["actions"] == {"event:mesh": 2, "rpc:build": 1}
        assert len(s["recent"]) == 3

    def test_report_lists_every_plugin(self):
        log = CapabilityLedger()
        log.grant("a", ["cards"])
        log.record("b", "event:place")
        assert set(log.report()) == {"a", "b"}

    def test_empty_plugin_is_blank(self):
        assert CapabilityLedger().summary("nobody") == {
            "granted": [], "actions": {}, "recent": []}


class TestOrchestratorWiring:
    def test_grants_recorded_on_load(self):
        orc = Orchestrator(FakeBridge())
        orc.load_plugins([make_plugin("widget", lambda c: None, requires=("glance",))])
        report = orc.capability_report()
        assert "widget" in report
        assert report["widget"]["granted"] == ["glance"]

    def test_event_delivery_is_logged(self):
        orc = Orchestrator(FakeBridge())
        orc.load_plugins([_subscriber("glance", "glance")])
        orc.publish_plugin_event("glance", {"scene": "object"})
        summary = orc.capability_report("sub")
        assert summary["granted"] == ["glance"]
        assert summary["actions"].get("event:glance", 0) >= 1

    def test_veiled_events_are_not_logged(self):
        orc = Orchestrator(FakeBridge())
        orc.load_plugins([_subscriber("glance", "glance")])
        orc.privacy.pause()                       # veil down: only 'veil' events flow
        orc.publish_plugin_event("glance", {"scene": "object"})
        summary = orc.capability_report("sub")
        assert summary["actions"].get("event:glance", 0) == 0   # nothing routed, nothing logged
