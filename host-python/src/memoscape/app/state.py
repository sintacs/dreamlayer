from dataclasses import dataclass
@dataclass
class HostState:
    connected: bool = False; paused: bool = False; last_card_type: str = ""
