from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from . import themes as T

W = H = 256
CENTER = (128, 128)

def _font(size):
    try:    return ImageFont.truetype("DejaVuSans.ttf", size)
    except: return ImageFont.load_default()

_SIZES = {"xl": 30, "lg": 24, "md": 18, "sm": 13}

def render(payload: dict) -> Image.Image:
    img = Image.new("RGB", (W, H), T.BACKGROUND)
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, W-2, H-2], outline=T.BORDER_SUBTLE, width=1)
    if payload.get("type") == "PrivacyPausedCard":
        d.rounded_rectangle([26, 78, W-26, H-78], radius=14, outline=T.STATUS_PAUSED, width=2)
    lines = []
    if payload.get("eyebrow"): lines.append((payload["eyebrow"], "sm", payload.get("accent", T.ACCENT_MEMORY)))
    if payload.get("primary"): lines.append((payload["primary"], "xl", T.TEXT_PRIMARY))
    for l in payload.get("lines") or []:
        if l: lines.append((l, "md", T.TEXT_SECONDARY))
    if payload.get("footer"): lines.append((payload["footer"], "sm", T.TEXT_SECONDARY))
    heights = [_SIZES[s] + 8 for _, s, _ in lines]
    y = CENTER[1] - sum(heights)//2
    for (text, size, color), lh in zip(lines, heights):
        f = _font(_SIZES[size])
        tw = d.textlength(text, font=f)
        d.text((CENTER[0]-tw/2, y), text, fill=color, font=f)
        y += lh
    conf = payload.get("confidence")
    if conf is not None:
        c = T.ACCENT_SUCCESS if conf >= 0.75 else (T.ACCENT_MEMORY if conf >= 0.4 else T.STATUS_PAUSED)
        d.ellipse([CENTER[0]-3, H-40, CENTER[0]+3, H-34], fill=c)
    return img
