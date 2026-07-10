"""reality_compiler — behaviors for Halo, authored by the user.

v2 (``dreamlayer.reality_compiler.v2``) is the product: the Rehearsal
paradigm — perform a behavior once in sketch time, the choreographer infers
a Figment (a total, statically-budgeted, signed scene-machine), and a fixed
on-device stage runs it. No user code ever ships to the glasses.

    from dreamlayer.reality_compiler.v2 import RealityCompilerV2

    rc = RealityCompilerV2()
    session = rc.rehearse()
    session.double_tap()
    session.say("rolling - three minutes")
    session.say("last ten seconds, pulse")
    session.say("then it starts again")
    result = session.finish()
    if result.ok:
        rc.keep(result.figment)
        rc.deploy(result.figment.id)

The v1 plain-English surface survives as a *parser only*:
``RealityCompilerV2.compile_text()`` reuses the v1 ``IntentParser`` and
lifts the parsed intent to a Figment (``v2/compat.py``). The v1 codegen and
deploy pipeline (string-templated Lua uploaded over BLE) was removed — it
substituted parsed natural-language parameters into Lua source with no
escaping and no API blocklist, an injection-shaped surface with no reason
to exist now that everything new travels as verified data to the fixed
stage. Stored Figments, not phrases or generated code, are the durable
objects (docs/RC_V2_PICKED.md).
"""
from .intent_parser import IntentParser
from .schema import (
    BehaviorIntent, RoundTimerIntent, OvertimeTimerIntent,
    StopwatchIntent, IntervalTimerIntent, SimpleCounterIntent,
    BatteryWarningIntent, TeleprompterIntent, CoachingCueIntent,
    PointsMarkerIntent, NextClassIntent, TextSubtitlesIntent,
    HabitReminderIntent, ReactTimerIntent, GestureRepeaterIntent,
    SpeakerIndicatorIntent, ValidationError,
)

__all__ = [
    "IntentParser",
    "BehaviorIntent", "RoundTimerIntent", "OvertimeTimerIntent",
    "StopwatchIntent", "IntervalTimerIntent", "SimpleCounterIntent",
    "BatteryWarningIntent", "TeleprompterIntent", "CoachingCueIntent",
    "PointsMarkerIntent", "NextClassIntent", "TextSubtitlesIntent",
    "HabitReminderIntent", "ReactTimerIntent", "GestureRepeaterIntent",
    "SpeakerIndicatorIntent", "ValidationError",
]
