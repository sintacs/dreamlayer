"""dream/engine.py — DreamEngine: ambient loop coordinator.

Runs as an asyncio background task alongside the normal Orchestrator.
The Orchestrator starts/stops it via enter_dream() / exit_dream().

Architecture
------------
  DreamEngine.run()  (infinite async loop, 2 Hz)
    ├── MicReactor.tick(ctx)    → palette shift BLE frame
    ├── ImuReactor.tick(ctx)    → geometry distortion BLE frame
    ├── GhostLayer.tick(ctx)    → WorldAnchorCard if place match
    └── SceneDescriber.tick(ctx)→ SynesthesiaCard every ~4s (camera gated)

All sub-systems receive a RecallContext built from the latest sensor data.
They return either a card dict (dispatched via bridge.send_card) or a raw
BLE command dict (dispatched via bridge.send_raw).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from ..recall_context import RecallContext
from .mic_reactor import MicReactor
from .imu_reactor import ImuReactor
from .ghost_layer import GhostLayer
from .scene_describer import SceneDescriber
from .sprite_bridge import SpriteBridge

log = logging.getLogger(__name__)

AMBIENT_HZ       = 2.0          # main loop cadence
SCENE_INTERVAL_S = 4.0          # how often to fire the VLM scene describer


class DreamEngine:
    """Coordinates all Dream Mode sub-systems."""

    def __init__(self, bridge, db=None, privacy=None) -> None:
        self.bridge   = bridge
        self.db       = db
        self.privacy  = privacy
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_scene_t: float = 0.0
        self._ctx: RecallContext = RecallContext()

        self.mic      = MicReactor()
        self.imu      = ImuReactor()
        self.ghost    = GhostLayer(db=db, privacy=privacy)
        self.describer = SceneDescriber()
        self.sprites  = SpriteBridge(bridge)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the ambient loop as a background asyncio task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="dream-engine")
        log.info("DreamEngine started")

    def stop(self) -> None:
        """Stop the ambient loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        log.info("DreamEngine stopped")

    @property
    def running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Sensor feed  (called by Orchestrator on every sensor event)
    # ------------------------------------------------------------------

    def feed_mic(self, fft: list[float], amplitude: float) -> None:
        self._ctx.mic_fft = fft
        self._ctx.mic_amplitude = amplitude

    def feed_imu(self, pose: dict, delta: dict) -> None:
        self._ctx.imu_pose = pose
        self._ctx.imu_delta = delta

    def feed_camera(self, jpeg_bytes: bytes) -> None:
        self._ctx.camera_frame = jpeg_bytes

    def feed_place(self, signature: str, anchors: list[dict]) -> None:
        self._ctx.place_signature = signature
        self._ctx.world_anchors = anchors

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        interval = 1.0 / AMBIENT_HZ
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                log.warning("DreamEngine tick error: %s", exc)
            await asyncio.sleep(interval)

    async def _tick(self) -> None:
        ctx = self._ctx

        # 1. Mic → palette shift (fast, every tick)
        palette_cmd = self.mic.tick(ctx)
        if palette_cmd:
            self.bridge.send_raw(palette_cmd)

        # 2. IMU → geometry distortion (fast, every tick)
        geo_cmd = self.imu.tick(ctx)
        if geo_cmd:
            self.bridge.send_raw(geo_cmd)

        # 3. Place anchors → ghost overlay (fires only on new match)
        ghost_card = self.ghost.tick(ctx)
        if ghost_card:
            self.bridge.send_card(ghost_card, event="dream_ghost")

        # 4. Scene describer → VLM text overlay (slow, gated by interval + camera)
        now = time.monotonic()
        if ctx.has_camera() and (now - self._last_scene_t) >= SCENE_INTERVAL_S:
            self._last_scene_t = now
            scene_card = await self.describer.tick(ctx)
            if scene_card:
                self.bridge.send_card(scene_card, event="dream_scene")
                # Also stream a generated sprite if SpriteBridge has a pending frame
                await self.sprites.flush_pending()
