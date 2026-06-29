
"""renderer.py — Pillow-based 256x256 HUD renderer."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from . import themes as T

SIZE = 256

FONT_PX = {
    "hero": 22,
    "xl":   19,
    "lg":   17,
    "md":   13,
    "sm":   10,
}


def _hex_to_rgb(h: int) -> tuple[int, int, int]:
    return T.to_rgb(h)


def _font(size_token: str) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    px = FONT_PX.get(size_token, 13)
    candidates = [
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, px)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _mask() -> Image.Image:
    m = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(m).ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    return m


class CardRenderer:
    def __init__(self):
        self._mask = _mask()

    def render(self, card: dict) -> Image.Image:
        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img, "RGBA")
        dispatch = {
            "ReadyCard":            self._ready,
            "SavedMemoryCard":      self._saved_memory,
            "QueryListeningCard":   self._query_listening,
            "LoadingCard":          self._loading,
            "ObjectRecallCard":     self._object_recall,
            "CommitmentRecallCard": self._commitment_recall,
            "ProactiveMemoryCard":  self._proactive_memory,
            "PersonContextCard":    self._person_context,
            "PrivacyPausedCard":    self._privacy_paused,
            "ErrorCard":            self._error_card,
            "LowConfidenceCard":    self._low_confidence,
        }
        fn = dispatch.get(card.get("type", ""))
        if fn:
            fn(draw, card)
        img.putalpha(self._mask)
        return img

    def save(self, card: dict, path: str | Path) -> None:
        self.render(card).save(str(path))

    def _text(self, draw, x, y, text, size, color, anchor="mm"):
        draw.text((x, y), str(text), font=_font(size),
                  fill=_hex_to_rgb(color), anchor=anchor)

    def _multiline_text(self, draw, x, y, text, size, color, max_width=192):
        font = _font(size)
        words = str(text).split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            try:
                w = font.getlength(test)
            except AttributeError:
                w = len(test) * FONT_PX.get(size, 13) * 0.6
            if w <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            return
        line_h = FONT_PX.get(size, 13) + 5
        total_h = len(lines) * line_h
        start_y = y - total_h / 2 + line_h / 2
        for i, line in enumerate(lines):
            draw.text((x, start_y + i * line_h), line, font=font,
                      fill=_hex_to_rgb(color), anchor="mm")

    def _hline(self, draw, x1, x2, y, color, alpha=255):
        r, g, b = _hex_to_rgb(color)
        draw.line([(x1, y), (x2, y)], fill=(r, g, b, alpha), width=1)

    def _vbar(self, draw, x, y1, y2, width, color, alpha=255):
        r, g, b = _hex_to_rgb(color)
        draw.rectangle([x, y1, x + width - 1, y2], fill=(r, g, b, alpha))

    def _dot(self, draw, x, y, r, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(r_, g_, b_, alpha))

    def _circle(self, draw, cx, cy, r, stroke, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(r_, g_, b_, alpha), width=stroke)

    def _arc(self, draw, cx, cy, r, start_deg, end_deg, stroke, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.arc([cx - r, cy - r, cx + r, cy + r],
                 start=start_deg, end=end_deg,
                 fill=(r_, g_, b_, alpha), width=stroke)

    def _pause_glyph(self, draw, cx, cy, color):
        r_, g_, b_ = _hex_to_rgb(color)
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20],
                     outline=(r_, g_, b_, 255), width=2)
        draw.rectangle([cx - 8, cy - 8, cx - 4, cy + 8], fill=(r_, g_, b_, 255))
        draw.rectangle([cx + 2, cy - 8, cx + 6, cy + 8], fill=(r_, g_, b_, 255))

    def _warning_triangle(self, draw, cx, cy, h, stroke, color, alpha=255):
        r_, g_, b_ = _hex_to_rgb(color)
        half_base = int(h * 0.58)
        pts = [
            (cx, cy - h // 2),
            (cx + half_base, cy + h // 2),
            (cx - half_base, cy + h // 2),
            (cx, cy - h // 2),
        ]
        draw.line(pts, fill=(r_, g_, b_, alpha), width=stroke, joint="curve")

    def _ready(self, draw, card):
        self._dot(draw, 128, 128, 10, T.ACCENT_MEMORY)
        self._dot(draw, 128, 128, 16, T.ACCENT_MEMORY_DIM, alpha=46)
        for sx, sy in [
            (128, 106), (144, 112), (150, 128), (144, 144),
            (128, 150), (112, 144), (106, 128), (112, 112),
        ]:
            self._dot(draw, sx, sy, 2, T.ACCENT_MEMORY_DIM)

    def _saved_memory(self, draw, card):
        self._text(draw, 128, 98, "SAVED", "sm", T.ACCENT_SUCCESS)
        self._hline(draw, 88, 168, 110, T.ACCENT_SUCCESS, alpha=64)
        self._multiline_text(draw, 128, 130, card.get("primary", ""),
                             "lg", T.TEXT_PRIMARY, max_width=188)
        self._dot(draw, 128, 158, 3, T.ACCENT_SUCCESS)
        self._arc(draw, 128, 128, 108, 200, 340, 1, T.ACCENT_SUCCESS, alpha=64)

    def _query_listening(self, draw, card):
        self._dot(draw, 128, 92, 3, T.ACCENT_ATTENTION, alpha=153)
        self._text(draw, 128, 104, "Listening", "sm", T.ACCENT_ATTENTION)
        for cx_b, bh in zip([101, 109, 117, 128, 139, 147, 155],
                            [10, 16, 20, 22, 20, 14, 10]):
            draw.rectangle([cx_b - 1, 138 - bh // 2, cx_b + 1, 138 + bh // 2],
                           fill=_hex_to_rgb(T.ACCENT_ATTENTION))

    def _loading(self, draw, card):
        self._circle(draw, 128, 128, 52, 1, T.BORDER_SUBTLE, alpha=128)
        self._arc(draw, 128, 128, 52, -70, 20, 2, T.ACCENT_MEMORY)

    def _object_recall(self, draw, card):
        obj_name = (card.get("object") or card.get("primary") or "").upper()
        place    = card.get("place") or ""
        detail   = card.get("detail") or ""
        footer   = card.get("last_seen") or card.get("footer") or ""
        conf     = card.get("confidence")

        self._text(draw, 128, 72, obj_name, "sm", T.ACCENT_MEMORY)
        self._hline(draw, 48, 208, 86, T.BORDER_SUBTLE)
        self._vbar(draw, 20, 98, 130, 2, T.MEMORY_RAIL)
        self._multiline_text(draw, 128, 114, place, "hero", T.TEXT_PRIMARY, max_width=192)
        self._text(draw, 128, 146, detail, "md", T.TEXT_SECONDARY)
        self._text(draw, 128, 170, footer, "sm", T.TEXT_GHOST)
        self._dot(draw, 128, 192, 3, T.conf_color(conf))

    def _commitment_recall(self, draw, card):
        person = card.get("person") or ""
        task   = card.get("primary") or ""
        due    = card.get("due") or ""
        conf   = card.get("confidence")

        self._text(draw, 128, 74, f"YOU PROMISED {person.upper()}", "sm", T.ACCENT_MEMORY)
        self._hline(draw, 48, 208, 88, T.BORDER_SUBTLE)
        self._vbar(draw, 20, 100, 158, 2, T.MEMORY_RAIL)
        self._multiline_text(draw, 128, 118, task, "lg", T.TEXT_PRIMARY, max_width=192)
        self._text(draw, 128, 166, due, "sm", T.ACCENT_MEMORY)
        self._dot(draw, 128, 186, 2, T.conf_color(conf))

    def _proactive_memory(self, draw, card):
        summary = card.get("primary") or ""
        person  = card.get("person")

        self._text(draw, 128, 68, "LAST TIME HERE", "sm", T.TEXT_GHOST)
        self._arc(draw, 128, 128, 96, 200, 340, 1, T.ACCENT_MEMORY, alpha=77)
        self._hline(draw, 72, 184, 82, T.BORDER_SUBTLE)
        self._multiline_text(draw, 128, 116, summary, "lg", T.TEXT_SECONDARY, max_width=180)
        if person:
            self._text(draw, 128, 174, f"With {person}", "sm", T.ACCENT_MEMORY)

    def _person_context(self, draw, card):
        self._arc(draw, 128, 128, 108, 240, 300, 1, T.ACCENT_MEMORY, alpha=100)
        self._text(draw, 128, 84, card.get("primary") or "", "lg", T.ACCENT_MEMORY)
        self._hline(draw, 72, 184, 98, T.BORDER_SUBTLE)
        self._multiline_text(draw, 128, 122, card.get("headline") or "",
                             "md", T.TEXT_PRIMARY, max_width=192)
        self._text(draw, 128, 148, card.get("detail") or "", "sm", T.TEXT_SECONDARY)

    def _privacy_paused(self, draw, card):
        self._circle(draw, 128, 128, 116, 1, T.STATUS_PAUSED, alpha=89)
        self._pause_glyph(draw, 128, 100, T.STATUS_PAUSED)
        self._text(draw, 128, 146, "Memory paused", "lg", T.STATUS_PAUSED)
        self._text(draw, 128, 168, "Nothing is captured", "sm", T.TEXT_GHOST)

    def _error_card(self, draw, card):
        self._circle(draw, 128, 128, 116, 1, T.ACCENT_ERROR, alpha=64)
        self._warning_triangle(draw, 128, 90, 20, 2, T.ACCENT_ERROR)
        self._text(draw, 128, 122, "Connection issue", "lg", T.TEXT_PRIMARY)
        self._text(draw, 128, 146, card.get("primary", "Try again"), "sm", T.TEXT_GHOST)

    def _low_confidence(self, draw, card):
        self._text(draw, 128, 106, "Not sure", "lg", T.TEXT_SECONDARY)
        self._text(draw, 128, 136, "Try rephrasing", "sm", T.TEXT_GHOST)
        self._dot(draw, 107, 168, 2, T.TEXT_GHOST)
        self._dot(draw, 128, 172, 2, T.TEXT_GHOST)
        self._dot(draw, 149, 168, 2, T.TEXT_GHOST)
