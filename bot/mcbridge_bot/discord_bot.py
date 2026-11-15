"""The Discord side of MCBridge: slash commands, live status, alerts, chat bridge and feed.

It runs in the SAME process as the gateway, so it can read live sessions directly
(no extra network hop) and react to gateway events the moment they happen.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks

from . import embeds
from .alerts import Alert, AlertTracker
from .config import Settings
from .gateway import CommandFailed, Gateway, Session
from .protocol import MAX_CHAT_LEN, Actor, command
from .store import LINK_CODE_TTL_S, ServerRecord, Store

log = logging.getLogger("mcbridge.discord")

STATUS_REFRESH_S = 30
FEED_EVENTS = {"event.player_join", "event.player_leave", "event.player_death", "event.player_advancement"}


class UserError(Exception):
    pass


def actor_of(user: discord.abc.User) -> Actor:
    return Actor(discord_id=str(user.id), name=user.display_name)


class MCBridgeBot(commands.Bot):
    def __init__(self, store: Store, gateway: Gateway, settings: Settings):
        intents = discord.Intents.default()
        intents.message_content = settings.chat_bridge
        super().__init__(command_prefix=commands.when_mentioned, intents=intents,
                         allowed_mentions=discord.AllowedMentions.none(), help_command=None)
        self.store, self.gateway, self.settings = store, gateway, settings
        self.tracker = AlertTracker()
        self._tasks: set[asyncio.Task] = set()
        gateway.on(self._on_gateway)
        self.tree.on_error = self.on_app_command_error

    async def setup_hook(self) -> None:
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

    async def on_ready(self) -> None:
        log.info("logged in as %s, in %d Discord servers", self.user, len(self.guilds))
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                             name="Minecraft servers | /help"))

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        original = getattr(error, "original", error)
        if isinstance(original, UserError):
            text = f"❌ {original}"
        elif isinstance(error, app_commands.MissingPermissions):
            text = "❌ You need the **" + ", ".join(p.replace("_", " ").title() for p in error.missing_permissions) \
                   + "** permission for that."
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

    def status_of(self, record: ServerRecord) -> discord.Embed:
        session = self.gateway.sessions.get(record.server_id)
        return embeds.status_embed(
            record.name,
            session.hello if session else None,
            session.heartbeat if session else None,
            online=session is not None,
            lagging=self.tracker.is_lagging(record.server_id),
            offline_reason=self.tracker.last_lost(record.server_id))

    async def _on_gateway(self, session: Session, what: str, details: dict) -> None:
        record = session.record
        alert: Alert | None = None
        if what == "heartbeat":
            alert = self.tracker.heartbeat(record.server_id, details)
        elif what == "connected":
            alert = self.tracker.connected(record.server_id)
            self.spawn(self.announce_link(record))
            self.spawn(self.refresh_status(record))
        elif what == "lost":
            alert = self.tracker.lost(record.server_id, details["reason"])
            if details["reason"] != "unlinked":
                self.spawn(self.refresh_status(record))
        elif what == "event.player_chat":
            self.spawn(self.post_chat(record, details))
        elif what in FEED_EVENTS:
            self.spawn(self.post_feed(record, what, details))
        if alert is not None:
            self.spawn(self.send_alert(record, alert))

    async def announce_link(self, record: ServerRecord) -> None:
        if self.store.get_setting(record.server_id, "announced"):
            return
        self.store.set_setting(record.server_id, "announced", "1")
        await self.wait_until_ready()
        channel = await self.channel_for(record, "alerts")
        if channel:
            e = discord.Embed(title="✅ Linked!", color=embeds.GREEN,
                              description=f"**{embeds.safe(record.name)}** is now connected to this Discord.\n"
                                          "Alerts will show up here. Next steps:\n"
                                          "• `/status live:True` for an auto-updating status message\n"
                                          "• `/channel kind:chat` to bridge chat\n"
                                          "• `/alerts role:` to ping a role when something breaks")
            await channel.send(embed=e)

    async def send_alert(self, record: ServerRecord, alert: Alert) -> None:
        await self.wait_until_ready()
        channel = await self.channel_for(record, "alerts")
        if channel is None:
            return
        role_id = self.store.get_setting(record.server_id, "alert_role")
        content, mentions = None, discord.AllowedMentions.none()
        if alert.ping and role_id:
            content = f"<@&{role_id}>"
            mentions = discord.AllowedMentions(roles=[discord.Object(id=int(role_id))])
        await channel.send(content=content, embed=embeds.alert_embed(record.name, alert), allowed_mentions=mentions)

    async def post_chat(self, record: ServerRecord, data: dict) -> None:
        await self.wait_until_ready()
        channel = await self.channel_for(record, "chat")
        if channel:
            await channel.send(f"**{embeds.safe(data['player']['name'])}**: {embeds.safe(data['message'])}")

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
        try:
            await channel.get_partial_message(int(message_id)).edit(embed=self.status_of(record))
        except discord.NotFound:
            self.store.set_setting(record.server_id, "status_message", None)
        except discord.HTTPException as e:
            log.warning("couldn't update status for %s: %s", record.server_id, e)

    async def on_message(self, message: discord.Message) -> None:
        if not self.settings.chat_bridge or message.author.bot or message.guild is None:
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


class ConfirmUnlink(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=60)
        self.owner_id = owner_id
        self.confirmed: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the person who ran /unlink can confirm.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Unlink", style=discord.ButtonStyle.danger)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        await interaction.response.defer()
        self.stop()


class MCBridgeCommands(commands.Cog):
    def __init__(self, bot: MCBridgeBot):
        self.bot = bot
        self.store = bot.store

    def resolve(self, interaction: discord.Interaction, server: str | None) -> ServerRecord:
        records = self.store.servers_for_guild(str(interaction.guild_id))
        if not records:
            raise UserError("No Minecraft server is linked here yet. Run `/setup` first.")
        if server:
            for r in records:
                if server in (r.server_id, r.name) or server.lower() == r.name.lower():
                    return r
            raise UserError(f"No linked server called **{embeds.safe(server)}**. See `/servers`.")
        if len(records) == 1:
            return records[0]
        raise UserError("This Discord has several servers linked, so pick one with the `server` option.")

    def session(self, record: ServerRecord, capability: str | None = None) -> Session:
        session = self.bot.gateway.sessions.get(record.server_id)
        if session is None:
            raise UserError(f"**{embeds.safe(record.name)}** is offline right now.")
        if capability and capability not in session.capabilities:
            raise UserError(f"**{embeds.safe(record.name)}** doesn't allow `{capability}`. The server owner can "
                            f"turn it on with `allow.{capability}: true` in `plugins/MCBridge/config.yml`.")
        return session

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        records = self.store.servers_for_guild(str(interaction.guild_id))
        return [app_commands.Choice(name=r.name[:100], value=r.server_id)
                for r in records if current.lower() in r.name.lower()][:25]

    def audit(self, interaction: discord.Interaction, server_id: str | None, action: str,
              detail: str = "", result: str = "") -> None:
        self.store.audit(str(interaction.guild_id), server_id, str(interaction.user.id),
                         interaction.user.name, action, detail, result)

    @app_commands.guild_only()
    @app_commands.command(name="help", description="What MCBridge can do")
    async def help(self, interaction: discord.Interaction):
        e = discord.Embed(title="MCBridge", color=embeds.GREEN,
                          description="Connects your Minecraft server to Discord: live stats, alerts, chat and more.")
        e.add_field(name="Getting started", inline=False,
                    value="`/setup` - link a Minecraft server (gives you a code)\n`/servers` - list linked servers")
        e.add_field(name="Status", inline=False,
                    value="`/status` - TPS, MSPT, RAM and players\n`/status live:True` - a message that keeps updating")
        e.add_field(name="Settings", inline=False,
                    value="`/channel` - pick channels for alerts, chat and the join/leave feed\n"
                          "`/alerts` - role to ping on crashes and lag\n`/unlink` - disconnect a server")
        e.add_field(name="Admin", inline=False,
                    value="`/whitelist` - add or remove players\n`/console` - run a console command (if allowed)\n"
                          "`/audit` - who did what")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="setup", description="Link a Minecraft server to this Discord")
    @app_commands.describe(name="A name for the server, e.g. 'Survival SMP'")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup(self, interaction: discord.Interaction, name: app_commands.Range[str, 1, 40]):
        guild_id = str(interaction.guild_id)
        if len(self.store.servers_for_guild(guild_id)) >= self.bot.settings.max_servers_per_guild:
            raise UserError(f"This Discord already has the maximum of "
                            f"{self.bot.settings.max_servers_per_guild} servers. `/unlink` one first.")
        code = self.store.create_link_code(guild_id, name.strip(), created_by=str(interaction.user.id),
                                           channel_id=str(interaction.channel_id))
        self.audit(interaction, None, "setup", name)

        steps = ["Put **MCBridge.jar** in your server's `plugins` folder and restart the server."]
        if self.bot.settings.public_ws_url:
            steps.append(f"In `plugins/MCBridge/config.yml`, set `bot-url: \"{self.bot.settings.public_ws_url}\"`, "
                         "then run `/mcbridge reload`.")
        steps.append(f"In the server console (or in-game as an op), run:\n```\nmcbridge link {code}\n```")
        e = discord.Embed(title=f"Link {embeds.safe(name)}", color=embeds.GREEN,
                          description="\n".join(f"**{i}.** {s}" for i, s in enumerate(steps, 1)))
        e.add_field(name="Code expires", value=f"<t:{int(time.time()) + LINK_CODE_TTL_S}:R> (works once)")
        e.add_field(name="Alerts go to", value=f"<#{interaction.channel_id}> (change with `/channel`)")
        e.set_footer(text="Keep this code private - anyone with it can link their server here.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="servers", description="List the Minecraft servers linked to this Discord")
    async def servers(self, interaction: discord.Interaction):
        records = self.store.servers_for_guild(str(interaction.guild_id))
        if not records:
            raise UserError("No servers linked yet. Run `/setup` to add one.")
        lines = []
        for r in records:
            session = self.bot.gateway.sessions.get(r.server_id)
            if session is None:
                lines.append(f"🔴 **{embeds.safe(r.name)}** - offline")
            else:
                hb = session.heartbeat
                players = f"{len(hb['players'])}/{hb['max_players']} players" if hb else "starting"
                lines.append(f"🟢 **{embeds.safe(r.name)}** - {players}")
        await interaction.response.send_message(
            embed=discord.Embed(title="Linked servers", description="\n".join(lines), color=embeds.GREEN))

    @app_commands.guild_only()
    @app_commands.command(name="status", description="Live TPS, MSPT, memory and players")
    @app_commands.describe(server="Which server (only needed if you have several)",
                           live="Post a status message here that updates itself every 30 seconds")
    @app_commands.autocomplete(server=server_autocomplete)
    async def status(self, interaction: discord.Interaction, server: str | None = None, live: bool = False):
        record = self.resolve(interaction, server)
        if not live:
            await interaction.response.send_message(embed=self.bot.status_of(record))
            return
        if not interaction.user.guild_permissions.manage_guild:
            raise UserError("You need **Manage Server** to post a live status message.")
        channel = interaction.channel
        if not channel.permissions_for(interaction.guild.me).send_messages:
            raise UserError("I can't send messages in this channel.")
        message = await channel.send(embed=self.bot.status_of(record))
        self.store.set_setting(record.server_id, "status_message", f"{channel.id}:{message.id}")
        self.audit(interaction, record.server_id, "status_live", f"#{channel.name}")
        await interaction.response.send_message("✅ Live status posted. Delete it any time to stop it.",
                                                ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="channel", description="Choose where alerts, chat and the player feed go")
    @app_commands.describe(kind="alerts = crashes & lag, chat = two-way chat bridge, feed = joins/leaves/deaths",
                           channel="Leave empty to turn this off", server="Which server")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def channel(self, interaction: discord.Interaction, kind: Literal["alerts", "chat", "feed"],
                      channel: discord.TextChannel | None = None, server: str | None = None):
        record = self.resolve(interaction, server)
        if channel is None:
            self.store.set_channel(record.server_id, kind, None)
            self.audit(interaction, record.server_id, "channel", f"{kind} off")
            await interaction.response.send_message(f"✅ {kind.title()} turned off for **{embeds.safe(record.name)}**.",
                                                    ephemeral=True)
            return
        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.view_channel and perms.send_messages and perms.embed_links):
            raise UserError(f"I need **View Channel**, **Send Messages** and **Embed Links** in {channel.mention}.")
        self.store.set_channel(record.server_id, kind, str(channel.id))
        self.audit(interaction, record.server_id, "channel", f"{kind} -> #{channel.name}")
        note = ""
        if kind == "chat" and not self.bot.settings.chat_bridge:
            note = "\n⚠️ Discord → Minecraft chat is turned off on this bot, so only Minecraft → Discord will work."
        await interaction.response.send_message(
            f"✅ {kind.title()} for **{embeds.safe(record.name)}** now goes to {channel.mention}.{note}", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="alerts", description="Choose a role to ping when a server crashes or lags")
    @app_commands.describe(role="Leave empty to stop pinging", server="Which server")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def alerts(self, interaction: discord.Interaction, role: discord.Role | None = None,
                     server: str | None = None):
        record = self.resolve(interaction, server)
        self.store.set_setting(record.server_id, "alert_role", str(role.id) if role else None)
        self.audit(interaction, record.server_id, "alert_role", role.name if role else "none")
        await interaction.response.send_message(
            f"✅ {'Pinging ' + role.mention if role else 'No role pings'} for **{embeds.safe(record.name)}** alerts.",
            ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="unlink", description="Disconnect a Minecraft server from this Discord")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unlink(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        view = ConfirmUnlink(interaction.user.id)
        await interaction.response.send_message(
            f"Unlink **{embeds.safe(record.name)}**? Its token stops working immediately and its settings are "
            "deleted. You can always `/setup` it again.", view=view, ephemeral=True)
        await view.wait()
        if not view.confirmed:
            await interaction.edit_original_response(content="Cancelled.", view=None)
            return
        self.store.delete_server(record.server_id)
        self.bot.gateway.disconnect_server(record.server_id)
        self.bot.tracker.forget(record.server_id)
        self.audit(interaction, record.server_id, "unlink", record.name)
        await interaction.edit_original_response(content=f"✅ **{embeds.safe(record.name)}** unlinked.", view=None)

    @app_commands.guild_only()
    @app_commands.command(name="whitelist", description="Add or remove a player from the whitelist")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def whitelist(self, interaction: discord.Interaction, action: Literal["add", "remove"],
                        player: app_commands.Range[str, 3, 16], server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "whitelist")
        await interaction.response.defer(ephemeral=True)
        try:
            reply = await session.command(command("cmd.whitelist", actor_of(interaction.user),
                                                  action=action, player_name=player))
            result = reply.get("result") or "done"
            self.audit(interaction, record.server_id, f"whitelist_{action}", player, "ok")
            await interaction.followup.send(f"✅ {embeds.safe(result)}", ephemeral=True)
        except CommandFailed as e:
            self.audit(interaction, record.server_id, f"whitelist_{action}", player, e.code)
            await interaction.followup.send(f"❌ {embeds.safe(e.message)}", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="console", description="Run a console command on the server (admins only)")
    @app_commands.describe(cmd="The command, without a leading /", server="Which server")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def console(self, interaction: discord.Interaction, cmd: app_commands.Range[str, 1, 1000],
                      server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "console")
        cmd = cmd.strip().lstrip("/")
        if not cmd:
            raise UserError("That command is empty.")
        self.audit(interaction, record.server_id, "console", cmd, "sent")
        await interaction.response.defer(ephemeral=True)
        try:
            reply = await session.command(command("cmd.console", actor_of(interaction.user), command=cmd))
            output = (reply.get("result") or "(no output)")[:1800].replace("```", "'''")
            self.audit(interaction, record.server_id, "console_result", cmd, "ok")
            await interaction.followup.send(f"```\n{output}\n```", ephemeral=True)
        except CommandFailed as e:
            self.audit(interaction, record.server_id, "console_result", cmd, e.code)
            await interaction.followup.send(f"❌ {embeds.safe(e.message)}", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="audit", description="Recent MCBridge actions in this Discord")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def audit_log(self, interaction: discord.Interaction):
        entries = self.store.recent_audit(str(interaction.guild_id), limit=15)
        if not entries:
            raise UserError("Nothing logged yet.")
        lines = [f"<t:{e['ts']}:R> **{embeds.safe(e['actor_name'])}** `{e['action']}` "
                 f"{embeds.safe(e['detail'] or '')[:60]} {('→ ' + e['result']) if e['result'] else ''}"
                 for e in entries]
        await interaction.response.send_message(
            embed=discord.Embed(title="Audit log", description="\n".join(lines), color=embeds.GREY), ephemeral=True)