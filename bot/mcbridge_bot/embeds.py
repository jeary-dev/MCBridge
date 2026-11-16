"""Builds every Discord embed MCBridge sends: status cards, alerts, the player feed, stats and recaps."""
from __future__ import annotations

import datetime as dt

import discord

from .alerts import GREEN, GREY, RED, YELLOW, Alert

BLUE = 0x3987E5
MAX_LISTED_PLAYERS = 20
ICON_FILE = "icon.png"
CHART_FILE = "activity.png"


def head_url(uuid_or_name: str, size: int = 64) -> str:
    return f"https://mc-heads.net/avatar/{uuid_or_name}/{size}"


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


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


OFFLINE_REASONS = {"crashed": "crashed", "stopped": "stopped", "plugin_disconnected": "plugin disconnected",
                   "unlinked": "unlinked"}


def status_embed(name: str, hello: dict | None, heartbeat: dict | None, *, online: bool, lagging: bool = False,
                 offline_reason: str | None = None, address: str | None = None, has_icon: bool = False,
                 has_chart: bool = False, last_seen: int | None = None) -> discord.Embed:
    join = f"\n**Join:** `{safe(address)}`" if address else ""

    if not online:
        reason = OFFLINE_REASONS.get(offline_reason or "", "offline")
        seen = f" · last seen <t:{last_seen}:R>" if last_seen else ""
        e = discord.Embed(title=name, description=f"🔴 **Offline** ({reason}){seen}{join}", color=RED,
                          timestamp=_now())
    elif heartbeat is None:
        e = discord.Embed(title=name, description=f"🟢 **Online** · waiting for the first stats...{join}",
                          color=GREEN, timestamp=_now())
    else:
        tps = heartbeat["tps"]
        players = heartbeat["players"]
        mem = heartbeat["memory"]
        state = "🟡 **Lagging**" if lagging else "🟢 **Online**"
        version = f" · {hello.get('platform', '?').title()} {hello.get('mc_version', '')}" if hello else ""
        e = discord.Embed(title=name, color=YELLOW if lagging or tps[0] < 15 else GREEN, timestamp=_now(),
                          description=f"{state}{version} · up {fmt_duration(heartbeat['uptime_s'])}{join}")
        names = ", ".join(safe(p["name"]) for p in players[:MAX_LISTED_PLAYERS]) or "*nobody online*"
        if len(players) > MAX_LISTED_PLAYERS:
            names += f" and {len(players) - MAX_LISTED_PLAYERS} more"
        e.add_field(name=f"Players · {len(players)}/{heartbeat['max_players']}", value=names, inline=False)
        e.add_field(name="TPS", value=f"{tps_dot(tps[0])} **{tps[0]:.1f}**\n-# 5m {tps[1]:.1f} · 15m {tps[2]:.1f}")
        e.add_field(name="MSPT", value=f"**{heartbeat['mspt']:.1f}** ms\n-# 50 ms = 20 TPS limit")
        e.add_field(name="Memory", value=f"**{mem['used_mb'] / 1024:.1f}** / {mem['max_mb'] / 1024:.1f} GB\n"
                                         f"-# `{bar(mem['used_mb'], mem['max_mb'], 12)}`")
    if has_icon:
        e.set_thumbnail(url=f"attachment://{ICON_FILE}")
    if has_chart:
        e.set_image(url=f"attachment://{CHART_FILE}")
    plugin = f" · plugin {hello.get('plugin_version')}" if hello and hello.get("plugin_version") else ""
    e.set_footer(text=f"MCBridge{plugin} · updated")
    return e


def alert_embed(server_name: str, alert: Alert, diagnostics: dict | None = None) -> discord.Embed:
    e = discord.Embed(title=alert.title, description=alert.description, color=alert.color, timestamp=_now())
    e.set_author(name=server_name)
    if diagnostics:
        add_diagnostics(e, diagnostics)
    return e


def add_diagnostics(e: discord.Embed, d: dict) -> None:
    worlds = d.get("worlds") or []
    if worlds:
        lines = [f"`{safe(w['name'])[:20]}` {w['chunks']:,} chunks · {w['entities']:,} entities · "
                 f"{w['tile_entities']:,} tiles · {w.get('players', 0)} players" for w in worlds[:5]]
        e.add_field(name="Worlds", value="\n".join(lines), inline=False)
    chunks = d.get("top_chunks") or []
    if chunks:
        lines = [f"`{safe(c['world'])[:16]}` x {c['x'] * 16}, z {c['z'] * 16} · **{c['entities']}** entities · "
                 f"{c['tile_entities']} tiles" for c in chunks[:5]]
        e.add_field(name="Busiest chunks", value="\n".join(lines), inline=False)
    types = d.get("top_entities") or []
    if types:
        e.add_field(name="Most common entities",
                    value=" · ".join(f"{safe(t['type']).lower()} **{t['count']:,}**" for t in types[:6]), inline=False)


def diagnostics_embed(server_name: str, d: dict) -> discord.Embed:
    worlds = d.get("worlds") or []
    total_e = sum(w["entities"] for w in worlds)
    total_c = sum(w["chunks"] for w in worlds)
    e = discord.Embed(title="🔍 Lag check", color=BLUE, timestamp=_now(),
                      description=f"**{total_c:,}** loaded chunks · **{total_e:,}** entities")
    e.set_author(name=server_name)
    add_diagnostics(e, d)
    e.set_footer(text="Lots of entities in one chunk is the most common cause of lag")
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


def player_embed(server_name: str, p: dict, discord_id: str | None = None) -> discord.Embed:
    status = "🟢 Online now" if p["online"] else f"Last seen <t:{p['last_seen']}:R>"
    e = discord.Embed(title=p["name"], description=status, color=GREEN if p["online"] else BLUE)
    e.set_thumbnail(url=f"https://mc-heads.net/body/{p['uuid']}/128")
    e.set_author(name=server_name)
    e.add_field(name="Playtime", value=fmt_duration(p["playtime_s"]))
    e.add_field(name="Sessions", value=f"{p['joins']:,}")
    e.add_field(name="Deaths", value=f"{p['deaths']:,}")
    e.add_field(name="First joined", value=f"<t:{p['first_seen']}:D>")
    if discord_id:
        e.add_field(name="Discord", value=f"<@{discord_id}>")
    return e


MEDALS = ["🥇", "🥈", "🥉"]


def top_embed(server_name: str, rows: list[dict]) -> discord.Embed:
    lines = []
    for i, r in enumerate(rows):
        rank = MEDALS[i] if i < 3 else f"`{i + 1:>2}`"
        dot = " 🟢" if r.get("online") else ""
        lines.append(f"{rank} **{safe(r['name'])}** · {fmt_duration(r['playtime_s'])}{dot}")
    e = discord.Embed(title="🏆 Top players by playtime", description="\n".join(lines) or "*No players yet*",
                      color=BLUE)
    e.set_author(name=server_name)
    if rows:
        e.set_thumbnail(url=head_url(rows[0]["uuid"], 128))
    return e


def recap_embed(server_name: str, r: dict, has_chart: bool = False) -> discord.Embed:
    uptime = 100 * r["online_minutes"] / r["window_minutes"]
    avg = f"{r['avg_tps']:.1f}" if r["avg_tps"] is not None else "-"
    e = discord.Embed(title="📊 Daily recap", color=BLUE, timestamp=_now(),
                      description=f"The last 24 hours on **{safe(server_name)}**")
    e.add_field(name="Peak players", value=f"**{r['peak_players']}**")
    e.add_field(name="Players", value=f"**{r['unique_players']}**" +
                (f" · {r['new_players']} new" if r["new_players"] else ""))
    e.add_field(name="Playtime", value=f"**{fmt_duration(r['playtime_s'])}**")
    e.add_field(name="Uptime", value=f"**{min(100.0, uptime):.1f}%**")
    e.add_field(name="Average TPS", value=f"**{avg}**")
    e.add_field(name="Lag", value=f"**{r['lag_minutes']}** min" if r["lag_minutes"] else "None 🎉")
    if r["top"]:
        e.add_field(name="Most active", inline=False,
                    value="\n".join(f"{MEDALS[i]} **{safe(p['name'])}** · {fmt_duration(p['playtime_s'])}"
                                    for i, p in enumerate(r["top"])))
    if has_chart:
        e.set_image(url=f"attachment://{CHART_FILE}")
    return e


def whitelist_request_embed(server_name: str, player: str, requester_id: str, *, status: str = "pending",
                            decided_by: str | None = None, linked_name: str | None = None,
                            note: str | None = None) -> discord.Embed:
    colors = {"pending": YELLOW, "approved": GREEN, "denied": RED}
    titles = {"pending": "📝 Whitelist request", "approved": "✅ Whitelist request approved",
              "denied": "❌ Whitelist request denied"}
    e = discord.Embed(title=titles[status], color=colors[status], timestamp=_now(),
                      description=f"<@{requester_id}> wants to join as **{safe(player)}**")
    e.set_author(name=server_name)
    e.set_thumbnail(url=head_url(player, 128))
    e.add_field(name="NameMC", value=f"[View profile](https://namemc.com/profile/{player})")
    if linked_name:
        e.add_field(name="Linked account", value=safe(linked_name))
    if decided_by:
        e.add_field(name="Decided by", value=f"<@{decided_by}>")
    if note:
        e.add_field(name="Note", value=safe(note), inline=False)
    return e


STAT_LINES = [
    ("play_time_ticks", "Play time", lambda v: fmt_duration(v // 20)),
    ("deaths", "Deaths", None),
    ("mob_kills", "Mob kills", None),
    ("player_kills", "Player kills", None),
    ("blocks_mined", "Blocks mined", None),
    ("distance_cm", "Distance travelled", lambda v: f"{v / 100_000:,.1f} km"),
    ("jumps", "Jumps", None),
    ("damage_dealt", "Damage dealt", lambda v: f"{v / 20:,.0f} ❤"),
    ("damage_taken", "Damage taken", lambda v: f"{v / 20:,.0f} ❤"),
    ("fish_caught", "Fish caught", None),
    ("animals_bred", "Animals bred", None),
    ("villager_trades", "Villager trades", None),
    ("items_enchanted", "Items enchanted", None),
]


def stats_embed(server_name: str, data: dict) -> discord.Embed:
    stats = data.get("stats") or {}
    status = "🟢 Online now" if data.get("online") else "Offline"
    e = discord.Embed(title=f"{data.get('name', '?')}'s stats", description=status, color=BLUE)
    e.set_author(name=server_name)
    if data.get("uuid"):
        e.set_thumbnail(url=f"https://mc-heads.net/body/{data['uuid']}/128")
    for key, label, fmt in STAT_LINES:
        if key in stats and stats[key] is not None:
            value = stats[key]
            e.add_field(name=label, value=fmt(value) if fmt else f"{value:,}")
    adv = data.get("advancements")
    if adv:
        pct = 100 * adv["done"] / adv["total"] if adv.get("total") else 0
        e.add_field(name="Advancements", value=f"{adv['done']}/{adv['total']} ({pct:.0f}%)")
    if not data.get("online"):
        e.set_footer(text="Blocks mined and advancements show while the player is online")
    return e


SLOT_NAMES = ["Helmet", "Chestplate", "Leggings", "Boots"]


def _item(i: dict) -> str:
    name = i.get("name") or i.get("type", "?").replace("_", " ").title()
    text = f"{safe(name)}"
    if i.get("amount", 1) > 1:
        text = f"**{i['amount']}×** {text}"
    extras = []
    if i.get("enchantments"):
        extras.append(", ".join(f"{e['id'].replace('_', ' ').title()} {e['level']}" for e in i["enchantments"][:4]))
    if i.get("durability") is not None and i.get("max_durability"):
        extras.append(f"{i['durability']}/{i['max_durability']}")
    if extras:
        text += f" · *{' · '.join(extras)}*"
    return text


def inventory_embed(server_name: str, data: dict) -> discord.Embed:
    e = discord.Embed(title=f"{data.get('name', '?')}'s inventory", color=BLUE)
    e.set_author(name=server_name)
    if data.get("uuid"):
        e.set_thumbnail(url=f"https://mc-heads.net/body/{data['uuid']}/128")
    armor = data.get("armor") or []
    lines = [f"{SLOT_NAMES[i]}: {_item(a)}" for i, a in enumerate(armor[:4]) if a]
    if data.get("offhand"):
        lines.append(f"Offhand: {_item(data['offhand'])}")
    e.add_field(name="Equipped", value="\n".join(lines) or "*nothing*", inline=False)
    hotbar = [f"`{i + 1}` {_item(it)}" for i, it in enumerate(data.get("hotbar") or []) if it]
    e.add_field(name="Hotbar", value="\n".join(hotbar)[:1024] or "*empty*", inline=False)
    main = [_item(it) for it in data.get("main") or [] if it]
    if main:
        text = "\n".join(main)
        if len(text) > 1024:
            text = text[:1000].rsplit("\n", 1)[0] + "\n…"
        e.add_field(name=f"Backpack · {len(main)} stacks", value=text, inline=False)
    else:
        e.add_field(name="Backpack", value="*empty*", inline=False)
    return e


def rolesync_embed(server_name: str, links: list[dict]) -> discord.Embed:
    arrows = {"both": "⇄", "minecraft-to-discord": "→", "discord-to-minecraft": "←"}
    lines = [f"`{safe(link['group_name'])}` {arrows.get(link['direction'], '?')} <@&{link['role_id']}>" for link in links]
    e = discord.Embed(title="🔗 Role sync", color=BLUE,
                      description="\n".join(lines) or "*No role links yet. Add one with `/rolesync add`.*")
    e.set_author(name=server_name)
    e.set_footer(text="⇄ both ways · → Minecraft to Discord · ← Discord to Minecraft")
    return e
