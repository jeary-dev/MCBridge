"""The Discord side of MCBridge: reacts to everything the gateway sees and keeps Discord up to date.

It runs in the SAME process as the gateway, so it can read live sessions directly
(no extra network hop) and react to gateway events the moment they happen.
Slash commands live in commands.py, buttons and menus in views.py.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import datetime as dt
import io
import logging
import time
from collections import defaultdict, deque

import discord
from discord import app_commands
from discord.ext import commands, tasks

from . import charts, embeds, views
from .alerts import Alert, AlertTracker
from .config import Settings
from .gateway import CommandFailed, Gateway, Session
from .protocol import MAX_CHAT_LEN, Actor, Envelope, command
from .store import ServerRecord, Store

log = logging.getLogger("mcbridge.discord")

STATUS_REFRESH_S = 60
HISTORY_S = 3600
KEEP_HISTORY_S = 8 * 86400
LINK_ATTEMPTS_PER_MINUTE = 10
FEED_EVENTS = {"event.player_join", "event.player_leave", "event.player_death", "event.player_advancement"}
SYSTEM_ACTOR = Actor(discord_id="0", name="MCBridge")


class UserError(Exception):
    pass


def actor_of(user: discord.abc.User) -> Actor:
    return Actor(discord_id=str(user.id), name=user.display_name)


def webhook_name(name: str) -> str:
    cleaned = name.replace("discord", "d1scord").replace("Discord", "D1scord").replace("clyde", "c1yde")
    return cleaned[:80] or "Player"


def file_of(data: bytes, name: str) -> discord.File:
    return discord.File(io.BytesIO(data), filename=name)


class MCBridgeBot(commands.Bot):
    def __init__(self, store: Store, gateway: Gateway, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = settings.chat_bridge
        super().__init__(command_prefix=commands.when_mentioned, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none(), help_command=None)
        self.store, self.gateway, self.settings = store, gateway, settings
        self.tracker = AlertTracker()
        self.icons: dict[str, bytes] = {}
        self._tasks: set[asyncio.Task] = set()
        self._last_sample: dict[str, int] = {}
        self._synced: dict[str, int] = {}
        self._webhooks: dict[str, discord.Webhook] = {}
        self._link_attempts: dict[str, deque[float]] = defaultdict(deque)
        gateway.on(self._on_gateway)
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self) -> None:
        from .commands import MCBridgeCommands
        self.add_dynamic_items(views.ConfigureButton, views.WhitelistDecision)
        await self.add_cog(MCBridgeCommands(self))
        if self.settings.dev_guild_id:
            guild = discord.Object(id=self.settings.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("slash commands synced to dev guild %s", self.settings.dev_guild_id)
        else:
            await self.tree.sync()
            log.info("slash commands synced globally (can take a while to show up)")
        self.status_loop.start()
        self.recap_loop.start()

    async def on_ready(self) -> None:
        log.info("logged in as %s, in %d Discord servers", self.user, len(self.guilds))
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                             name="Minecraft servers | mcbridge.dev"))

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        if isinstance(original, UserError):
            text = f"❌ {original}"
        elif isinstance(error, app_commands.MissingPermissions):
            text = "❌ You need the **" + ", ".join(p.replace("_", " ").title() for p in error.missing_permissions) \
                   + "** permission for that."
        elif isinstance(error, app_commands.CommandOnCooldown):
            text = f"⏳ Slow down - try again in {error.retry_after:.0f}s."
        else:
            log.exception("command failed", exc_info=original)
            text = "❌ Something went wrong on our side. Try again in a moment."
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)

    def spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if not task.cancelled() and task.exception():
            log.error("background task failed", exc_info=task.exception())

    async def channel_for(self, record: ServerRecord, kind: str) -> discord.abc.Messageable | None:
        cid = self.store.get_channel(record.server_id, kind)
        if not cid:
            return None
        channel = self.get_channel(int(cid))
        if channel is None:
            try:
                channel = await self.fetch_channel(int(cid))
            except (discord.NotFound, discord.Forbidden):
                return None
        if getattr(channel, "guild", None) is None or str(channel.guild.id) != record.guild_id:
            return None
        return channel

    def status_of(self, record: ServerRecord) -> tuple[discord.Embed, list[discord.File]]:
        session = self.gateway.sessions.get(record.server_id)
        now = int(time.time())
        samples = self.store.samples(record.server_id, now - HISTORY_S)
        files = []
        icon = self.icons.get(record.server_id)
        if icon:
            files.append(file_of(icon, embeds.ICON_FILE))
        if samples:
            hb = session.heartbeat if session else None
            files.append(file_of(charts.activity_chart(samples, now - HISTORY_S, now,
                                                       max_players=hb["max_players"] if hb else None),
                                 embeds.CHART_FILE))
        embed = embeds.status_embed(
            record.name,
            session.hello if session else None,
            session.heartbeat if session else None,
            online=session is not None,
            lagging=self.tracker.is_lagging(record.server_id),
            offline_reason=self.tracker.last_lost(record.server_id),
            address=record.address,
            has_icon=bool(icon),
            has_chart=bool(samples),
            last_seen=samples[-1]["ts"] if samples else None)
        return embed, files

    async def _on_gateway(self, session: Session, what: str, details: dict) -> None:
        record = self.store.get_server(session.server_id) or session.record
        sid = record.server_id
        now = int(time.time())
        alert: Alert | None = None
        if what == "heartbeat":
            alert = self.tracker.heartbeat(sid, details)
            minute = now - now % 60
            if self._last_sample.get(sid) != minute:
                self._last_sample[sid] = minute
                self.store.add_sample(sid, minute, details)
            if self._synced.get(sid) != id(session):
                self._synced[sid] = id(session)
                self.store.sync_online(sid, details["players"], now)
        elif what == "connected":
            alert = self.tracker.connected(sid)
            self._remember_icon(sid, details)
            self.spawn(self.announce_link(record))
            self.spawn(self.refresh_status(record))
        elif what == "lost":
            reason = details["reason"]
            alert = self.tracker.lost(sid, reason)
            self._synced.pop(sid, None)
            if reason != "unlinked":
                self.store.close_all_sessions(sid, now)
                self.spawn(self.refresh_status(record))
        elif what == "event.player_chat":
            self.spawn(self.post_chat(record, details))
        elif what in FEED_EVENTS:
            player = details["player"]
            if what == "event.player_join":
                self.store.player_joined(sid, player["uuid"], player["name"], now)
            elif what == "event.player_leave":
                self.store.player_left(sid, player["uuid"], now)
            elif what == "event.player_death":
                self.store.player_died(sid, player["uuid"])
            self.spawn(self.post_feed(record, what, details))
        elif what == "event.link_request":
            self.spawn(self.handle_link_request(session, record, details))
        if alert is not None:
            self.spawn(self.send_alert(record, alert, session))

    def _remember_icon(self, server_id: str, hello: dict) -> None:
        icon = hello.get("icon")
        if not icon:
            self.icons.pop(server_id, None)
            return
        try:
            data = base64.b64decode(icon, validate=True)
        except (binascii.Error, ValueError):
            return
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            self.icons[server_id] = data

    async def announce_link(self, record: ServerRecord) -> None:
        if self.store.get_setting(record.server_id, "announced"):
            return
        self.store.set_setting(record.server_id, "announced", "1")
        await self.wait_until_ready()
        channel = await self.channel_for(record, "alerts")
        if channel:
            e = discord.Embed(title=f"✅ {record.name} is linked!", color=embeds.GREEN,
                              description="Alerts will show up in this channel.\n\n"
                                          "Open the settings to pick channels for the **chat bridge**, the "
                                          "**player feed** and **whitelist requests**, choose a role to ping, "
                                          "and post a **live status** message.")
            await channel.send(embed=e, view=views.configure_button(record.server_id))

    async def send_alert(self, record: ServerRecord, alert: Alert, session: Session | None = None) -> None:
        await self.wait_until_ready()
        channel = await self.channel_for(record, "alerts")
        if channel is None:
            return
        diagnostics = None
        if alert.kind == "lagging" and session is not None and "diagnostics" in session.capabilities:
            try:
                reply = await session.command(command("cmd.diagnostics", SYSTEM_ACTOR), timeout=8)
                diagnostics = reply.get("data")
            except CommandFailed:
                pass
        role_id = self.store.get_setting(record.server_id, "alert_role")
        content, mentions = None, discord.AllowedMentions.none()
        if alert.ping and role_id:
            content = f"<@&{role_id}>"
            mentions = discord.AllowedMentions(roles=[discord.Object(id=int(role_id))])
        await channel.send(content=content, embed=embeds.alert_embed(record.name, alert, diagnostics),
                           allowed_mentions=mentions)

    async def chat_webhook(self, record: ServerRecord, channel) -> discord.Webhook | None:
        if not isinstance(channel, discord.TextChannel):
            return None
        stored = self.store.get_setting(record.server_id, "chat_webhook")
        if stored:
            channel_id, _, url = stored.partition("|")
            if channel_id == str(channel.id):
                hook = self._webhooks.get(url)
                if hook is None:
                    hook = discord.Webhook.from_url(url, client=self)
                    self._webhooks[url] = hook
                return hook
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            return None
        try:
            hooks = await channel.webhooks()
            hook = next((h for h in hooks if h.user and self.user and h.user.id == self.user.id and h.token), None)
            if hook is None:
                hook = await channel.create_webhook(name="MCBridge", reason="MCBridge chat bridge")
        except discord.HTTPException as e:
            log.warning("couldn't set up a chat webhook in %s: %s", channel.id, e)
            return None
        self.store.set_setting(record.server_id, "chat_webhook", f"{channel.id}|{hook.url}")
        self._webhooks[hook.url] = hook
        return hook

    async def post_chat(self, record: ServerRecord, data: dict) -> None:
        await self.wait_until_ready()
        channel = await self.channel_for(record, "chat")
        if channel is None:
            return
        player = data["player"]
        hook = await self.chat_webhook(record, channel)
        if hook is not None:
            try:
                await hook.send(embeds.safe(data["message"]), username=webhook_name(player["name"]),
                                avatar_url=embeds.head_url(player["uuid"], 128),
                                allowed_mentions=discord.AllowedMentions.none())
                return
            except discord.NotFound:
                self.store.set_setting(record.server_id, "chat_webhook", None)
            except discord.HTTPException as e:
                log.warning("webhook send failed: %s", e)
        await channel.send(f"**{embeds.safe(player['name'])}**: {embeds.safe(data['message'])}")

    async def post_feed(self, record: ServerRecord, event_type: str, data: dict) -> None:
        await self.wait_until_ready()
        channel = await self.channel_for(record, "feed") or await self.channel_for(record, "chat")
        embed = embeds.feed_embed(event_type, data)
        if channel and embed:
            await channel.send(embed=embed)

    @tasks.loop(seconds=STATUS_REFRESH_S)
    async def status_loop(self) -> None:
        for record, _ in self.store.servers_with_setting("status_message"):
            await self.refresh_status(record)

    @status_loop.before_loop
    async def _before_status_loop(self) -> None:
        await self.wait_until_ready()

    async def refresh_status(self, record: ServerRecord) -> None:
        value = self.store.get_setting(record.server_id, "status_message")
        if not value:
            return
        await self.wait_until_ready()
        channel_id, message_id = value.split(":")
        channel = self.get_channel(int(channel_id))
        if channel is None or getattr(channel, "guild", None) is None or str(channel.guild.id) != record.guild_id:
            return
        embed, files = self.status_of(record)
        try:
            await channel.get_partial_message(int(message_id)).edit(embed=embed, attachments=files)
        except discord.NotFound:
            self.store.set_setting(record.server_id, "status_message", None)
        except discord.HTTPException as e:
            log.warning("couldn't update status for %s: %s", record.server_id, e)

    def recap_message(self, record: ServerRecord, until: int | None = None) -> tuple[discord.Embed, list]:
        until = until or int(time.time())
        since = until - 86400
        r = self.store.recap(record.server_id, since, until)
        files = []
        if r["samples"]:
            png = charts.activity_chart(charts.bucket(r["samples"], 900), since, until, step=900)
            files.append(file_of(png, embeds.CHART_FILE))
        return embeds.recap_embed(record.name, r, has_chart=bool(files)), files

    @tasks.loop(minutes=5)
    async def recap_loop(self) -> None:
        now = dt.datetime.now(dt.timezone.utc)
        today = now.date().isoformat()
        for guild in list(self.guilds):
            for record in self.store.servers_for_guild(str(guild.id)):
                sid = record.server_id
                if self.store.get_setting(sid, "recap") == "off":
                    continue
                if now.hour < int(self.store.get_setting(sid, "recap_hour") or 9):
                    continue
                if self.store.get_setting(sid, "recap_last") == today:
                    continue
                self.store.set_setting(sid, "recap_last", today)
                embed, files = self.recap_message(record)
                if not files:
                    continue
                channel = await self.channel_for(record, "alerts")
                if channel:
                    try:
                        await channel.send(embed=embed, files=files)
                    except discord.HTTPException as e:
                        log.warning("couldn't post recap for %s: %s", sid, e)
        self.store.prune(int(time.time()) - KEEP_HISTORY_S)

    @recap_loop.before_loop
    async def _before_recap_loop(self) -> None:
        await self.wait_until_ready()

    async def handle_link_request(self, session: Session, record: ServerRecord, data: dict) -> None:
        player = data["player"]
        attempts = self._link_attempts[record.server_id]
        now = time.monotonic()
        while attempts and now - attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= LINK_ATTEMPTS_PER_MINUTE:
            await self._link_result(session, player["uuid"], False, "Too many link attempts. Wait a minute.")
            return
        attempts.append(now)

        discord_id = self.store.redeem_account_code(record.guild_id, data["code"], player["uuid"], player["name"])
        if discord_id is None:
            await self._link_result(session, player["uuid"], False,
                                    "That code is wrong or expired. Run /account link in Discord to get a new one.")
            return
        await self.wait_until_ready()
        name = "your Discord account"
        guild = self.get_guild(int(record.guild_id))
        if guild is not None:
            try:
                member = guild.get_member(int(discord_id)) or await guild.fetch_member(int(discord_id))
                name = member.display_name
                role_id = self.store.get_setting(record.server_id, "link_role")
                role = guild.get_role(int(role_id)) if role_id else None
                if role is not None:
                    await member.add_roles(role, reason=f"Linked Minecraft account {player['name']}")
            except discord.HTTPException as e:
                log.warning("couldn't give link role in %s: %s", record.guild_id, e)
        self.store.audit(record.guild_id, record.server_id, discord_id, name, "account_link", player["name"], "ok")
        await self._link_result(session, player["uuid"], True, f"Linked to Discord as {name}!")
        try:
            user = await self.fetch_user(int(discord_id))
            await user.send(f"✅ Your Discord is now linked to **{embeds.safe(player['name'])}** on "
                            f"**{embeds.safe(record.name)}**.")
        except Exception:
            pass

    async def _link_result(self, session: Session, uuid: str, ok: bool, message: str) -> None:
        if "link" not in session.capabilities:
            return
        try:
            await session.command(Envelope(type="cmd.link_result",
                                           data={"player_uuid": uuid, "ok": ok, "message": message[:256]}))
        except CommandFailed:
            pass

    async def decide_whitelist(self, interaction: discord.Interaction, request_id: int, approve: bool) -> None:
        if not views.can_manage(interaction):
            await interaction.response.send_message("You need **Manage Server** to decide whitelist requests.",
                                                    ephemeral=True)
            return
        req = self.store.whitelist_request(request_id)
        record = self.store.get_server(req["server_id"]) if req else None
        if req is None or record is None or record.guild_id != str(interaction.guild_id):
            await interaction.response.send_message("This request no longer exists.", ephemeral=True)
            return
        if req["status"] != "pending":
            await interaction.response.send_message(f"Already {req['status']}.", ephemeral=True)
            return
        await interaction.response.defer()

        note = None
        if approve:
            session = self.gateway.sessions.get(record.server_id)
            if session is None or "whitelist" not in session.capabilities:
                await interaction.followup.send("The server is offline or doesn't allow whitelisting right now. "
                                                "Try again when it's back.", ephemeral=True)
                return
            try:
                reply = await session.command(command("cmd.whitelist", actor_of(interaction.user),
                                                      action="add", player_name=req["player"]))
                note = reply.get("result")
            except CommandFailed as e:
                await interaction.followup.send(f"❌ {embeds.safe(e.message)}", ephemeral=True)
                return

        status = "approved" if approve else "denied"
        if not self.store.decide_whitelist_request(request_id, status, str(interaction.user.id)):
            await interaction.followup.send("Someone else already decided this one.", ephemeral=True)
            return
        self.store.audit(record.guild_id, record.server_id, str(interaction.user.id), interaction.user.name,
                         f"whitelist_request_{status}", req["player"])
        linked = self.store.linked_account(record.guild_id, req["discord_id"])
        await interaction.edit_original_response(
            embed=embeds.whitelist_request_embed(record.name, req["player"], req["discord_id"], status=status,
                                                 decided_by=str(interaction.user.id),
                                                 linked_name=linked["name"] if linked else None, note=note),
            view=None)
        try:
            user = await self.fetch_user(int(req["discord_id"]))
            text = (f"✅ You've been whitelisted on **{embeds.safe(record.name)}** as **{req['player']}**. Have fun!"
                    if approve else
                    f"Your whitelist request for **{embeds.safe(record.name)}** ({req['player']}) was declined.")
            if approve and record.address:
                text += f"\nJoin with `{record.address}`"
            await user.send(text)
        except Exception:
            pass

    async def on_message(self, message: discord.Message) -> None:
        if not self.settings.chat_bridge or message.author.bot or message.webhook_id or message.guild is None:
            return
        servers = self.store.servers_for_channel(str(message.channel.id), "chat")
        if not servers:
            return
        text = message.clean_content.replace("\n", " ").strip()
        if message.attachments:
            text = (text + " [attachment]").strip()
        if not text:
            return
        if len(text) > MAX_CHAT_LEN:
            text = text[:MAX_CHAT_LEN - 1] + "…"
        for record in servers:
            session = self.gateway.sessions.get(record.server_id)
            if session is None:
                await message.add_reaction("🔴")
                continue
            try:
                await session.command(command("cmd.chat_send", actor_of(message.author), message=text))
            except CommandFailed:
                await message.add_reaction("⚠️")

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        for server_id in self.store.delete_guild(str(guild.id)):
            self.gateway.disconnect_server(server_id)
            self.tracker.forget(server_id)
        log.info("removed from guild %s, cleaned up its servers", guild.id)
