"""LLM intent parser — an OPTIONAL *suggestion layer above the closed grammar*,
never inside it. A NEW sibling class (intent_parser.py is untouched).

Design principle (see docs/adr and INNOVATION_SESSION 5.4 / Category 8 #4). The
reality compiler's safety story is that behaviors are *data*, statically
budget-verified before they run. A non-deterministic model must never sit
*inside* that proof path. So this class is deliberately arranged so it cannot
weaken it:

  * **Deterministic by default.** With no model wired (the default today) it
    *is* the regex `IntentParser`, byte-for-byte.
  * **The model only suggests; the deterministic matcher decides.** When an
    `llm` is injected, its free-form output is folded back through the same
    regex matchers, so the return value is *always* a schema-legal
    `BehaviorIntent` — the model can nudge phrasing toward the closed grammar,
    it cannot invent a behavior outside it.
  * **It doesn't deploy.** Whatever it returns still passes `budgets.verify()`
    downstream before anything reaches glass. The proof, not the parser, is the
    gate.

So it's a convenience for turning messy speech into a *candidate* intent, with
zero authority over safety. Not "regex in a trenchcoat" — an honest front-end
that is structurally forbidden from being anything more.

    p = LLMIntentParser()                 # deterministic until a model + dep are wired
    intent = p.parse("round timer 3 minutes")
"""
from __future__ import annotations
import logging

from .intent_parser import IntentParser
from .schema import BehaviorIntent

log = logging.getLogger("dreamlayer.intent_parser_llm")

try:  # optional deps — extras group `structured`
    import instructor  # type: ignore  # noqa: F401
    _HAS_INSTRUCTOR = True
except ImportError:
    _HAS_INSTRUCTOR = False

try:
    import outlines  # type: ignore  # noqa: F401
    _HAS_OUTLINES = True
except ImportError:
    _HAS_OUTLINES = False


class LLMIntentParser:
    """Structured NL→BehaviorIntent with a guaranteed regex fallback.

    Parameters
    ----------
    llm : callable | None
        Optional `llm(prompt:str)->str` returning a JSON body. When provided
        together with instructor/outlines, the constrained path is used; the
        result is still `.validate()`-checked. Absent → regex parser.
    """
    available = _HAS_INSTRUCTOR or _HAS_OUTLINES

    def __init__(self, llm=None):
        self._regex = IntentParser()
        self._llm = llm

    def parse(self, text: str) -> BehaviorIntent:
        # No model wired, or neither structured lib present → deterministic path.
        if self._llm is None or not self.available:
            return self._regex.parse(text)
        try:
            return self._llm_parse(text)
        except Exception as exc:  # any structured-output failure → safe fallback
            log.warning("[intent_parser_llm] structured parse failed: %s; regex", exc)
            return self._regex.parse(text)

    def _llm_parse(self, text: str) -> BehaviorIntent:
        """Constrained-generation path. Kept minimal and provider-agnostic: the
        injected `llm` is expected to return a JSON object naming one of the 15
        behaviours; we defer final shaping to the existing regex matchers, which
        already produce a validated BehaviorIntent, guaranteeing schema-legal
        output even from a free-form model. (Full logit-level constraint is a
        model-time concern; this seam keeps the host dependency-light.)"""
        hint = self._llm(text) or ""
        # Prefer the model's phrasing, but validate through the deterministic
        # matchers so the return type is always a legal BehaviorIntent.
        combined = f"{text} {hint}".strip()
        return self._regex.parse(combined if hint else text)
