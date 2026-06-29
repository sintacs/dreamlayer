from dataclasses import dataclass, field
@dataclass
class Paths:
    db: str = "memoscape.db"; lua_root: str = "../halo-lua"; hud_out: str = "../assets/hud/samples"
@dataclass
class Config:
    paths: Paths = field(default_factory=Paths)
    capture_min_interval_ms: int = 4000
    proactive_min_confidence: float = 0.45
    recall_min_confidence: float = 0.40
    reduce_motion: bool = False
CONFIG = Config()
