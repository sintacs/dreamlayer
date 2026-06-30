"""app/dream/engine.py

DreamEngine — coordinates all Dream Mode sub-reactors.

Runs as a background asyncio task alongside the normal Memoscape
card pipeline.  When state.mode == 'DREAM', the orchestrator starts
this engine and suspends the normal ask() / tick() flow.

Architecture
------------
    DreamEngine.run()
        every 0.5s  → mic_reactor.tick()    → stream_palette()
        every 0.5s  → imu_reactor.tick()    → stream_geometry()
        every 0.5s  → ghost_layer.tick()    → send_card(WorldAnchorCard)
        every 4.0s  → scene_describer.tick()→ send_sprite() / send_card(SynesthesiaCard)

All sub-reactors are stateless between ticks; the engine owns timing.

Usage
-----
    engine = DreamEngine(bridge, orchestrator, state)
    task   = asyncio.create_task(engine.run())
    # To exit:
    engine.stop()
    await task
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from ..state import HostState
from .mic_reactor   import MicReactor
from .imu_reactor   import ImuReactor
from .ghost_layer   import GhostLayer
from .scene_describer import SceneDescriber
from ..recall_context import RecallContext

log = logging.getLogger(__name__)

AMBIENT_TICK_S  = 0.5   # mic / IMU / ghost tick rate
SCENE_TICK_S    = 4.0   # VLM scene descrip