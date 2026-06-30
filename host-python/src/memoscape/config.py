from __future__ import annotations
import os
from dataclasses import dataclass, field


@dataclass
class Paths:
    db:      str = "memoscape.db"
    lua_root: str = "../halo-lua"
    hud_out: str = "../assets/hud/samples"


@dataclass
class Config:
    paths:                      Paths = field(default_factory=Paths)
    capture_min_interval_ms:    int   = 4000
    proactive_min_confidence:   float = 0.45
    recall_min_confidence:      float = 0.40
    reduce_motion:              bool  = False

    # LLM tier-3 extraction
    llm_model:                  str   = "gpt-4o-mini"
    llm_confidence_threshold:   float = 0.60   # trigger if any event below this
    llm_word_threshold:         int   = 40      # trigger if transcript > N words
    llm_timeout_s:              float = 4.0
    openai_api_key:             str   = field(
        default_factory=lambda: os.environ.get("OPENAI_API_KEY", "")
    )


CONFIG = Config()
