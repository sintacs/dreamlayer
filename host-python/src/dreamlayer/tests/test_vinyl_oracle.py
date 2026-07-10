"""test_vinyl_oracle.py — the Vinyl Oracle object-lens connector.

Pins the connector's pure logic (query build with an optional token, release
parse, the want/have collectibility read, lookup with an injected fetch), that
the provider folds a Discogs release into a look-at-a-thing panel row and caches
by release, and its plugin registration + object_lens/network capability gate.
Everything here runs with no network and no Discogs token.
"""
from __future__ import annotations

import json

from dreamlayer.plugins import PluginContext, PluginRegistry, PluginPackage, validate
from dreamlayer.plugins.vinyl_oracle import (
    build_query, parse_release, lookup, _sought_after,
    VinylOracleProvider, vinyl_oracle_plugin,
)
from dreamlayer.object_lens.schema import ObjectSighting


def _sighting(**attrs) -> ObjectSighting:
    return ObjectSighting(label="record", confidence=0.9, attributes=attrs)


# -- pure logic ---------------------------------------------------------------

def test_build_query_encodes_artist_and_title():
    url = build_query("Miles Davis", "Kind of Blue")
    assert "artist=Miles+Davis" in url and "release_title=Kind+of+Blue" in url
    assert "type=release" in url and "token" not in url      # no token → no param


def test_build_query_includes_a_token_when_present():
    assert "token=abc123" in build_query("a", "b", token="abc123")


def test_sought_after_reads_want_over_have():
    assert _sought_after({"want": 900, "have": 300}) == "grail"       # ratio 3.0
    assert _sought_after({"want": 60, "have": 100}) == "sought-after"  # ratio 0.6
    assert _sought_after({"want": 10, "have": 100}) == "common"
    assert _sought_after({"want": 5, "have": 3}) is None              # too few own it


def test_parse_release_maps_present_fields_only():
    got = parse_release({
        "title": "Miles Davis - Kind Of Blue", "year": 1959,
        "label": ["Columbia"], "country": "US", "format": ["Vinyl", "LP"],
        "community": {"want": 4000, "have": 2000},
    })
    assert got["title"] == "Miles Davis - Kind Of Blue" and got["year"] == "1959"
    assert got["label"] == "Columbia" and got["country"] == "US"
    assert got["format"] == ["vinyl", "LP"] and got["collectibility"] == "grail"


def test_parse_release_omits_missing_fields():
    assert parse_release({"title": "Mystery"}) == {"title": "Mystery"}   # no year/etc


def test_lookup_with_an_injected_fetch():
    body = json.dumps({"results": [{"title": "A - B", "year": 1971,
                                    "label": ["Harvest"]}]})
    got = lookup("a", "b", lambda url: body)
    assert got["title"] == "A - B" and got["year"] == "1971" and got["label"] == "Harvest"


def test_lookup_swallows_failures():
    assert lookup("a", "b", lambda url: (_ for _ in ()).throw(OSError("no net"))) == {}
    assert lookup("a", "b", lambda url: "not json") == {}
    assert lookup("", "", lambda url: '{"results":[]}') == {}          # nothing to ask


# -- the object-lens provider -------------------------------------------------

def test_provider_matches_a_record_sighting_with_a_title():
    p = VinylOracleProvider(fetch_fn=lambda u: "{}")
    assert p.matches(_sighting(artist="Bowie", title="Low"))
    assert not p.matches(_sighting(artist="Bowie"))         # a title is required


def test_provider_builds_a_pressing_row():
    body = json.dumps({"results": [{
        "title": "David Bowie - Low", "year": 1977, "label": ["RCA Victor"],
        "country": "UK", "format": ["Vinyl", "LP"],
        "community": {"want": 3000, "have": 1000}}]})
    p = VinylOracleProvider(fetch_fn=lambda u: body)
    rows = p.build(_sighting(artist="David Bowie", title="Low"))
    assert len(rows) == 1 and rows[0].source == "vinyl-oracle"
    assert "David Bowie - Low" in rows[0].label
    assert "1977" in rows[0].detail and "RCA Victor" in rows[0].detail
    assert "grail" in rows[0].detail


def test_provider_caches_by_release(monkeypatch=None):
    calls = {"n": 0}
    def fetch(url):
        calls["n"] += 1
        return json.dumps({"results": [{"title": "X", "year": 1980}]})
    clock = {"t": 0.0}
    p = VinylOracleProvider(fetch_fn=fetch, ttl=100.0, now_fn=lambda: clock["t"])
    p.build(_sighting(artist="a", title="x"))
    p.build(_sighting(artist="a", title="x"))               # same release → one fetch
    assert calls["n"] == 1
    clock["t"] = 200.0                                       # past the TTL → refetch
    p.build(_sighting(artist="a", title="x"))
    assert calls["n"] == 2


def test_provider_degrades_when_nothing_is_found():
    p = VinylOracleProvider(fetch_fn=lambda u: '{"results":[]}')
    rows = p.build(_sighting(artist="Nobody", title="Nothing"))
    assert rows[0].kind == "info" and "no pressing found" in rows[0].detail


# -- it loads as a plugin, gated on object_lens + network ---------------------

def test_plugin_registers_and_is_capability_gated():
    reg: list = []
    # missing network → skipped
    ctx0 = PluginContext(object_registry=None, capabilities=frozenset({"object_lens"}))
    r0 = PluginRegistry(ctx0)
    r0.load(vinyl_oracle_plugin(fetch_fn=lambda u: "{}"))
    assert r0.result.loaded == []                           # requires network too
    # with both caps → registers an object provider
    ctx = PluginContext(capabilities=frozenset({"object_lens", "network"}))
    r = PluginRegistry(ctx)
    r.load(vinyl_oracle_plugin(fetch_fn=lambda u: "{}"))
    assert r.result.loaded == ["vinyl-oracle"]
    assert ctx.added["object_provider"]


def test_plugin_persists_and_restores_the_token():
    # settings are name-scoped by the registry; go through it so set_token writes
    # to *this* plugin's bucket and a later load restores it.
    ctx = PluginContext(capabilities=frozenset({"object_lens", "network"}))
    plug = vinyl_oracle_plugin(fetch_fn=lambda u: "{}")
    reg = PluginRegistry(ctx)
    reg.load(plug)
    plug.set_token("tok-xyz")
    # a fresh instance on the same context restores it on start()
    plug2 = vinyl_oracle_plugin(fetch_fn=lambda u: "{}")
    reg2 = PluginRegistry(ctx)
    reg2.load(plug2)
    reg2.start_all()
    assert plug2.provider.token == "tok-xyz"


def test_packaged_passes_the_validation_gate():
    src = ("from dreamlayer.plugins.vinyl_oracle import vinyl_oracle_plugin\n"
           "def p():\n return vinyl_oracle_plugin()\n")
    pkg = PluginPackage.build(name="vinyl-oracle", version="0.1.0",
                              entry="plugin:p", requires=("object_lens", "network"),
                              source=src)
    report = validate(pkg, host_capabilities=frozenset({"object_lens", "network"}))
    assert report.ok, report.errors
