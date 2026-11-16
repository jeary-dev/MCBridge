"""Draws the activity charts attached to status cards and daily recaps (Pillow, no browser needed).

Two stacked panels sharing one time axis: players online, then TPS. Gaps where the
server was offline stay empty instead of being drawn as a misleading straight line.
"""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

SCALE = 2
W, H = 600, 300

SURFACE = "#1a1a19"
TEXT = "#f0efec"
TEXT_2 = "#c3c2b7"
MUTED = "#898781"
GRID = "#2c2c2a"
AXIS = "#383835"
SERIES = "#3987e5"
WARNING = "#fab219"

PAD_L, PAD_R, PAD_T, GAP, PAD_B = 44, 16, 30, 34, 26


def _font(size: int):
    try:
        return ImageFont.load_default(size=size * SCALE)
    except TypeError:
        return ImageFont.load_default()


def _hex(c: str, alpha: int = 255) -> tuple[int, int, int, int]:
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha


def _runs(points: list[tuple[int, float]], step: int) -> list[list[tuple[int, float]]]:
    runs: list[list[tuple[int, float]]] = []
    for ts, v in points:
        if runs and ts - runs[-1][-1][0] <= step * 2:
            runs[-1].append((ts, v))
        else:
            runs.append([(ts, v)])
    return runs


def _time_label(seconds_before_end: int, span: int) -> str:
    if seconds_before_end == 0:
        return "now"
    if span <= 3 * 3600:
        return f"-{seconds_before_end // 60}m"
    return f"-{seconds_before_end // 3600}h"


def activity_chart(samples: list[dict], start: int, end: int, *, max_players: int | None = None,
                   step: int = 60) -> bytes:
    img = Image.new("RGBA", (W * SCALE, H * SCALE), _hex(SURFACE))
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    o = ImageDraw.Draw(over)
    f_title, f_small = _font(12), _font(10)

    span = max(60, end - start)
    plot_w = W - PAD_L - PAD_R
    panel_h = (H - PAD_T - GAP - PAD_B) / 2

    def x(ts: int) -> float:
        return (PAD_L + (ts - start) / span * plot_w) * SCALE

    lines: list[list[tuple[float, float]]] = []
    dots: list[tuple[float, float]] = []
    panels = [
        ("Players online", "players", PAD_T, max(4, max_players or 0, *(s["players"] for s in samples)) if samples
         else max(4, max_players or 0)),
        ("TPS", "tps", PAD_T + panel_h + GAP, 20),
    ]

    for title, key, top, vmax in panels:
        bottom = top + panel_h

        def y(v: float, top=top, bottom=bottom, vmax=vmax) -> float:
            return (bottom - (min(v, vmax) / vmax) * (bottom - top)) * SCALE

        latest = samples[-1][key] if samples else None
        label = f"{title}" + (f"  {latest:.1f}" if key == "tps" and latest is not None
                              else f"  {latest}" if latest is not None else "")
        d.text((PAD_L * SCALE, (top - 18) * SCALE), label, font=f_title, fill=TEXT)

        ticks = [0, vmax // 2, vmax] if key == "players" else [0, 10, 20]
        for t in ticks:
            yy = y(t)
            d.line([(PAD_L * SCALE, yy), ((W - PAD_R) * SCALE, yy)], fill=AXIS if t == 0 else GRID, width=SCALE)
            d.text(((PAD_L - 6) * SCALE, yy), str(int(t)), font=f_small, fill=MUTED, anchor="rm")

        points = [(s["ts"], float(s[key])) for s in samples]
        if key == "tps":
            for ts, v in points:
                if v < 15:
                    half = step / span * plot_w * SCALE / 2
                    o.rectangle([max(PAD_L * SCALE, x(ts) - half), top * SCALE,
                                 min((W - PAD_R) * SCALE, x(ts) + half), bottom * SCALE],
                                fill=_hex(WARNING, 46))
            yy = y(15)
            for xx in range(PAD_L * SCALE, (W - PAD_R) * SCALE, 8 * SCALE):
                d.line([(xx, yy), (xx + 4 * SCALE, yy)], fill=_hex(WARNING, 200), width=SCALE)
            d.text(((PAD_L + 4) * SCALE, yy + 4 * SCALE), "lag below 15", font=f_small, fill=TEXT_2, anchor="lt")

        for run in _runs(points, step):
            coords = [(x(ts), y(v)) for ts, v in run]
            if key == "players" and len(coords) > 1:
                o.polygon(coords + [(coords[-1][0], y(0)), (coords[0][0], y(0))], fill=_hex(SERIES, 56))
            if len(coords) == 1:
                dots.append(coords[0])
            else:
                lines.append(coords)

        if not samples:
            d.text(((PAD_L + plot_w / 2) * SCALE, ((top + bottom) / 2) * SCALE), "No data yet",
                   font=f_small, fill=MUTED, anchor="mm")

    for i in range(5):
        ts = start + span * i // 4
        anchor = "lt" if i == 0 else "rt" if i == 4 else "mt"
        d.text((x(ts), (H - PAD_B + 8) * SCALE), _time_label(end - ts, span), font=f_small, fill=MUTED,
               anchor=anchor)

    img = Image.alpha_composite(img, over)
    d = ImageDraw.Draw(img)
    for coords in lines:
        d.line(coords, fill=SERIES, width=2 * SCALE, joint="curve")
    for cx, cy in dots:
        d.ellipse([cx - 4 * SCALE, cy - 4 * SCALE, cx + 4 * SCALE, cy + 4 * SCALE], fill=SERIES)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG", optimize=True)
    return buf.getvalue()


def bucket(samples: list[dict], size: int) -> list[dict]:
    """Squash per-minute samples into bigger buckets: busiest player count, worst TPS."""
    out: dict[int, dict] = {}
    for s in samples:
        key = s["ts"] - s["ts"] % size
        b = out.setdefault(key, {"ts": key, "players": 0, "tps": 20.0})
        b["players"] = max(b["players"], s["players"])
        b["tps"] = min(b["tps"], s["tps"])
    return [out[k] for k in sorted(out)]
