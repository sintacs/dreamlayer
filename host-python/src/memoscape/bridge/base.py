from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable

class BridgeBase(ABC):
    def __init__(self) -> None:
        self._event_cb: Callable[[str, dict], None] | None = None
    def on_event(self, cb: Callable[[str, dict], None]) -> None:
        self._event_cb = cb
    def _emit_event(self, name: str, payload: dict | None = None) -> None:
        if self._event_cb:
            self._event_cb(name, payload or {})
    @abstractmethod
    def connect(self) -> dict: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def load_lua_app(self, lua_root: str) -> None: ...
    @abstractmethod
    def send_command(self, kind: str, payload: dict | None = None) -> None: ...
    @abstractmethod
    def send_card(self, payload: dict, event: str = "answer_ready") -> None: ...
    @abstractmethod
    def inject_event(self, name: str, payload: dict | None = None) -> None: ...
