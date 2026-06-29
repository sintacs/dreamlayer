"""themes.py — Python mirror of halo-lua/display/palette.lua.

Used by renderer.py (Pillow) and hud/cards.py for card payload generation.
All hex values must stay in sync with palette.lua.
"""

# Foundations
BACKGROUND        = 0x000000
SURFACE           = 0x0E1416   # outline / 1px border only — never fill

# Text
TEXT_PRIMARY      = 0xF0F4F5   # warm off-white; kills white-fringe halation
TEXT_SECONDARY    = 0xA8B8C0   # raised from 0x8A9BA3
TEXT_GHOST        = 0x5A6E76   # lowest hierarchy

# Memory / trust (teal family)
ACCENT_MEMORY     = 0x39D6A8   # was 0x2FD4C4; +8° warm, -12% lum
ACCENT_MEMORY_DIM = 0x1E7A6A   # idle breathing dot glow

# Coral / attention
ACCENT_ATTENTION  = 0xE8624E   # was 0xFF6B5E

# Status
ACCENT_SUCCESS    = 0x56D364
ACCENT_ERROR      = 0xFF5C5C
BORDER_SUBTLE     = 0x2E4048   # was 0x1F2A2E
STATUS_PAUSED     = 0x9AADB5   # was 0x6B7A82


def to_rgb(hexval: int) -> tuple[int, int, int]:
    """Convert 0xRRGGBB int to (R, G, B) tuple."""
    return ((hexval >> 16) & 0xFF, (hexval >> 8) & 0xFF, hexval & 0xFF)


def to_rgba(hexval: int, alpha: float = 1.0) -> tuple[int, int, int, int]:
    """Convert 0xRRGGBB + float alpha [0..1] to (R, G, B, A) tuple."""
    r, g, b = to_rgb(hexval)
    return (r, g, b, int(alpha * 255))


def conf_color(confidence: float | None) -> int:
    """Return palette color for a confidence value."""
    if confidence is None:
        return TEXT_GHOST
    if confidence >= 0.75:
        return ACCENT_SUCCESS
    if confidence >= 0.40:
        return ACCENT_MEMORY
    return STATUS_PAUSED
