"""plugins/wasm_host.py — the WASM isolation tier (roadmap, seam-complete).

The strongest confinement for untrusted plugins: run the same sandbox child
under a WebAssembly runtime (wasmtime) where the guest has **no ambient
authority** — no filesystem, no network, no syscalls — unless the host grants a
specific WASI capability. That maps one-to-one onto DreamLayer's capability
model: a *denied* capability is simply a WASI grant the host never provides.

    denied `fs`      -> no --dir grants (the guest sees no host filesystem)
    denied `network` -> no --wasi inherit-network (the guest cannot reach the net)
    granted `fs`     -> --dir=<package>::/pkg  (only the package dir, read-only intent)

Architecturally this subclasses SubprocessPluginHost and overrides only the
launch command, so the capability-mediated proxy surface, the deadline, the
health + transparency recording, and the kill-on-hang are all inherited.

**Operator-provided runtime.** Actually executing needs (a) a `wasmtime` binary
and (b) a Python-for-WASI guest (`python.wasm`) with the dreamlayer package
bundled in — the same way the NPU perceptor needs a Vela model or the BLE tier
needs a bench Halo. Set ``DL_WASM_RUNTIME`` (path to wasmtime) and
``DL_WASM_GUEST`` (path to the guest .wasm). Without both, this tier reports
unavailable and the store falls back to the subprocess jail — see
``PluginStore.load_installed``. The command construction + tier selection here
are exercised in tests; end-to-end execution is gated on that operator runtime.
"""
from __future__ import annotations

import os
import shutil

from .isolation import SubprocessPluginHost


def runtime() -> str:
    """Path to the wasmtime binary, from DL_WASM_RUNTIME or PATH; "" if none."""
    return os.environ.get("DL_WASM_RUNTIME") or shutil.which("wasmtime") or ""


def guest() -> str:
    """Path to the Python-for-WASI guest (python.wasm) from DL_WASM_GUEST."""
    return os.environ.get("DL_WASM_GUEST", "")


def available() -> bool:
    """True only when both a wasmtime runtime and a guest image are configured.
    Off by default (this container has neither), so the store degrades to the
    subprocess tier rather than half-running."""
    if os.environ.get("DL_WASM", "auto").lower() == "none":
        return False
    return bool(runtime() and os.path.isfile(guest()))


def wasi_command(runtime_bin: str, guest_wasm: str, capabilities, package_dir,
                 child_args) -> list:
    """Build the wasmtime invocation that runs the sandbox child in the guest,
    granting only the WASI capabilities that map to declared plugin capabilities.
    A denied capability = a grant that is simply absent."""
    caps = set(capabilities or [])
    cmd = [runtime_bin, "run"]
    # filesystem: only when `fs` is granted, and only the package dir
    if "fs" in caps:
        cmd += [f"--dir={package_dir}::/pkg"]
    # network: wasmtime withholds sockets unless explicitly inherited
    if "network" in caps:
        cmd += ["--wasi", "inherit-network"]
    cmd += [guest_wasm, "-m", "dreamlayer.plugins.sandbox_child", "/pkg"]
    cmd += list(child_args)
    return cmd


class WasmPluginHost(SubprocessPluginHost):
    """Runs the sandbox child under wasmtime. Overrides only the launch command;
    everything else (proxies, deadline, health, transparency, kill-on-hang) is
    inherited from SubprocessPluginHost."""

    def _child_argv(self) -> list:
        import json
        self.sandbox = "wasm"
        return wasi_command(runtime(), guest(), self.capabilities,
                            self.package_dir,
                            [json.dumps(self.capabilities)])
