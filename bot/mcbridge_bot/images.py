"""Draws the image cards for /player, /advancements and /inventory (Pillow, no browser needed).

Everything here is original artwork drawn with shapes: hearts, bars, item tiles and tab emblems.
No Minecraft textures are used. Player skins come from mc-heads.net and are passed in as PNG bytes;
when there's no skin a plain silhouette is drawn instead.
"""
from __future__ import annotations

import colorsys
import datetime as dt
import hashlib
import io
import math
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONT_DIR = Path(__file__).parent / "fonts"
SS = 4
OUT = 2

BG_TOP = "#1d1d1c"
BG_BOTTOM = "#151514"
PANEL = "#242422"
PANEL_2 = "#2b2b29"
BORDER = "#33332f"
SLOT = "#1a1a19"
TEXT = "#f0efec"
TEXT_2 = "#c3c2b7"
MUTED = "#898781"
TRACK = "#33332f"
DEFAULT_ACCENT = "#3987e5"

GREEN = "#3ddc84"
RED = "#e5484d"
HEART = "#e5484d"
HUNGER = "#e8973a"
XP = "#7ccf3c"
ENCHANT = "#b07cff"
GOLD = "#f2c94c"


def rgb(c, alpha: int = 255) -> tuple[int, int, int, int]:
    if isinstance(c, tuple):
        return (*c[:3], alpha)
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha


def shade(c, factor: float) -> tuple[int, int, int, int]:
    r, g, b, a = rgb(c)
    if factor >= 1:
        f = factor - 1
        return int(r + (255 - r) * f), int(g + (255 - g) * f), int(b + (255 - b) * f), a
    return int(r * factor), int(g * factor), int(b * factor), a


def mix(a, b, t: float) -> tuple[int, int, int, int]:
    a, b = rgb(a), rgb(b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(4))


@lru_cache(maxsize=64)
def font(size: float, weight: str = "Regular"):
    try:
        return ImageFont.truetype(str(FONT_DIR / f"Inter-{weight}.otf"), int(size * SS))
    except OSError:
        try:
            return ImageFont.load_default(size=int(size * SS))
        except TypeError:
            return ImageFont.load_default()


class Card:
    def __init__(self, w: int, h: int, accent: str = DEFAULT_ACCENT, radius: int = 18):
        self.w, self.h, self.accent = w, h, accent
        grad = Image.new("RGBA", (1, 256))
        for y in range(256):
            grad.putpixel((0, y), mix(BG_TOP, BG_BOTTOM, y / 255))
        bg = grad.resize((w * SS, h * SS))
        glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([-w * SS * 0.3, -h * SS * 0.9, w * SS * 0.7, h * SS * 0.5],
                                     fill=rgb(accent, 34))
        bg = Image.alpha_composite(bg, glow.filter(ImageFilter.GaussianBlur(60 * SS)))
        mask = Image.new("L", bg.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius * SS, fill=255)
        self.img = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        self.img.paste(bg, (0, 0), mask)
        self.d = ImageDraw.Draw(self.img)
        self.d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius * SS, outline=rgb(BORDER), width=SS)

    @staticmethod
    def s(*v: float) -> list[float]:
        return [x * SS for x in v]

    def rect(self, x, y, w, h, r=8, fill=PANEL, outline=None, width=1):
        self.d.rounded_rectangle(self.s(x, y, x + w, y + h), r * SS, fill=rgb(fill) if fill else None,
                                 outline=rgb(outline) if outline else None, width=int(width * SS))

    def text(self, x, y, txt, size=14, weight="Regular", fill=TEXT, anchor="la"):
        self.d.text((x * SS, y * SS), txt, font=font(size, weight), fill=rgb(fill), anchor=anchor)

    def text_w(self, txt, size=14, weight="Regular") -> float:
        return font(size, weight).getlength(txt) / SS

    def fit(self, txt, max_w, size=14, weight="Regular") -> str:
        if self.text_w(txt, size, weight) <= max_w:
            return txt
        while txt and self.text_w(txt + "…", size, weight) > max_w:
            txt = txt[:-1]
        return txt.rstrip() + "…"

    def bar(self, x, y, w, h, frac, color, track=TRACK):
        self.rect(x, y, w, h, h / 2, fill=track)
        frac = max(0.0, min(1.0, frac))
        if frac > 0:
            self.rect(x, y, max(h, w * frac), h, h / 2, fill=color)

    def pill(self, x, y, txt, color, size=12, dot=False) -> float:
        pad = 8
        tw = self.text_w(txt, size, "SemiBold")
        w = tw + pad * 2 + (12 if dot else 0)
        h = size + 10
        self.rect(x, y, w, h, h / 2, fill=mix(color, PANEL, 0.78), outline=mix(color, PANEL, 0.45))
        tx = x + pad
        if dot:
            self.d.ellipse(self.s(tx, y + h / 2 - 3.5, tx + 7, y + h / 2 + 3.5), fill=rgb(color))
            tx += 12
        self.text(tx, y + h / 2, txt, size, "SemiBold", mix(color, TEXT, 0.55), "lm")
        return w

    def paste(self, im: Image.Image, x, y, w=None, h=None):
        im = im.convert("RGBA")
        if w and h:
            im = im.resize((int(w * SS), int(h * SS)), Image.LANCZOS)
        self.img.alpha_composite(im, (int(x * SS), int(y * SS)))

    def layer(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        lay = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        return lay, ImageDraw.Draw(lay)

    def merge(self, lay: Image.Image):
        self.img.alpha_composite(lay)
        self.d = ImageDraw.Draw(self.img)

    def png(self) -> bytes:
        out = self.img.resize((self.w * OUT, self.h * OUT), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, "PNG", optimize=True)
        return buf.getvalue()


def _heart_mask(size: int) -> Image.Image:
    s = size
    m = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(m)
    r = s * 0.27
    for cx in (0.29, 0.71):
        d.ellipse([cx * s - r, 0.33 * s - r, cx * s + r, 0.33 * s + r], fill=255)
    d.polygon([(0.03 * s, 0.40 * s), (0.97 * s, 0.40 * s), (0.5 * s, 0.94 * s)], fill=255)
    return m


def draw_heart(card: Card, x, y, size, frac: float):
    s = int(size * SS)
    mask = _heart_mask(s)
    outline = mask.filter(ImageFilter.MaxFilter(2 * (SS // 2) + 1))
    lay = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    lay.paste(rgb("#141413"), (0, 0), outline)
    lay.paste(rgb("#3a2627"), (0, 0), mask)
    if frac > 0:
        fill = Image.new("L", (s, s), 0)
        ImageDraw.Draw(fill).rectangle([0, 0, s * frac, s], fill=255)
        part = ImageChops.multiply(mask, fill)
        lay.paste(rgb(HEART), (0, 0), part)
        hi = Image.new("L", (s, s), 0)
        ImageDraw.Draw(hi).ellipse([s * 0.18, s * 0.17, s * 0.38, s * 0.37], fill=150)
        lay.paste(rgb("#ff9a9d"), (0, 0), ImageChops.multiply(hi, part))
    card.img.alpha_composite(lay, (int(x * SS), int(y * SS)))


def draw_ping(card: Card, x, y, ping: int | None):
    level = 0 if ping is None or ping < 0 else 4 if ping < 150 else 3 if ping < 300 else 2 if ping < 600 else 1
    color = GREEN if level >= 3 else GOLD if level == 2 else RED
    for i in range(4):
        h = 4 + i * 3
        card.rect(x + i * 5, y + 13 - h, 3, h, 1, fill=color if i < level else TRACK)


def silhouette(w: int, h: int, accent: str) -> Image.Image:
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    u = min(w / 16, h / 32)
    ox, oy = (w - 16 * u) / 2, (h - 32 * u) / 2
    body, limb = rgb(mix(accent, "#3a3a37", 0.75)), rgb(mix(accent, "#2c2c2a", 0.8))

    def r(x, y, ww, hh, c):
        d.rounded_rectangle([ox + x * u, oy + y * u, ox + (x + ww) * u, oy + (y + hh) * u], u * 0.6, fill=c)
    r(4, 0, 8, 8, body)
    r(4, 8.4, 8, 12, body)
    r(0, 8.4, 3.6, 12, limb)
    r(12.4, 8.4, 3.6, 12, limb)
    r(4, 20.8, 3.8, 11.2, limb)
    r(8.2, 20.8, 3.8, 11.2, limb)
    return im


def skin_image(skin: bytes | None, w: int, h: int, accent: str) -> Image.Image:
    if skin:
        try:
            im = Image.open(io.BytesIO(skin)).convert("RGBA")
            scale = min(w / im.width, h / im.height)
            nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
            im = im.resize((nw, nh), Image.NEAREST if scale >= 2 else Image.LANCZOS)
            out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            out.alpha_composite(im, ((w - nw) // 2, h - nh))
            return out
        except Exception:
            pass
    return silhouette(w, h, accent)


def avatar_image(skin: bytes | None, size: int, accent: str) -> Image.Image:
    if skin:
        try:
            return Image.open(io.BytesIO(skin)).convert("RGBA").resize((size, size), Image.NEAREST)
        except Exception:
            pass
    im = Image.new("RGBA", (size, size), rgb(mix(accent, PANEL, 0.6)))
    return im


def _rounded(im: Image.Image, radius: int) -> Image.Image:
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius, fill=255)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "-"
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {rem // 60}m"
    return f"{rem // 60}m"


def fmt_ago(ts: int | None, now: int | None = None) -> str:
    if not ts:
        return "-"
    now = now or int(dt.datetime.now(dt.timezone.utc).timestamp())
    diff = max(0, now - int(ts))
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    if diff < 86400 * 30:
        return f"{diff // 86400}d ago"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%-d %b %Y")


def fmt_date(ts: int | None) -> str:
    if not ts:
        return "-"
    return dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).strftime("%-d %b %Y")


WORLD_COLORS = {"normal": "#5fbf4a", "nether": "#d0503a", "the_end": "#b38bea", "custom": "#8b8d98"}
WORLD_NAMES = {"normal": "Overworld", "nether": "Nether", "the_end": "The End"}
GAMEMODE_NAMES = {"survival": "Survival", "creative": "Creative", "adventure": "Adventure", "spectator": "Spectator"}


def world_label(info: dict) -> str:
    world = info.get("world") or "-"
    env = info.get("environment")
    if env in WORLD_NAMES and world in ("world", "world_nether", "world_the_end"):
        return WORLD_NAMES[env]
    return world


def _player_tiles(tracked: dict, live: dict, online: bool) -> list[tuple[str, str]]:
    tiles = []
    if tracked:
        tiles += [("Playtime", fmt_duration(tracked.get("playtime_s"))), ("Sessions", f"{tracked.get('joins', 0):,}"),
                  ("Deaths", f"{tracked.get('deaths', 0):,}")]
    if live.get("world"):
        tiles.append(("World", world_label(live)))
    if live.get("gamemode"):
        tiles.append(("Game mode", GAMEMODE_NAMES.get(live["gamemode"], live["gamemode"].title())))
    if online and live.get("ping") is not None:
        tiles.append(("Ping", f"{live['ping']} ms"))
    first = tracked.get("first_seen") or (live.get("first_played") or 0) // 1000 or None
    tiles.append(("First joined", fmt_date(first)))
    if not online:
        last = tracked.get("last_seen") or (live.get("last_played") or 0) // 1000 or None
        tiles.append(("Last seen", fmt_ago(last)))
    return tiles[:8]


def player_card(name: str, *, server: str, tracked: dict | None = None, live: dict | None = None,
                skin: bytes | None = None, discord_name: str | None = None, accent: str = DEFAULT_ACCENT) -> bytes:
    tracked, live = tracked or {}, live or {}
    has_vitals = live.get("health") is not None
    online = bool(live.get("online", tracked.get("online", False)))
    tiles = _player_tiles(tracked, live, online)
    cols, th, gap = 4, 50, 8
    rows = max(1, math.ceil(len(tiles) / cols))
    W = 640
    vitals_h = 134 if has_vitals else 0
    H = 118 + vitals_h + rows * th + (rows - 1) * gap + 18 + (0 if has_vitals else 10)
    c = Card(W, H, accent)

    px, py, pw, ph = 18, 18, 150, H - 36
    c.rect(px, py, pw, ph, 14, fill=PANEL, outline=BORDER)
    lay, ld = c.layer()
    ld.ellipse(c.s(px + 10, py + ph * 0.45, px + pw - 10, py + ph + 40), fill=rgb(accent, 60))
    c.merge(lay.filter(ImageFilter.GaussianBlur(18 * SS)))
    lay, ld = c.layer()
    ld.ellipse(c.s(px + 36, py + ph - 20, px + pw - 36, py + ph - 9), fill=(0, 0, 0, 110))
    c.merge(lay.filter(ImageFilter.GaussianBlur(2 * SS)))
    body_h = min(ph - 30, (pw - 20) * 2.2)
    c.paste(skin_image(skin, int((pw - 20) * SS), int(body_h * SS), accent), px + 10, py + ph - 16 - body_h)

    x = px + pw + 18
    right = W - 20
    c.text(x, 22, c.fit(name, right - x, 26, "Bold"), 26, "Bold")
    cx = x
    cy = 58
    cx += c.pill(cx, cy, "Online" if online else "Offline", GREEN if online else MUTED, dot=True) + 6
    if live.get("op"):
        cx += c.pill(cx, cy, "Operator", GOLD) + 6
    if live.get("banned"):
        cx += c.pill(cx, cy, "Banned", RED) + 6
    elif live.get("whitelisted"):
        cx += c.pill(cx, cy, "Whitelisted", accent) + 6
    sub = server + (f"  ·  @{discord_name}" if discord_name else "")
    c.text(x, 92, c.fit(sub, right - x, 13), 13, fill=MUTED)

    y = 118
    if has_vitals:
        hp, max_hp = float(live.get("health") or 0), float(live.get("max_health") or 20)
        c.text(x, y, "Health", 12, "Medium", MUTED)
        c.text(right, y, f"{hp:g} / {max_hp:g}", 12, "SemiBold", TEXT_2, "ra")
        per = max_hp / 10
        size, gap_h = 19.5, 2.4
        for i in range(10):
            frac = max(0.0, min(1.0, (hp - i * per) / per)) if per > 0 else 0
            frac = 1.0 if frac >= 0.75 else 0.5 if frac >= 0.25 else 0.0
            draw_heart(c, x + i * (size + gap_h), y + 18, size, frac)

        y += 48
        food = int(live.get("food") or 0)
        c.text(x, y, "Hunger", 12, "Medium", MUTED)
        c.text(right, y, f"{food} / 20", 12, "SemiBold", TEXT_2, "ra")
        seg_w = (right - x - 9 * 3) / 10
        for i in range(10):
            fill = max(0.0, min(1.0, (food - i * 2) / 2))
            sx = x + i * (seg_w + 3)
            c.rect(sx, y + 19, seg_w, 9, 3, fill=TRACK)
            if fill > 0:
                c.rect(sx, y + 19, seg_w * fill, 9, 3, fill=HUNGER)

        y += 40
        level, prog = int(live.get("level") or 0), float(live.get("exp") or 0)
        c.text(x, y, "Experience", 12, "Medium", MUTED)
        c.text(right, y, f"Level {level}  ·  {prog * 100:.0f}%", 12, "SemiBold", TEXT_2, "ra")
        c.bar(x, y + 19, right - x, 9, prog, XP)

    tw = (right - x - (cols - 1) * gap) / cols
    y = H - 18 - rows * th - (rows - 1) * gap
    for i, (label, value) in enumerate(tiles):
        tx, ty = x + (i % cols) * (tw + gap), y + (i // cols) * (th + gap)
        c.rect(tx, ty, tw, th, 10, fill=PANEL, outline=BORDER)
        c.text(tx + 10, ty + 9, label, 11, "Medium", MUTED)
        if label == "Ping":
            draw_ping(c, tx + tw - 28, ty + 7, live.get("ping"))
        if label == "World":
            col = WORLD_COLORS.get(live.get("environment") or "custom", WORLD_COLORS["custom"])
            c.d.ellipse(c.s(tx + tw - 18, ty + 11, tx + tw - 10, ty + 19), fill=rgb(col))
        size = 15
        while size > 12 and c.text_w(value, size, "SemiBold") > tw - 20:
            size -= 0.5
        c.text(tx + 10, ty + 27, c.fit(value, tw - 20, size, "SemiBold"), size, "SemiBold")
    return c.png()


TAB_STYLE = {
    "story": ("#5fbf4a", "cube"),
    "nether": ("#d0503a", "flame"),
    "end": ("#b38bea", "orb"),
    "adventure": ("#e0a83a", "compass"),
    "husbandry": ("#4fc0a0", "leaf"),
}


def tab_style(tab_id: str, accent: str) -> tuple[str, str]:
    key = tab_id.split(":")[-1].split("/")[0]
    return TAB_STYLE.get(key, (accent, "star"))


def draw_emblem(card: Card, x, y, size, color, kind):
    card.rect(x, y, size, size, size * 0.3, fill=mix(color, PANEL, 0.75), outline=mix(color, PANEL, 0.4))
    d = card.d
    u = size * SS
    ox, oy = x * SS, y * SS

    def P(px, py):
        return ox + px * u, oy + py * u
    if kind == "cube":
        d.polygon([P(.5, .2), P(.8, .35), P(.5, .5), P(.2, .35)], fill=shade(color, 1.35))
        d.polygon([P(.2, .35), P(.5, .5), P(.5, .82), P(.2, .67)], fill=rgb(color))
        d.polygon([P(.5, .5), P(.8, .35), P(.8, .67), P(.5, .82)], fill=shade(color, 0.7))
    elif kind == "flame":
        d.polygon([P(.5, .16), P(.72, .45), P(.74, .62), P(.62, .8), P(.38, .8), P(.26, .62), P(.32, .44),
                   P(.42, .52)], fill=rgb(color))
        d.polygon([P(.5, .45), P(.6, .62), P(.56, .76), P(.44, .76), P(.4, .62)], fill=shade(color, 1.5))
    elif kind == "orb":
        d.ellipse([*P(.22, .22), *P(.78, .78)], fill=rgb(color))
        d.ellipse([*P(.38, .38), *P(.62, .62)], fill=shade(color, 0.45))
        d.ellipse([*P(.45, .45), *P(.55, .55)], fill=shade(color, 1.6))
    elif kind == "compass":
        d.ellipse([*P(.2, .2), *P(.8, .8)], outline=rgb(color), width=int(u * 0.07))
        d.polygon([P(.5, .26), P(.58, .5), P(.5, .74), P(.42, .5)], fill=rgb(color))
        d.polygon([P(.5, .26), P(.58, .5), P(.42, .5)], fill=shade(color, 1.5))
    elif kind == "leaf":
        d.ellipse([*P(.24, .2), *P(.76, .8)], fill=rgb(color))
        d.line([P(.34, .72), P(.66, .3)], fill=shade(color, 0.55), width=int(u * 0.06))
    else:
        pts = []
        for i in range(10):
            r = .32 if i % 2 == 0 else .14
            a = -math.pi / 2 + i * math.pi / 5
            pts.append(P(.5 + r * math.cos(a), .52 + r * math.sin(a)))
        d.polygon(pts, fill=rgb(color))


def draw_ring(card: Card, cx, cy, r, width, frac, color):
    box = card.s(cx - r, cy - r, cx + r, cy + r)
    card.d.arc(box, 0, 360, fill=rgb(TRACK), width=int(width * SS))
    if frac > 0:
        card.d.arc(box, -90, -90 + 360 * min(1.0, frac), fill=rgb(color), width=int(width * SS))
        for a in (-90, -90 + 360 * min(1.0, frac)):
            rad = math.radians(a)
            px, py = cx + (r - width / 2) * math.cos(rad), cy + (r - width / 2) * math.sin(rad)
            card.d.ellipse(card.s(px - width / 2, py - width / 2, px + width / 2, py + width / 2), fill=rgb(color))


FRAME_COLORS = {"challenge": ENCHANT, "goal": "#4fc0a0"}


def advancements_card(data: dict, *, server: str, avatar: bytes | None = None, accent: str = DEFAULT_ACCENT,
                      now: int | None = None) -> bytes:
    tabs = [t for t in (data.get("tabs") or []) if t.get("total")][:8]
    recent = (data.get("recent") or [])[:7]
    done, total = int(data.get("done") or 0), int(data.get("total") or 0)
    rows = max(len(tabs), 1)
    W = 600
    H = max(100 + rows * 46 + 22, 100 + max(len(recent), 1) * 40 + 22)
    c = Card(W, H, accent)

    av = _rounded(avatar_image(avatar, 52 * SS, accent), 12 * SS)
    c.paste(av, 20, 20)
    c.text(84, 22, c.fit(data.get("name", "?"), 340, 24, "Bold"), 24, "Bold")
    online = data.get("online")
    c.text(84, 54, f"{server}  ·  {'online now' if online else 'offline'}", 13, fill=MUTED)
    pct = done / total if total else 0
    draw_ring(c, W - 52, 46, 28, 7, pct, accent)
    c.text(W - 52, 46, f"{pct * 100:.0f}%", 14, "Bold", anchor="mm")
    c.text(W - 94, 36, f"{done} / {total}", 15, "SemiBold", anchor="ra")
    c.text(W - 94, 56, "advancements", 11, "Medium", MUTED, "ra")

    c.d.line(c.s(20, 88, W - 20, 88), fill=rgb(BORDER), width=SS)
    lx, lw = 20, 300
    c.text(lx, 100, "PROGRESS BY TAB", 10.5, "SemiBold", MUTED)
    y = 122
    if not tabs:
        c.text(lx, y + 8, "No advancement tabs found", 13, fill=MUTED)
    for t in tabs:
        color, kind = tab_style(t.get("id", ""), accent)
        draw_emblem(c, lx, y, 34, color, kind)
        tx = lx + 46
        c.text(tx, y + 1, c.fit(t.get("title", "?"), lw - 120, 14, "SemiBold"), 14, "SemiBold")
        c.text(lx + lw, y + 2, f"{t.get('done', 0)}/{t['total']}", 12.5, "SemiBold", TEXT_2, "ra")
        c.bar(tx, y + 23, lw - 46, 7, t.get("done", 0) / t["total"], color)
        y += 46

    rx = lx + lw + 24
    rw = W - 20 - rx
    c.text(rx, 100, "RECENTLY COMPLETED", 10.5, "SemiBold", MUTED)
    y = 122
    if not recent:
        c.text(rx, y + 8, "Nothing yet", 13, fill=MUTED)
    for r in recent:
        color, _ = tab_style(r.get("tab", ""), accent)
        c.rect(rx, y, rw, 34, 9, fill=PANEL, outline=BORDER)
        c.rect(rx, y, 4, 34, 2, fill=color)
        frame = r.get("frame")
        title_w = rw - 24
        if frame in FRAME_COLORS:
            c.d.ellipse(c.s(rx + rw - 16, y + 9, rx + rw - 9, y + 16), fill=rgb(FRAME_COLORS[frame]))
            title_w -= 12
        c.text(rx + 14, y + 5, c.fit(r.get("title", "?"), title_w, 12.5, "SemiBold"), 12.5, "SemiBold")
        when = fmt_ago(r["ts"] // 1000 if r.get("ts") else None, now)
        c.text(rx + 14, y + 20, c.fit(f"{r.get('tab_title') or ''}  ·  {when}".strip(" ·"), rw - 24, 10.5),
               10.5, fill=MUTED)
        y += 40
    return c.png()


DYES = {
    "white": "#e9ecec", "light_gray": "#9d9d97", "gray": "#474f52", "black": "#1d1d21", "brown": "#835432",
    "red": "#b02e26", "orange": "#f9801d", "yellow": "#fed83d", "lime": "#80c71f", "green": "#5e7c16",
    "cyan": "#169c9c", "light_blue": "#3ab3da", "blue": "#3c44aa", "purple": "#8932b8", "magenta": "#c74ebd",
    "pink": "#f38baa",
}

MATERIALS = [
    ("netherite", "#6a6270"), ("diamond", "#4fd6d0"), ("emerald", "#2fc76b"), ("golden", "#f2c94c"),
    ("gold", "#f2c94c"), ("iron", "#d8d8d8"), ("chainmail", "#9aa0a6"), ("copper", "#d07a4f"),
    ("leather", "#8b5a2b"), ("turtle", "#47a036"), ("wooden", "#a07a4a"), ("stone_sword", "#8a8a8a"),
    ("stone_pickaxe", "#8a8a8a"), ("stone_axe", "#8a8a8a"), ("stone_shovel", "#8a8a8a"), ("stone_hoe", "#8a8a8a"),
    ("redstone", "#d0312d"), ("lapis", "#2d5bd0"), ("coal", "#2f2f33"), ("amethyst", "#9a6ad0"),
    ("quartz", "#ece6dc"), ("prismarine", "#5fae9f"), ("obsidian", "#2a1f3d"), ("crying_obsidian", "#4a1f7a"),
    ("deepslate", "#4d4d55"), ("blackstone", "#2e2a30"), ("basalt", "#5a5a60"), ("cobblestone", "#7a7a7a"),
    ("stone", "#7f7f7f"), ("andesite", "#8a8a8c"), ("diorite", "#c8c8c8"), ("granite", "#9a6a55"),
    ("tuff", "#6c6d66"), ("calcite", "#dfe0dc"), ("netherrack", "#7a3333"), ("nether_brick", "#3c1d22"),
    ("nether_wart", "#7a1f22"), ("soul", "#5b4536"), ("glowstone", "#f2c46a"), ("end_stone", "#dcdc9e"),
    ("purpur", "#a77ba7"), ("ender", "#2e8a7a"), ("chorus", "#8c6a8c"), ("shulker", "#9a6a9a"),
    ("dirt", "#7a5233"), ("mud", "#3c3837"), ("clay", "#a0a6b3"), ("grass", "#5aa83a"), ("moss", "#5c7a2e"),
    ("sand", "#e3d39a"), ("gravel", "#837f7e"), ("snow", "#f4fbfb"), ("ice", "#9ec3f5"), ("glass", "#bfe6f0"),
    ("water", "#3b6fd8"), ("lava", "#e8641c"), ("milk", "#f4f4f0"), ("slime", "#7cc35c"), ("honey", "#f0a43a"),
    ("tnt", "#c8352b"), ("bone", "#e6e2d0"), ("string", "#e8e8e8"), ("feather", "#f0f0f0"),
    ("gunpowder", "#5a5a5a"), ("paper", "#f0ecd8"), ("book", "#8a5a33"), ("blaze", "#f2a93a"),
    ("ghast", "#e8e8e8"), ("magma", "#a8481c"), ("pearl", "#2e8a7a"), ("experience", "#9be04a"),
    ("totem", "#e8c84a"), ("elytra", "#9aa0c0"), ("trident", "#58a59a"), ("shield", "#8a6a44"),
    ("bow", "#8a6a44"), ("arrow", "#b0a080"), ("stick", "#8a6a44"), ("torch", "#f2b84a"), ("lantern", "#4a4d55"),
    ("apple", "#d8402e"), ("golden_apple", "#f2c94c"), ("bread", "#c8954a"), ("carrot", "#f08a24"),
    ("potato", "#d8b060"), ("beef", "#b8483a"), ("porkchop", "#e08a7a"), ("chicken", "#e8c0a0"),
    ("mutton", "#c0503a"), ("cod", "#b8a080"), ("salmon", "#e07a5a"), ("cookie", "#c8884a"),
    ("melon", "#d84a3a"), ("berries", "#c8243a"), ("pumpkin", "#e88a1c"), ("cake", "#f0e0d0"),
    ("wheat", "#d8c060"), ("sugar", "#f4f4f4"), ("egg", "#efe3c8"), ("kelp", "#4a8a3a"),
    ("oak", "#b08850"), ("spruce", "#6e4f2e"), ("birch", "#d8c890"), ("jungle", "#a8744c"),
    ("acacia", "#b05a30"), ("dark_oak", "#4a3018"), ("mangrove", "#7a3530"), ("cherry", "#e8b0b0"),
    ("bamboo", "#c8b850"), ("crimson", "#7a3050"), ("warped", "#2a7a7a"), ("pale_oak", "#e0dcd4"),
    ("log", "#8a6a44"), ("planks", "#b08850"), ("wood", "#8a6a44"), ("brick", "#a85a4a"),
    ("potion", "#7a5ad8"), ("bottle", "#bfe6f0"), ("map", "#e8dcb0"), ("compass", "#b0b0b8"),
    ("clock", "#f2c94c"), ("name_tag", "#d8d0b0"), ("saddle", "#8b5a2b"), ("bucket", "#c0c4c8"),
    ("spawn_egg", "#c0a080"), ("music_disc", "#2a2a2e"), ("firework", "#d84a3a"), ("rail", "#9a9080"),
    ("hopper", "#4a4a50"), ("chest", "#a8783a"), ("barrel", "#8a6438"), ("furnace", "#6a6a6a"),
    ("crafting_table", "#a0703a"), ("anvil", "#4a4a4e"), ("beacon", "#9ae0e0"), ("sponge", "#d8d050"),
]

DYEABLE = ("wool", "carpet", "concrete", "terracotta", "glass", "shulker_box", "bed", "candle", "banner", "dye",
           "glazed")


def material_color(item_type: str) -> str:
    t = item_type.lower()
    if any(k in t for k in DYEABLE) or t.endswith("_dye"):
        for name in sorted(DYES, key=len, reverse=True):
            if t.startswith(name + "_"):
                return DYES[name]
    if t.startswith("golden_apple") or t.startswith("enchanted_golden"):
        return "#f2c94c"
    for key, color in MATERIALS:
        if key in t:
            return color
    h = int(hashlib.md5(t.encode()).hexdigest()[:6], 16)
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, 0.55, 0.35)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


FOODS = ("apple", "bread", "carrot", "potato", "beef", "porkchop", "chicken", "mutton", "rabbit", "cod", "salmon",
         "cookie", "melon_slice", "berries", "stew", "soup", "pie", "beetroot", "kelp", "tropical_fish", "pufferfish",
         "rotten_flesh", "spider_eye", "chorus_fruit", "honey_bottle")
GEMS = ("diamond", "emerald", "quartz", "amethyst_shard", "prismarine_crystals", "lapis_lazuli", "echo_shard")
ORBS = ("ender_pearl", "ender_eye", "slime_ball", "snowball", "fire_charge", "heart_of_the_sea", "magma_cream",
        "nether_star", "egg", "turtle_scute", "armadillo_scute")
DUSTS = ("redstone", "glowstone_dust", "gunpowder", "sugar", "bone_meal", "blaze_powder")
RODS = ("stick", "blaze_rod", "breeze_rod", "bone", "end_rod", "fishing_rod", "carrot_on_a_stick", "torch",
        "lightning_rod")


def item_kind(item: dict) -> str:
    t = (item.get("type") or "").lower()
    if "shulker_box" in t:
        return "shulker"
    for suffix in ("sword", "pickaxe", "axe", "shovel", "hoe", "helmet", "chestplate", "leggings", "boots"):
        if t.endswith("_" + suffix) or t == suffix:
            return suffix
    if t in ("mace",):
        return "axe"
    if t in ("bow", "crossbow", "trident", "shield", "elytra", "totem_of_undying", "arrow", "spectral_arrow",
             "tipped_arrow"):
        return {"crossbow": "bow", "spectral_arrow": "arrow", "tipped_arrow": "arrow", "totem_of_undying": "totem"
                }.get(t, t)
    if t.endswith("_ingot") or t in ("netherite_scrap", "brick", "nether_brick", "copper_ingot"):
        return "ingot"
    if t in GEMS:
        return "gem"
    if t in DUSTS:
        return "dust"
    if t in ORBS:
        return "orb"
    if "potion" in t or t in ("experience_bottle", "glass_bottle", "dragon_breath", "ominous_bottle"):
        return "potion"
    if t.endswith("book"):
        return "book"
    if t.endswith("bucket"):
        return "bucket"
    if t in RODS:
        return "rod"
    if any(f in t for f in FOODS) or t.startswith("golden_carrot"):
        return "food"
    if item.get("block"):
        return "block"
    return "chip"


def abbreviation(item_type: str) -> str:
    words = [w for w in item_type.lower().split("_") if w not in ("of", "the", "on", "a")]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:2].title()
    return (words[0][0] + words[-1][0]).upper()


def draw_item(card: Card, x, y, size, item: dict, *, badge: str | None = None):
    color = material_color(item.get("type", ""))
    kind = item_kind(item)
    d = card.d
    u = size * SS
    ox, oy = x * SS, y * SS
    dark = shade(color, 0.6)
    light = shade(color, 1.35)
    handle = rgb("#7a5a36")

    def P(px, py):
        return ox + px * u, oy + py * u

    def line(a, b, w, fill):
        d.line([P(*a), P(*b)], fill=fill, width=max(1, int(w * u)))
        r = w * u / 2
        for px, py in (P(*a), P(*b)):
            d.ellipse([px - r, py - r, px + r, py + r], fill=fill)

    glow = item.get("enchantments") or item.get("glint")
    if glow:
        lay, ld = card.layer()
        ld.ellipse([*P(.12, .12), *P(.88, .88)], fill=rgb(ENCHANT, 90))
        card.merge(lay.filter(ImageFilter.GaussianBlur(size * SS * 0.12)))
        d = card.d

    if kind in ("block", "shulker"):
        top, left, rightc = light, rgb(color), shade(color, 0.68)
        d.polygon([P(.5, .14), P(.86, .32), P(.5, .5), P(.14, .32)], fill=top)
        d.polygon([P(.14, .32), P(.5, .5), P(.5, .88), P(.14, .7)], fill=left)
        d.polygon([P(.5, .5), P(.86, .32), P(.86, .7), P(.5, .88)], fill=rightc)
        edge = shade(color, 0.45)
        d.line([P(.14, .32), P(.5, .5), P(.86, .32)], fill=edge, width=max(1, int(u * 0.025)))
        d.line([P(.5, .5), P(.5, .88)], fill=edge, width=max(1, int(u * 0.025)))
        if kind == "shulker":
            d.line([P(.14, .5), P(.5, .68), P(.86, .5)], fill=shade(color, 0.4), width=max(1, int(u * 0.05)))
    elif kind in ("sword",):
        d.polygon([P(.78, .14), P(.86, .22), P(.42, .66), P(.34, .58)], fill=rgb(color))
        d.polygon([P(.78, .14), P(.86, .22), P(.82, .18)], fill=light)
        d.line([P(.82, .18), P(.38, .62)], fill=light, width=max(1, int(u * 0.03)))
        line((.26, .5), (.5, .74), .08, dark)
        line((.36, .64), (.18, .82), .08, handle)
    elif kind in ("pickaxe", "axe", "shovel", "hoe"):
        line((.24, .82), (.7, .3), .08, handle)
        if kind == "pickaxe":
            d.polygon([P(.22, .3), P(.42, .14), P(.66, .12), P(.86, .2), P(.88, .36), P(.8, .26), P(.62, .22),
                       P(.44, .26)], fill=rgb(color))
            d.polygon([P(.42, .14), P(.66, .12), P(.86, .2), P(.62, .18)], fill=light)
        elif kind == "axe":
            d.polygon([P(.52, .2), P(.7, .12), P(.86, .28), P(.82, .5), P(.62, .4)], fill=rgb(color))
            d.polygon([P(.7, .12), P(.86, .28), P(.76, .24)], fill=light)
        elif kind == "shovel":
            d.ellipse([*P(.58, .1), *P(.9, .42)], fill=rgb(color))
            d.ellipse([*P(.64, .14), *P(.78, .28)], fill=light)
        else:
            d.polygon([P(.5, .2), P(.84, .14), P(.86, .26), P(.6, .32)], fill=rgb(color))
    elif kind == "helmet":
        d.chord([*P(.16, .2), *P(.84, .9)], 180, 360, fill=rgb(color))
        d.rectangle([*P(.16, .54), *P(.3, .76)], fill=rgb(color))
        d.rectangle([*P(.7, .54), *P(.84, .76)], fill=rgb(color))
        d.chord([*P(.26, .28), *P(.6, .62)], 200, 300, fill=light)
    elif kind == "chestplate":
        d.polygon([P(.14, .2), P(.36, .14), P(.5, .26), P(.64, .14), P(.86, .2), P(.9, .44), P(.76, .48),
                   P(.76, .88), P(.24, .88), P(.24, .48), P(.1, .44)], fill=rgb(color))
        d.polygon([P(.24, .48), P(.5, .3), P(.5, .88), P(.24, .88)], fill=light)
        d.line([P(.5, .3), P(.5, .88)], fill=dark, width=max(1, int(u * 0.03)))
    elif kind == "leggings":
        d.polygon([P(.2, .14), P(.8, .14), P(.82, .88), P(.58, .88), P(.5, .42), P(.42, .88), P(.18, .88)],
                  fill=rgb(color))
        d.rectangle([*P(.2, .14), *P(.8, .24)], fill=dark)
        d.polygon([P(.22, .26), P(.4, .26), P(.36, .86), P(.2, .86)], fill=light)
    elif kind == "boots":
        for bx in (.12, .54):
            d.polygon([P(bx, .3), P(bx + .2, .3), P(bx + .2, .66), P(bx + .34, .7), P(bx + .34, .84), P(bx, .84)],
                      fill=rgb(color))
            d.rectangle([*P(bx, .3), *P(bx + .08, .78)], fill=light)
    elif kind == "bow":
        d.arc([*P(.1, .1), *P(.9, .9)], 225 - 70, 225 + 70, fill=handle, width=max(1, int(u * .09)))
        d.line([P(.22, .22), P(.78, .78)], fill=rgb("#e8e8e8"), width=max(1, int(u * .025)))
        line((.3, .7), (.7, .3), .04, rgb("#b0a080"))
        d.polygon([P(.7, .3), P(.6, .32), P(.68, .24)], fill=rgb("#c8c8c8"))
    elif kind == "arrow":
        line((.2, .8), (.74, .26), .05, rgb("#b0a080"))
        d.polygon([P(.82, .18), P(.64, .26), P(.74, .36)], fill=rgb("#c8c8c8"))
        d.polygon([P(.14, .72), P(.28, .86), P(.3, .7)], fill=rgb("#f0f0f0"))
    elif kind == "trident":
        line((.22, .82), (.66, .38), .07, rgb(color))
        for a, b in (((.66, .38), (.84, .2)), ((.56, .3), (.64, .14)), ((.74, .48), (.88, .38))):
            line(a, b, .06, light)
    elif kind == "shield":
        d.polygon([P(.2, .14), P(.8, .14), P(.8, .5), P(.5, .88), P(.2, .5)], fill=rgb(color))
        d.polygon([P(.28, .2), P(.72, .2), P(.72, .48), P(.5, .78), P(.28, .48)], fill=light)
        d.line([P(.5, .2), P(.5, .78)], fill=dark, width=max(1, int(u * .04)))
    elif kind == "elytra":
        for flip in (0, 1):
            pts = [(.48, .16), (.2, .24), (.12, .5), (.2, .86), (.4, .66), (.48, .5)]
            if flip:
                pts = [(1 - px, py) for px, py in pts]
            d.polygon([P(*p) for p in pts], fill=rgb(color) if flip else light)
    elif kind == "totem":
        d.ellipse([*P(.34, .1), *P(.66, .4)], fill=rgb(color))
        d.polygon([P(.3, .4), P(.7, .4), P(.66, .88), P(.34, .88)], fill=rgb(color))
        d.polygon([P(.3, .44), P(.12, .6), P(.3, .6)], fill=light)
        d.polygon([P(.7, .44), P(.88, .6), P(.7, .6)], fill=light)
        d.ellipse([*P(.4, .2), *P(.47, .27)], fill=rgb("#2a7a3a"))
        d.ellipse([*P(.53, .2), *P(.6, .27)], fill=rgb("#2a7a3a"))
    elif kind == "ingot":
        d.polygon([P(.14, .62), P(.32, .36), P(.86, .36), P(.68, .62)], fill=light)
        d.polygon([P(.14, .62), P(.68, .62), P(.68, .76), P(.14, .76)], fill=rgb(color))
        d.polygon([P(.68, .62), P(.86, .36), P(.86, .5), P(.68, .76)], fill=dark)
    elif kind == "gem":
        d.polygon([P(.5, .12), P(.84, .4), P(.5, .88), P(.16, .4)], fill=rgb(color))
        d.polygon([P(.5, .12), P(.84, .4), P(.5, .4)], fill=light)
        d.polygon([P(.16, .4), P(.5, .4), P(.5, .88)], fill=dark)
    elif kind == "dust":
        d.chord([*P(.14, .44), *P(.86, 1.1)], 180, 360, fill=rgb(color))
        for px, py in ((.36, .58), (.56, .52), (.66, .66), (.44, .7)):
            d.ellipse([*P(px - .04, py - .04), *P(px + .04, py + .04)], fill=light)
    elif kind == "orb":
        d.ellipse([*P(.18, .18), *P(.82, .82)], fill=rgb(color))
        d.ellipse([*P(.3, .26), *P(.48, .44)], fill=light)
    elif kind == "potion":
        d.rectangle([*P(.42, .1), *P(.58, .3)], fill=rgb("#c8d8e0"))
        d.rectangle([*P(.4, .08), *P(.6, .14)], fill=rgb("#8a6a44"))
        d.ellipse([*P(.2, .3), *P(.8, .9)], fill=rgb("#c8d8e0"))
        d.chord([*P(.24, .34), *P(.76, .86)], 0, 180, fill=rgb(color))
        d.ellipse([*P(.3, .42), *P(.42, .54)], fill=(255, 255, 255, 160))
    elif kind == "book":
        cover = rgb(ENCHANT) if "enchanted" in item.get("type", "") else rgb(color)
        d.rounded_rectangle([*P(.2, .14), *P(.8, .86)], int(u * .06), fill=cover)
        d.rectangle([*P(.68, .18), *P(.76, .82)], fill=rgb("#f0ecd8"))
        d.rectangle([*P(.2, .14), *P(.28, .86)], fill=shade(cover, 0.6))
    elif kind == "bucket":
        d.polygon([P(.2, .3), P(.8, .3), P(.7, .86), P(.3, .86)], fill=rgb("#c0c4c8"))
        d.arc([*P(.2, .08), *P(.8, .52)], 180, 360, fill=rgb("#8a8e92"), width=max(1, int(u * .04)))
        t = item.get("type", "")
        if t != "bucket":
            d.ellipse([*P(.22, .24), *P(.78, .38)], fill=rgb(color))
        else:
            d.ellipse([*P(.22, .24), *P(.78, .38)], fill=rgb("#5a5e62"))
    elif kind == "rod":
        line((.22, .82), (.78, .18), .09, rgb(color))
        line((.3, .74), (.7, .26), .03, light)
    elif kind == "food":
        d.ellipse([*P(.16, .2), *P(.84, .86)], fill=rgb(color))
        d.ellipse([*P(.62, .12), *P(.92, .42)], fill=rgb(SLOT))
        d.ellipse([*P(.28, .32), *P(.42, .46)], fill=light)
    else:
        d.rounded_rectangle([*P(.16, .16), *P(.84, .84)], int(u * .18), fill=mix(color, SLOT, 0.35),
                            outline=rgb(color), width=max(1, int(u * .05)))
        card.text(x + size / 2, y + size / 2 + 0.5, abbreviation(item.get("type", "?")), size * 0.3, "Bold",
                  shade(color, 1.6), "mm")

    if glow:
        for sx, sy, sr in ((.8, .2, .09), (.18, .78, .06)):
            pts = []
            for i in range(8):
                rr = sr if i % 2 == 0 else sr * 0.3
                a = i * math.pi / 4
                pts.append(P(sx + rr * math.cos(a), sy + rr * math.sin(a)))
            d.polygon(pts, fill=rgb("#efe0ff"))

    dur, max_dur = item.get("durability"), item.get("max_durability")
    if dur is not None and max_dur and dur < max_dur:
        frac = max(0.0, dur / max_dur)
        bx, by, bw = x + size * 0.14, y + size * 0.84, size * 0.72
        card.rect(bx, by, bw, size * 0.08, 1, fill="#101010")
        hue = frac / 3
        r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 0.95)
        card.rect(bx, by, max(1, bw * frac), size * 0.08, 1, fill=(int(r * 255), int(g * 255), int(b * 255)))

    amount = item.get("amount", 1)
    if amount and amount > 1:
        txt = str(amount)
        f = font(size * 0.3, "Bold")
        px, py = (x + size - 3) * SS, (y + size - 2) * SS
        d.text((px + SS, py + SS), txt, font=f, fill=(0, 0, 0, 200), anchor="rd")
        d.text((px, py), txt, font=f, fill=rgb("#ffffff"), anchor="rd")
    if badge:
        card.rect(x + 2, y + 2, 14, 14, 7, fill=card.accent)
        card.text(x + 9, y + 9.5, badge, 9, "Bold", "#ffffff", "mm")


SLOT_SIZE = 44
SLOT_GAP = 4


def draw_slot(card: Card, x, y, item: dict | None, *, size=SLOT_SIZE, selected=False, badge=None, ghost=None):
    card.rect(x, y, size, size, 8, fill=SLOT, outline=card.accent if selected else BORDER,
              width=2 if selected else 1)
    if item:
        draw_item(card, x + 3, y + 3, size - 6, item, badge=badge)
    elif ghost:
        card.text(x + size / 2, y + size / 2, ghost, 10, "Medium", "#4a4a46", "mm")


def grid(card: Card, x, y, items: list, cols=9, *, selected: int | None = None, badges: dict | None = None):
    for i, item in enumerate(items):
        draw_slot(card, x + (i % cols) * (SLOT_SIZE + SLOT_GAP), y + (i // cols) * (SLOT_SIZE + SLOT_GAP), item,
                  selected=selected == i, badge=(badges or {}).get(i))


def item_name(item: dict) -> str:
    return item.get("name") or item.get("type", "?").replace("_", " ").title()


def roman(n: int) -> str:
    vals = [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    if n <= 0 or n > 30:
        return str(n)
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def shulker_slots(data: dict) -> list[tuple[str, int, dict]]:
    found = []
    for section in ("hotbar", "main"):
        for i, item in enumerate(data.get(section) or []):
            if item and item.get("contents") is not None:
                found.append((section, i, item))
    if data.get("offhand") and data["offhand"].get("contents") is not None:
        found.append(("offhand", 0, data["offhand"]))
    return found


def inventory_card(data: dict, *, server: str, skin: bytes | None = None, accent: str = DEFAULT_ACCENT) -> bytes:
    step = SLOT_SIZE + SLOT_GAP
    grid_w = 9 * step - SLOT_GAP
    W = grid_w + 40
    top_h = 4 * step - SLOT_GAP
    H = 76 + top_h + 18 + 3 * step - SLOT_GAP + 12 + SLOT_SIZE + 22
    c = Card(W, H, accent)

    name = data.get("name", "?")
    c.text(20, 20, c.fit(f"{name}", W - 160, 22, "Bold"), 22, "Bold")
    c.text(20, 50, server, 12.5, fill=MUTED)
    online = data.get("online", True)
    c.pill(W - 20 - c.text_w("Offline" if not online else "Online", 12, "SemiBold") - 28, 22,
           "Online" if online else "Offline", GREEN if online else MUTED, dot=True)

    x0, y0 = 20, 76
    armor = (data.get("armor") or []) + [None] * 4
    ghosts = ["Head", "Chest", "Legs", "Feet"]
    for i in range(4):
        draw_slot(c, x0, y0 + i * step, armor[i], ghost=ghosts[i])
    bx, bw = x0 + step, 2 * step - SLOT_GAP + 40
    c.rect(bx, y0, bw, top_h, 10, fill=PANEL, outline=BORDER)
    lay, ld = c.layer()
    ld.ellipse(c.s(bx + 10, y0 + top_h * 0.5, bx + bw - 10, y0 + top_h + 30), fill=rgb(accent, 55))
    c.merge(lay.filter(ImageFilter.GaussianBlur(14 * SS)))
    c.paste(skin_image(skin, int((bw - 24) * SS), int((top_h - 16) * SS), accent), bx + 12, y0 + 8)
    ox = bx + bw + SLOT_GAP
    draw_slot(c, ox, y0 + 3 * step, data.get("offhand"), ghost="Off")

    shulkers = shulker_slots(data)
    badge_for = {(s, i): str(n + 1) for n, (s, i, _) in enumerate(shulkers)}

    ix = ox + step + 10
    iw = x0 + grid_w - ix
    hotbar = (data.get("hotbar") or []) + [None] * 9
    sel = data.get("selected_slot")
    held = hotbar[sel] if isinstance(sel, int) and 0 <= sel < 9 else None
    c.text(ix, y0, "IN HAND", 10.5, "SemiBold", MUTED)
    if held:
        c.text(ix, y0 + 16, c.fit(item_name(held), iw, 14, "SemiBold"), 14, "SemiBold",
               ENCHANT if held.get("enchantments") else TEXT)
        ly = y0 + 38
        for e in (held.get("enchantments") or [])[:6]:
            label = f"{e['id'].replace('_', ' ').title()} {roman(int(e.get('level', 1)))}"
            c.text(ix, ly, c.fit(label, iw, 11.5), 11.5, fill=TEXT_2)
            ly += 16
        if held.get("durability") is not None and held.get("max_durability"):
            c.text(ix, ly + 2, f"{held['durability']} / {held['max_durability']} durability", 11, fill=MUTED)
    else:
        c.text(ix, y0 + 16, "Empty hand", 14, "Medium", MUTED)
    stats = []
    total = sum(1 for it in (data.get("hotbar") or []) + (data.get("main") or []) if it)
    stats.append(f"{total}/36 slots used")
    if shulkers:
        stats.append(f"{len(shulkers)} shulker box{'es' if len(shulkers) != 1 else ''}")
    for j, line in enumerate(reversed(stats)):
        c.text(ix, y0 + top_h - j * 16, line, 11, "Medium", MUTED, "ld")

    gy = y0 + top_h + 18
    main = (data.get("main") or []) + [None] * 27
    grid(c, x0, gy, main[:27], badges={i: badge_for[("main", i)] for i in range(27) if ("main", i) in badge_for})
    hy = gy + 3 * step - SLOT_GAP + 12
    grid(c, x0, hy, hotbar[:9], selected=sel if isinstance(sel, int) else None,
         badges={i: badge_for[("hotbar", i)] for i in range(9) if ("hotbar", i) in badge_for})
    return c.png()


def container_card(title: str, items: list, *, subtitle: str, color: str | None = None,
                   accent: str = DEFAULT_ACCENT) -> bytes:
    step = SLOT_SIZE + SLOT_GAP
    rows = max(1, math.ceil(len(items) / 9))
    W = 9 * step - SLOT_GAP + 40
    H = 78 + rows * step - SLOT_GAP + 20
    c = Card(W, H, color or accent)
    if color:
        c.rect(20, 22, 6, 44, 3, fill=color)
    tx = 36 if color else 20
    c.text(tx, 20, c.fit(title, W - tx - 20, 20, "Bold"), 20, "Bold")
    used = sum(1 for i in items if i)
    c.text(tx, 48, f"{subtitle}  ·  {used}/{len(items)} slots used", 12.5, fill=MUTED)
    grid(c, 20, 78, (items + [None] * 27)[:max(27, len(items))])
    return c.png()


def shulker_color(item_type: str) -> str:
    t = item_type.lower()
    for name in sorted(DYES, key=len, reverse=True):
        if t.startswith(name + "_"):
            return DYES[name]
    return "#9a6a9a"
