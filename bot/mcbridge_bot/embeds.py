"""Builds the Discord embeds: status cards, alerts, and the join/leave/death feed."""
from __future__ import annotations

import datetime as dt

import discord

from .alerts import GREEN, GREY, RED, YELLOW, Alert

MAX_LISTED_PLAYERS = 20


def head_url(uuid: str) -> str:
    return f"https://mc-heads.net/avatar/{uuid}/64"


def fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def tps_dot(tps: float) -> str:
    return "🟢" if tps >= 18 else "🟡" if tps >= 15 else "🔴"


def bar(used: float, total: float, width: int = 10) -> str:
    frac = 0 if total <= 0 else min(1.0, used / total)
    filled = round(frac * width)
    return "█" * filled + "░" * (width - filled)


def safe(text: str) -> str:
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text))


def status_embed(name: str, hello: dict | None, heartbeat: dict | None, *,
                 online: bool, lagging: bool = False, offline_reason: str | None = None) -> discord.Embed:
    now = dt.datetime.now(dt.timezone.utc)
    if not online:
        reason = {"crashed": "crashed", "stopped": "stopped", "plugin_disconnected": "plugin disconnected",
                  "unlinked": "unlinked"}.get(offline_reason or "", "offline")
        e = discord.Embed(title=f"🔴 {name}", description=f"**Offline** ({reason})", color=RED, timestamp=now)
        e.set_footer(text="MCBridge • last update")
        return e
    if heartbeat is None:
        e = discord.Embed(title=f"🟢 {name}", description="**Online** - waiting for the first stats...",
                          color=GREEN, timestamp=now)
        e.set_footer(text="MCBridge • last update")
        return e

    tps = heartbeat["tps"]
    players = heartbeat["players"]
    mem = heartbeat["memory"]
    color = YELLOW if lagging or tps[0] < 15 else GREEN
    state = "🟡 **Lagging**" if lagging else "🟢 **Online**"
    e = discord.Embed(title=f"{'🟡' if lagging else '🟢'} {name}", description=state, color=color, timestamp=now)

    names = ", ".join(safe(p["name"]) for p in players[:MAX_LISTED_PLAYERS]) or "*nobody online*"
    if len(players) > MAX_LISTED_PLAYERS:
        names += f" and {len(players) - MAX_LISTED_PLAYERS} more"
    e.add_field(name=f"Players ({len(players)}/{heartbeat['max_players']})", value=names, inline=False)
    e.add_field(name="TPS (1m / 5m / 15m)",
                value=f"{tps_dot(tps[0])} {tps[0]:.1f} / {tps[1]:.1f} / {tps[2]:.1f}", inline=True)
    e.add_field(name="MSPT", value=f"{heartbeat['mspt']:.1f} ms", inline=True)
    e.add_field(name="Uptime", value=fmt_duration(heartbeat["uptime_s"]), inline=True)
    e.add_field(name="Memory",
                value=f"`{bar(mem['used_mb'], mem['max_mb'])}` {mem['used_mb'] / 1024:.1f} / "
                      f"{mem['max_mb'] / 1024:.1f} GB", inline=False)
    if hello:
        e.set_footer(text=f"{hello.get('platform', '?').title()} {hello.get('mc_version', '')} • "
                          f"MCBridge {hello.get('plugin_version', '')} • last update")
    return e


def alert_embed(server_name: str, alert: Alert) -> discord.Embed:
    e = discord.Embed(title=alert.title, description=alert.description, color=alert.color,
                      timestamp=dt.datetime.now(dt.timezone.utc))
    e.set_author(name=server_name)
    return e


def feed_embed(event_type: str, data: dict) -> discord.Embed | None:
    p = data.get("player") or {}
    who = safe(p.get("name", "?"))
    if event_type == "event.player_join":
        text, color = (f"**{who}** joined for the first time! 🎉" if data.get("first_join")
                       else f"**{who}** joined"), GREEN
    elif event_type == "event.player_leave":
        how = {"kick": " (kicked)", "ban": " (banned)"}.get(data.get("reason", ""), "")
        text, color = f"**{who}** left{how} after {fmt_duration(data.get('session_s', 0))}", GREY
    elif event_type == "event.player_death":
        text, color = f"💀 {safe(data.get('message', who + ' died'))}", RED
    elif event_type == "event.player_advancement":
        text, color = f"🏆 **{who}** made the advancement **{safe(data.get('title', '?'))}**", YELLOW
    else:
        return None
    e = discord.Embed(description=text, color=color)
    if p.get("uuid"):
        e.set_author(name=p.get("name", "?"), icon_url=head_url(p["uuid"]))
    return e