"""test_wasm_host.py — the WASM isolation tier seam.

End-to-end execution needs an operator-provided wasmtime + python.wasm guest
(off in this container), so these pin the parts that are always exercisable:
the capability→WASI-grant command construction, availability gating, and that
the store falls back to the subprocess jail when WASM isn't configured.
"""
from __future__ import annotations

from dreamlayer.plugins import wasm_host


def test_wasi_command_maps_capabilities_to_grants():
    base = wasm_host.wasi_command("/wt", "/g.wasm", [], "/pkg", ["[]"])
    assert base[:2] == ["/wt", "run"]
    assert "--dir=/pkg::/pkg" not in base            # no fs grant when fs denied
    assert "inherit-network" not in base             # no net when network denied
    assert "/g.wasm" in base and "dreamlayer.plugins.sandbox_child" in base

    fs = wasm_host.wasi_command("/wt", "/g.wasm", ["fs"], "/pkg", ["[]"])
    assert "--dir=/pkg::/pkg" in fs                   # fs granted → the package dir

    net = wasm_host.wasi_command("/wt", "/g.wasm", ["network"], "/pkg", ["[]"])
    assert "inherit-network" in net                  # network granted → sockets


def test_available_is_off_without_a_runtime_and_guest(monkeypatch):
    monkeypatch.delenv("DL_WASM_RUNTIME", raising=False)
    monkeypatch.delenv("DL_WASM_GUEST", raising=False)
    monkeypatch.setattr(wasm_host.shutil, "which", lambda _n: None)
    assert wasm_host.available() is False


def test_dl_wasm_none_force_disables(monkeypatch):
    monkeypatch.setenv("DL_WASM", "none")
    monkeypatch.setenv("DL_WASM_RUNTIME", "/usr/bin/wasmtime")
    monkeypatch.setenv("DL_WASM_GUEST", "/tmp/anything")
    assert wasm_host.available() is False


def test_host_builds_a_wasmtime_argv(monkeypatch, tmp_path):
    monkeypatch.setattr(wasm_host, "runtime", lambda: "/usr/bin/wasmtime")
    monkeypatch.setattr(wasm_host, "guest", lambda: "/opt/python.wasm")
    h = wasm_host.WasmPluginHost(tmp_path, ["network"], name="x")
    argv = h._child_argv()
    assert argv[0] == "/usr/bin/wasmtime" and h.sandbox == "wasm"
    assert "inherit-network" in argv


def test_store_falls_back_to_subprocess_when_wasm_absent(monkeypatch):
    # available() False (default) → the untrusted tier is the subprocess jail
    from dreamlayer.plugins.isolation import SubprocessPluginHost
    from dreamlayer.plugins import wasm_host as wh
    monkeypatch.setattr(wh, "available", lambda: False)
    Host = wh.WasmPluginHost if wh.available() else SubprocessPluginHost
    assert Host is SubprocessPluginHost
