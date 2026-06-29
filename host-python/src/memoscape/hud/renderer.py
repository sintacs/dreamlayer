"""renderer.py — Pillow-based 256×256 card renderer for emulator previews.

Produces PNG snapshots of each card type at the final pixel positions
specified in cards.lua and the design spec.

Used by:
  - scripts/render_samples.py  (exports assets/hud/samples/*.png)
  - emulator_bridge.py         (on-screen preview in dev mode)

NOT used on-device. On device, the Lua renderer reads the card dict directly.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from . import themes as T
from . import cards as C

SIZE = 256
CENTER = (128, 128)

# Font sizes (px) per size token — tuned for 256px display
FONT_PX = {
    "hero": 22,   # SIZE_HERO: largest, primary answer
    "xl":   19,
    "lg":   16,
    "md":   13,
    "sm":   10,
}

# Safe margins
SAFE_L = 22
SAFE_R = 234
SAFE_T = 32
SAFE_B = 224


def _hex_to_rgb(h: int) -> tuple[int, int, int]:
    return T.to_rgb(h)


def _font(size_token: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    px = FONT_PX.get(size_token, 13)
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", px)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", px)
        except OSError:
            return ImageFont.load_default()


def _mask() -> Image.Image:
    """Circular mask: 1=visible inside circle, 0=clipped."""
    m = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(m).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    return m


class CardRenderer:
    def __init__(self):
        self._mask = _mask()

    def render(self, card: dict) -> Image.Image:
        """Render a card dict to a 256×256 RGBA PIL Image."""
        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        ctype = card.get("type", "")

        if ctype == "ReadyCard":            self._ready(draw, card)
        elif ctype == "SavedMemoryCard":    self._saved_memory(draw, card)
        elif ctype == "QueryListeningCard": self._query_listening(draw, card)
        elif ctype == "LoadingCard":        self._loading(draw, card)
        elif ctype == "ObjectRecallCard":   self._object_recall(draw, card)
        elif ctype == "CommitmentRecallCard": self._commitment_recall(draw, card)
        elif ctype == "ProactiveMemoryCard": self._proactive_memory(draw, card)
        elif ctype == "PersonContextCard":  self._person_context(draw, card)
        elif ctype == "PrivacyPausedCard":  self._privacy_paused(draw, card)
        elif ctype == "ErrorCard":          self._error_card(draw, card)
        elif ctype == "LowConfidenceCard":  self._low_confidence(draw, card)

        # Apply circular clip
        img.putalpha(self._mask)
        return img

    def save(self, card: dict, path: str | Path) -> None:
        self.render(card).save(str(path))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _text(self, draw, x, y, text, size, color, anchor="mm"):
        draw.text((x, y), text, font=_font(size), fill=_hex_to_rgb(color), anchor=anchor)

    def _hline(self, draw, x1, x2, y, color, alpha=255):
        r, g, b = _hex_to_rgb(color)
        draw.line([(x1, y), (x2, y)], fill=(r, g, b, alpha), width=1)

    def _vbar(self, draw, x, y1, y2, width, color):
        draw.rectangle([x, y1, x + width - 1, y2], fill=_hex_to_rgb(color))

    def _dot(self, draw, x, y, r, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(r_, g_, b_, alpha))

    def _circle(self, draw, cx, cy, r, stroke, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=(r_, g_, b_, alpha), width=stroke
        )

    def _arc(self, draw, cx, cy, r, start_deg, end_deg, stroke, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        box = [cx - r, cy - r, cx + r, cy + r]
        draw.arc(box, start=start_deg, end=end_deg,
                 fill=(r_, g_, b_, alpha), width=stroke)

    # ------------------------------------------------------------------
    # Card renderers
    # ------------------------------------------------------------------
    def _ready(self, draw, card):
        # Breathing dot at idle (peak radius)
        self._dot(draw, 128, 128, 9, T.ACCENT_MEMORY)
        # Glow (static preview = 18% alpha)
        self._dot(draw, 128, 128, 14, T.ACCENT_MEMORY_DIM, alpha=46)
        # Satellites
        for pos in [(128,108),(148,128),(128,148),(108,128)]:
            self._dot(draw, pos[0], pos[1], 2, T.ACCENT_MEMORY_DIM)

    def _saved_memory(self, draw, card):
        self._text(draw, 128, 102, "SAVED", "sm", T.ACCENT_SUCCESS)
        self._text(draw, 128, 126, card.get("primary",""), "lg", T.TEXT_PRIMARY)
        self._dot(draw, 128, 158, 3, T.ACCENT_SUCCESS)
        self._arc(draw, 128, 128, 110, 210, 330, 1, T.ACCENT_SUCCESS, alpha=77)

    def _query_listening(self, draw, card):
        self._text(draw, 128, 110, "Listening\u2026", "sm", T.ACCENT_ATTENTION)
        for i, cx in enumerate([104,112,120,128,136,144,152]):
            h = 8 + (i % 3) * 4  # deterministic heights for static preview
            draw.rectangle([cx-1, 136-h//2, cx+1, 136+h//2],
                           fill=_hex_to_rgb(T.ACCENT_ATTENTION))

    def _loading(self, draw, card):
        self._arc(draw, 128, 128, 48, 0, 90, 2, T.ACCENT_MEMORY)

    def _object_recall(self, draw, card):
        obj   = (card.get("object") or "").upper()
        place = card.get("primary") or ""
        detail = card.get("detail") or ""
        footer = card.get("last_seen") or ""
        conf   = card.get("confidence")

        self._text(draw, 128, 76,  obj,    "sm",   T.ACCENT_MEMORY)
        self._hline(draw, 54, 202, 92,     T.BORDER_SUBTLE)
        self._vbar(draw, 22, 104, 128, 2,  T.ACCENT_MEMORY)
        self._text(draw, 128, 116, place,  "hero", T.TEXT_PRIMARY)
        self._text(draw, 128, 148, detail, "md",   T.TEXT_SECONDARY)
        self._text(draw, 128, 173, footer, "sm",   T.TEXT_GHOST)
        self._dot(draw, 128, 196, 3, T.conf_color(conf))

    def _commitment_recall(self, draw, card):
        person = card.get("person") or ""
        task   = card.get("primary") or ""
        due    = card.get("due") or ""
        conf   = card.get("confidence")

        self._text(draw, 128, 82,  f"YOU PROMISED {person.upper()}", "sm", T.ACCENT_MEMORY)
        self._vbar(draw, 22, 96, 168, 2, T.ACCENT_MEMORY)
        self._text(draw, 128, 108, task, "lg", T.TEXT_PRIMARY)
        self._text(draw, 128, 174, due,  "sm", T.TEXT_SECONDARY)
        self._dot(draw, 128, 195, 2, T.conf_color(conf))

    def _proactive_memory(self, draw, card):
        summary = card.get("primary") or ""
        person  = card.get("person")

        self._text(draw, 128, 68, "LAST TIME HERE", "sm", T.TEXT_GHOST)
        self._hline(draw, 68, 188, 82, T.BORDER_SUBTLE)
        self._text(draw, 128, 96, summary, "md", T.TEXT_SECONDARY)
        if person:
            self._text(draw, 128, 178, f"With {person}", "sm", T.ACCENT_MEMORY)

    def _person_context(self, draw, card):
        self._circle(draw, 128, 128, 112, 1, T.BORDER_SUBTLE)
        self._text(draw, 128, 88,  card.get("primary") or "",  "lg", T.ACCENT_MEMORY)
        self._text(draw, 128, 122, card.get("headline") or "", "md", T.TEXT_PRIMARY)
        self._text(draw, 128, 150, card.get("detail") or "",   "sm", T.TEXT_SECONDARY)

    def _privacy_paused(self, draw, card):
        self._circle(draw, 128, 128, 118, 1, T.STATUS_PAUSED, alpha=102)
        r_, g_, b_ = _hex_to_rgb(T.STATUS_PAUSED)
        draw.ellipse([100,72,156,128], fill=(r_,g_,b_, 51))  # 20% alpha fill
        # Pause bars: left at x=119, right at x=128+5=133
        draw.rectangle([119, 93, 123, 107], fill=_hex_to_rgb(T.STATUS_PAUSED))
        draw.rectangle([128, 93, 132, 107], fill=_hex_to_rgb(T.STATUS_PAUSED))
        self._text(draw, 128, 142, "Memory paused",     "lg", T.STATUS_PAUSED)
        self._text(draw, 128, 166, "Nothing is captured","sm", T.TEXT_GHOST)

    def _error_card(self, draw, card):
        self._circle(draw, 128, 128, 118, 1, T.ACCENT_ERROR, alpha=77)
        # Triangle outline at (128, 88), height 24
        cx, cy, h = 128, 88, 24
        pts = [(cx, cy-h//2), (cx+h*0.6, cy+h//2), (cx-h*0.6, cy+h//2)]
        draw.polygon(pts, outline=_hex_to_rgb(T.ACCENT_ERROR), width=2)
        self._text(draw, 128, 108, "Something went wrong", "sm", T.TEXT_SECONDARY)
        self._text(draw, 128, 128, card.get("primary","Try again"), "md", T.ACCENT_ERROR)

    def _low_confidence(self, draw, card):
        self._text(draw, 128, 110, "Not sure",      "lg", T.TEXT_SECONDARY)
        self._text(draw, 128, 142, "Try rephrasing", "sm", T.TEXT_GHOST)
        for dx in [-20, 0, 20]:
            self._dot(draw, 128+dx, 170, 3, T.TEXT_GHOST)
