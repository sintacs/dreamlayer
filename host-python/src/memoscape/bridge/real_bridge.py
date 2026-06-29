"""
Real Halo bridge over BLE using `brilliant-ble` + `brilliant-msg`.
Install: pip install brilliant-ble brilliant-msg
"""
from __future__ import annotations
import asyncio, json, threading
from .base import BridgeBase
from .lua_loader import collect_lua

try:
    from brilliant_ble import BrilliantBLE           # type: ignore
    from brilliant_msg import Message, MessageKind   # type: ignore
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


class HardwareNotConnectedError(RuntimeError):
    pass


class RealBridge(BridgeBase):
    def __init__(self, address: str | None = None, scan_timeout: float = 10.0) -> None:
        super().__init__()
        self.address = address
        self.scan_timeout = scan_timeout
        self._client = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._bundle: dict[str, str] = {}

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop and self._loop.is_running():
            return self._loop
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        return self._loop

    def _run(self, coro):
        loop = self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result(timeout=self.scan_timeout + 5)

    def connect(self) -> dict:
        if not _SDK_AVAILABLE:
            raise ImportError("brilliant-ble not installed. Run: pip install brilliant-ble brilliant-msg")
        return self._run(self._async_connect())

    async def _async_connect(self) -> dict:
        ble = BrilliantBLE()
        device = await ble.find_device(address=self.address, timeout=self.scan_timeout)
        if device is None:
            raise HardwareNotConnectedError(
                f"No Halo found after {self.scan_timeout}s scan. Ensure Halo is powered on and in pairing range.")
        self._client = await ble.connect(device)
        self._client.on_message(self._on_inbound)
        self.address = device.address
        info = await self._client.get_device_info()
        return {"device": info.get("name", "halo"), "address": self.address,
                "fw": info.get("firmware_version"), "display": [256, 256],
                "lua": info.get("lua_version", "5.3"), "mock": False}

    def disconnect(self) -> None:
        if self._client:
            self._run(self._client.disconnect())
            self._client = None

    def load_lua_app(self, lua_root: str) -> None:
        self._bundle = collect_lua(lua_root)
        if not self._client:
            raise HardwareNotConnectedError("Call connect() before load_lua_app()")
        self._run(self._async_upload())

    async def _async_upload(self) -> None:
        for path, src in self._bundle.items():
            # TODO(hardware): confirm FILE_WRITE API name against brilliant-msg release
            msg = Message(kind=MessageKind.FILE_WRITE, path=path, content=src)
            await self._client.send(msg)
        reset_msg = Message(kind=MessageKind.COMMAND, command="reset")
        await self._client.send(reset_msg)

    def send_command(self, kind: str, payload: dict | None = None) -> None:
        self._require_connected()
        msg = {"t": "command", "kind": kind, "payload": payload or {}}
        self._run(self._send_raw(msg))

    def send_card(self, payload: dict, event: str = "answer_ready") -> None:
        self._require_connected()
        if getattr(self, "_paused", False) and payload.get("type") != "PrivacyPausedCard":
            return
        msg = {"t": "card", "payload": payload, "event": event}
        self._run(self._send_raw(msg))

    async def _send_raw(self, obj: dict) -> None:
        data = json.dumps(obj)
        # TODO(hardware): tune MTU fragmentation after first device test
        msg = Message(kind=MessageKind.DATA, payload=data)
        await self._client.send(msg)

    def inject_event(self, name: str, payload: dict | None = None) -> None:
        command_map = {"privacy_pause": ("pause", None), "privacy_resume": ("resume", None), "wake": ("wake", None)}
        if name in command_map:
            kind, p = command_map[name]
            self.send_command(kind, p)
        else:
            raise NotImplementedError(
                f"inject_event('{name}') has no real-device equivalent. "
                "Hardware emits real events; trigger the physical action instead.")

    def _on_inbound(self, raw) -> None:
        try:
            obj = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
            name    = obj.get("name") or obj.get("t", "unknown")
            payload = obj.get("payload", {})
            if name == "privacy_pause":  self._paused = True
            elif name == "privacy_resume": self._paused = False
            self._emit_event(name, payload)
        except Exception as exc:
            self._emit_event("parse_error", {"error": str(exc), "raw": str(raw)})

    def _require_connected(self) -> None:
        if not self._client:
            raise HardwareNotConnectedError("Not connected. Call connect() first.")
