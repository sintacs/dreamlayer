"""reality_compiler — Natural language → Halo behavior, deployed in < 10 s.

Public API
----------
    from memoscape.reality_compiler import RealityCompiler

    rc = RealityCompiler()
    result = await rc.compile("3-minute round timer with 20s overtime")
    # result.lua_code, result.host_code, result.intent, result.validation
"""
from .compiler import RealityCompiler, CompileResult
from .intent_parser import IntentParser
from .schema import (
    BehaviorIntent, RoundTimerIntent, OvertimeTimerIntent,
    StopwatchIntent, IntervalTimerIntent, SimpleCounterIntent,
    BatteryWarningIntent, TeleprompterIntent, CoachingCueIntent,
    PointsMarkerIntent, NextClassIntent, TextSubtitlesIntent,
    HabitReminderIntent, ReactTimerIntent, GestureRepeaterIntent,
    SpeakerIndicatorIntent, ValidationError,
)
from .codegen import CodeGenerator
from .emulator import HaloEmulator
from .validator import EmulatorValidator
from .deployer import HaloDeployer

__all__ = [
    "RealityCompiler", "CompileResult",
    "IntentParser",
    "BehaviorIntent", "RoundTimerIntent", "OvertimeTimerIntent",
    "StopwatchIntent", "IntervalTimerIntent", "SimpleCounterIntent",
    "BatteryWarningIntent", "TeleprompterIntent", "CoachingCueIntent",
    "PointsMarkerIntent", "NextClassIntent", "TextSubtitlesIntent",
    "HabitReminderIntent", "ReactTimerIntent", "GestureRepeaterIntent",
    "SpeakerIndicatorIntent", "ValidationError",
    "CodeGenerator",
    "HaloEmulator",
    "EmulatorValidator",
    "HaloDeployer",
]
