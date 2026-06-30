from dataclasses import dataclass

# mode: "MEMORY" = normal card recall pipeline
#       "DREAM"  = ambient generative reality layer
@dataclass
class HostState:
    connected:      bool = False
    paused:         bool = False
    last_card_type: str  = ""
    mode:           str  = "MEMORY"   # "MEMORY" | "DREAM"
