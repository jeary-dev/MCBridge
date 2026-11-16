"""Every slash command. Staff commands are hidden from members by default and checked again when run."""
from __future__ import annotations

import asyncio
import io
import time
from typing import TYPE_CHECKING, Literal

import discord
from discord import app_commands
from discord.ext import commands

from . import embeds, images, views
from .discord_bot import UserError, actor_of
from .gateway import CommandFailed, Session
from .protocol import command
from .sync import DIRECTIONS
from .store import LINK_CODE_TTL_S, ServerRecord

if TYPE_CHECKING:
    from .discord_bot import MCBridgeBot


class MCBridgeCommands(commands.Cog):
    account = app_commands.Group(name="account", description="Link your Discord to your Minecraft account",
                                 guild_only=True)
    mod = app_commands.Group(name="mod", description="Moderate players on your Minecraft server", guild_only=True,
                             default_permissions=discord.Permissions(manage_guild=True))
    rolesync = app_commands.Group(name="rolesync", description="Link permission groups to Discord roles",
                                  guild_only=True, default_permissions=discord.Permissions(manage_guild=True))

    def __init__(self, bot: "MCBridgeBot"):
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
            if capability in ("diagnostics", "link", "stats", "inventory", "message", "player_info", "advancements"):
                raise UserError(f"**{embeds.safe(record.name)}** needs a newer MCBridge plugin for that. "
                                "Ask the server owner to update it.")
            raise UserError(f"**{embeds.safe(record.name)}** doesn't allow `{capability}`. The server owner can "
                            f"turn it on with `allow.{capability}: true` in `plugins/MCBridge/config.yml`.")
        return session

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        records = self.store.servers_for_guild(str(interaction.guild_id))
        return [app_commands.Choice(name=r.name[:100], value=r.server_id)
                for r in records if current.lower() in r.name.lower()][:25]

    async def player_autocomplete(self, interaction: discord.Interaction, current: str):
        server = getattr(interaction.namespace, "server", None)
        try:
            record = self.resolve(interaction, server)
        except UserError:
            return []
        return [app_commands.Choice(name=n, value=n) for n in self.store.player_names(record.server_id, current)]

    def audit(self, interaction: discord.Interaction, server_id: str | None, action: str,
              detail: str = "", result: str = "") -> None:
        self.store.audit(str(interaction.guild_id), server_id, str(interaction.user.id),
                         interaction.user.name, action, detail, result)

    @app_commands.guild_only()
    @app_commands.command(name="help", description="What MCBridge can do")
    async def help(self, interaction: discord.Interaction):
        e = discord.Embed(title="MCBridge", color=embeds.BLUE, url="https://mcbridge.dev",
                          description="Your Minecraft server, live in Discord.")
        e.add_field(name="Everyone", inline=False,
                    value="`/status` live stats and graph\n`/player` health, XP, playtime and more\n"
                          "`/stats` Minecraft statistics\n`/advancements` advancement progress\n"
                          "`/inventory` inventory, shulkers and ender chest\n"
                          "`/top` most active players\n`/whitelist-request` ask to join\n"
                          "`/account link` link your Minecraft account")
        e.add_field(name="Staff", inline=False,
                    value="`/setup` link a server\n`/settings` channels, roles, recap, live status\n"
                          "`/lag` what's causing lag right now\n`/recap` the last 24 hours\n"
                          "`/settings` → Access & branding: join requirements, colour, footer\n"
                          "`/mod` kick, ban, unban, op, deop, gamemode\n`/msg` message a player\n"
                          "`/whitelist` add or remove players\n`/rolesync` link groups to roles\n"
                          "`/console` run a console command\n`/audit` who did what\n`/unlink` disconnect a server")
        e.set_footer(text="Full guide: mcbridge.dev/docs")
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

        steps = ["Download **MCBridge** from [mcbridge.dev](https://mcbridge.dev), put it in your server's "
                 "`plugins` folder and restart the server."]
        if self.bot.settings.public_ws_url:
            steps.append(f"Only if you changed it: `bot-url` in `plugins/MCBridge/config.yml` should be "
                         f"`{self.bot.settings.public_ws_url}`.")
        steps.append(f"In the server console (or in-game as an op), run:\n```\nmcbridge link {code}\n```")
        steps.append("I'll post here when it's linked, with a button to set everything else up.")
        e = discord.Embed(title=f"Link {embeds.safe(name)}", color=embeds.BLUE,
                          description="\n".join(f"**{i}.** {s}" for i, s in enumerate(steps, 1)))
        e.add_field(name="Code expires", value=f"<t:{int(time.time()) + LINK_CODE_TTL_S}:R> (works once)")
        e.set_footer(text="Keep this code private - anyone with it can link their server here.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="settings", description="Channels, roles, daily recap and live status")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def settings(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        view = views.SettingsView(self.bot, record.server_id, interaction.user.id)
        await interaction.response.send_message(embed=views.settings_embed(self.bot, record, "channels"), view=view,
                                                ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="servers", description="The Minecraft servers linked to this Discord")
    async def servers(self, interaction: discord.Interaction):
        records = self.store.servers_for_guild(str(interaction.guild_id))
        if not records:
            raise UserError("No servers linked yet. Run `/setup` to add one.")
        lines = []
        for r in records:
            session = self.bot.gateway.sessions.get(r.server_id)
            if session is None:
                lines.append(f"🔴 **{embeds.safe(r.name)}** · offline")
            else:
                hb = session.heartbeat
                detail = (f"{len(hb['players'])}/{hb['max_players']} players · {hb['tps'][0]:.1f} TPS"
                          if hb else "starting")
                lines.append(f"🟢 **{embeds.safe(r.name)}** · {detail}")
        await interaction.response.send_message(
            embed=discord.Embed(title="Linked servers", description="\n".join(lines), color=embeds.BLUE))

    @app_commands.guild_only()
    @app_commands.command(name="status", description="Live TPS, MSPT, memory, players and a graph of the last hour")
    @app_commands.describe(server="Which server (only needed if you have several)",
                           live="Post a status message here that updates itself every minute")
    @app_commands.autocomplete(server=server_autocomplete)
    async def status(self, interaction: discord.Interaction, server: str | None = None, live: bool = False):
        record = self.resolve(interaction, server)
        embed, files = self.bot.status_of(record)
        if not live:
            await interaction.response.send_message(embed=embed, files=files)
            return
        if not interaction.user.guild_permissions.manage_guild:
            raise UserError("You need **Manage Server** to post a live status message.")
        perms = interaction.channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.attach_files):
            raise UserError("I need **Send Messages**, **Embed Links** and **Attach Files** in this channel.")
        await interaction.response.defer(ephemeral=True)
        message = await interaction.channel.send(embed=embed, files=files)
        self.store.set_setting(record.server_id, "status_message", f"{interaction.channel.id}:{message.id}")
        self.audit(interaction, record.server_id, "status_live", f"#{interaction.channel.name}")
        await interaction.followup.send("✅ Live status posted. It updates every minute; delete it to stop.",
                                        ephemeral=True)

    def card(self, record: ServerRecord, png: bytes, filename: str, description: str | None = None):
        e = discord.Embed(color=embeds.BLUE, description=description)
        e.set_image(url=f"attachment://{filename}")
        self.bot.brand(e, record.server_id)
        return e, discord.File(io.BytesIO(png), filename=filename)

    async def live_command(self, record: ServerRecord, cmd_type: str, capability: str, user, player: str,
                           *, required: bool) -> dict | None:
        session = self.bot.gateway.sessions.get(record.server_id)
        if session is None or capability not in session.capabilities:
            if required:
                self.session(record, capability)
            return None
        try:
            reply = await session.command(command(cmd_type, actor_of(user), player_name=player), timeout=8)
        except CommandFailed as e:
            if required or e.code == "PLAYER_NOT_FOUND":
                raise UserError(e.message)
            return None
        return reply.get("data") or {}

    @app_commands.guild_only()
    @app_commands.command(name="player", description="Health, XP, world, playtime and more for a player")
    @app_commands.autocomplete(name=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def player(self, interaction: discord.Interaction, name: app_commands.Range[str, 1, 16],
                     server: str | None = None):
        record = self.resolve(interaction, server)
        tracked = self.store.player(record.server_id, name)
        await interaction.response.defer()
        live = None
        try:
            live = await self.live_command(record, "cmd.player_info", "player_info", interaction.user, name,
                                           required=False)
        except UserError:
            if tracked is None:
                raise
        if tracked is None and not live:
            raise UserError(f"**{embeds.safe(name)}** hasn't played on **{embeds.safe(record.name)}**.")
        source = live or tracked
        uuid, pname = source["uuid"], source["name"]
        discord_id = self.store.linked_discord(record.guild_id, uuid)
        member = interaction.guild.get_member(int(discord_id)) if discord_id else None
        skin = await self.bot.skin(uuid, "body")
        png = await asyncio.to_thread(images.player_card, pname, server=record.name, tracked=tracked, live=live,
                                      skin=skin, discord_name=member.display_name if member else None,
                                      accent=self.bot.accent(record.server_id))
        e, f = self.card(record, png, "player.png", f"Linked to <@{discord_id}>" if discord_id else None)
        session = self.bot.gateway.sessions.get(record.server_id)
        view = None
        if live and session is not None and "moderation" in session.capabilities:
            view = views.player_actions(record.server_id, pname, live)
        await interaction.followup.send(embed=e, file=f, view=view or discord.utils.MISSING)

    @app_commands.guild_only()
    @app_commands.command(name="advancements", description="A player's advancement progress and recent completions")
    @app_commands.autocomplete(name=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def advancements(self, interaction: discord.Interaction, name: app_commands.Range[str, 3, 16],
                           server: str | None = None):
        record = self.resolve(interaction, server)
        self.session(record, "advancements")
        await interaction.response.defer()
        data = await self.live_command(record, "cmd.advancements", "advancements", interaction.user, name,
                                       required=True)
        avatar = await self.bot.skin(data["uuid"], "avatar") if data.get("uuid") else None
        png = await asyncio.to_thread(images.advancements_card, data, server=record.name, avatar=avatar,
                                      accent=self.bot.accent(record.server_id))
        e, f = self.card(record, png, "advancements.png")
        await interaction.followup.send(embed=e, file=f)

    @app_commands.guild_only()
    @app_commands.command(name="top", description="The most active players by playtime")
    @app_commands.autocomplete(server=server_autocomplete)
    async def top(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        await interaction.response.send_message(
            embed=self.bot.brand(embeds.top_embed(record.name, self.store.top_players(record.server_id, 10)),
                                 record.server_id))

    @app_commands.guild_only()
    @app_commands.command(name="lag", description="What's using the server right now: chunks, entities, hot spots")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.checks.cooldown(1, 15)
    async def lag(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "diagnostics")
        await interaction.response.defer(ephemeral=True)
        try:
            reply = await session.command(command("cmd.diagnostics", actor_of(interaction.user)))
        except CommandFailed as e:
            raise UserError(e.message)
        await interaction.followup.send(
            embed=self.bot.brand(embeds.diagnostics_embed(record.name, reply.get("data") or {}), record.server_id),
            ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="recap", description="Stats and a graph for the last 24 hours")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def recap(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        await interaction.response.defer()
        embed, files = self.bot.recap_message(record)
        await interaction.followup.send(embed=embed, files=files)

    @app_commands.guild_only()
    @app_commands.command(name="whitelist-request", description="Ask the staff to whitelist your Minecraft account")
    @app_commands.describe(player="Your Minecraft username")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.cooldown(1, 30)
    async def whitelist_request(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                                server: str | None = None):
        record = self.resolve(interaction, server)
        if not views.PLAYER_NAME.match(player):
            raise UserError("That isn't a valid Minecraft username.")
        if self.store.pending_whitelist_request(record.server_id, str(interaction.user.id)):
            raise UserError("You already have a request waiting. The staff will get to it soon!")
        channel = await self.bot.channel_for(record, "requests") or await self.bot.channel_for(record, "alerts")
        if channel is None:
            raise UserError("The staff haven't set up whitelist requests yet.")
        rid = self.store.create_whitelist_request(record.server_id, str(interaction.user.id), player)
        linked = self.store.linked_account(record.guild_id, str(interaction.user.id))
        message = await channel.send(
            embed=embeds.whitelist_request_embed(record.name, player, str(interaction.user.id),
                                                 linked_name=linked["name"] if linked else None),
            view=views.whitelist_buttons(rid))
        self.store.set_whitelist_request_message(rid, str(channel.id), str(message.id))
        await interaction.response.send_message(
            f"📝 Request sent for **{embeds.safe(player)}**. I'll DM you when the staff decide.", ephemeral=True)

    @account.command(name="link", description="Link your Minecraft account")
    @app_commands.describe(code="The code from the message you got when the server didn't let you in")
    @app_commands.checks.cooldown(1, 10)
    async def account_link(self, interaction: discord.Interaction, code: app_commands.Range[str, 4, 12] | None = None):
        guild_id = str(interaction.guild_id)
        if not self.store.servers_for_guild(guild_id):
            raise UserError("No Minecraft server is linked to this Discord yet.")
        if code:
            linked = self.store.redeem_join_code(guild_id, code, str(interaction.user.id))
            if linked is None:
                raise UserError("That code is wrong or expired. Join the server again to get a new one.")
            record = self.store.get_server(linked["server_id"])
            note = ""
            if record is not None:
                await self.bot.give_link_role(interaction.guild, interaction.user, record, linked["name"])
                self.audit(interaction, record.server_id, "account_link", linked["name"], "ok (join code)")
                if self.bot.join_mode(record.server_id) == "role":
                    role_id = self.store.get_setting(record.server_id, "join_role")
                    role = interaction.guild.get_role(int(role_id)) if role_id else None
                    if role is not None and role not in interaction.user.roles:
                        note = f"\nYou also need the {role.mention} role before you can join."
            await interaction.response.send_message(
                f"✅ Linked to **{embeds.safe(linked['name'])}**. You can join the server now!{note}", ephemeral=True)
            return
        code = self.store.create_account_code(str(interaction.guild_id), str(interaction.user.id))
        current = self.store.linked_account(str(interaction.guild_id), str(interaction.user.id))
        e = discord.Embed(title="🔗 Link your Minecraft account", color=embeds.BLUE,
                          description=f"Join the server and type:\n```\n/discord link {code}\n```"
                                      f"The code works once and expires <t:{int(time.time()) + LINK_CODE_TTL_S}:R>.")
        if current:
            e.set_footer(text=f"You're currently linked to {current['name']}. Linking again replaces it.")
        await interaction.response.send_message(embed=e, ephemeral=True)

    @account.command(name="unlink", description="Unlink your Minecraft account from this Discord")
    async def account_unlink(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild_id)
        if not self.store.unlink_account(guild_id, str(interaction.user.id)):
            raise UserError("Your account isn't linked.")
        for record in self.store.servers_for_guild(guild_id):
            role_id = self.store.get_setting(record.server_id, "link_role")
            role = interaction.guild.get_role(int(role_id)) if role_id else None
            if role is not None and role in getattr(interaction.user, "roles", []):
                try:
                    await interaction.user.remove_roles(role, reason="Unlinked Minecraft account")
                except discord.HTTPException:
                    pass
        await interaction.response.send_message("✅ Unlinked.", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="unlink", description="Disconnect a Minecraft server from this Discord")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unlink(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        view = ConfirmUnlink(interaction.user.id)
        await interaction.response.send_message(
            f"Unlink **{embeds.safe(record.name)}**? Its token stops working immediately and its settings and "
            "stats are deleted. You can always `/setup` it again.", view=view, ephemeral=True)
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
            self.audit(interaction, record.server_id, f"whitelist_{action}", player, "ok")
            await interaction.followup.send(f"✅ {embeds.safe(reply.get('result') or 'done')}", ephemeral=True)
        except CommandFailed as e:
            self.audit(interaction, record.server_id, f"whitelist_{action}", player, e.code)
            await interaction.followup.send(f"❌ {embeds.safe(e.message)}", ephemeral=True)

    async def console_autocomplete(self, interaction: discord.Interaction, current: str):
        if not interaction.user.guild_permissions.administrator:
            return []
        try:
            record = self.resolve(interaction, getattr(interaction.namespace, "server", None))
        except UserError:
            return []
        session = self.bot.gateway.sessions.get(record.server_id)
        if session is None or "console" not in session.capabilities:
            return []
        text = current.lstrip("/")
        try:
            reply = await session.command(command("cmd.tab_complete", actor_of(interaction.user), command=text),
                                          timeout=2.0)
        except CommandFailed:
            return []
        base = text.rsplit(" ", 1)[0] + " " if " " in text else ""
        out = []
        for suggestion in (reply.get("data") or {}).get("suggestions", [])[:25]:
            full = (base + suggestion)[:100]
            out.append(app_commands.Choice(name=full, value=full))
        return out

    @app_commands.guild_only()
    @app_commands.command(name="console", description="Run a console command on the server (admins only)")
    @app_commands.describe(cmd="The command, without a leading /", server="Which server")
    @app_commands.autocomplete(server=server_autocomplete, cmd=console_autocomplete)
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


    async def run_moderation(self, interaction: discord.Interaction, server: str | None, action: str, player: str,
                             reason: str | None = None, gamemode: str | None = None):
        record = self.resolve(interaction, server)
        if not views.PLAYER_NAME.match(player):
            raise UserError("That isn't a valid Minecraft username.")
        self.session(record, "moderation")
        await self.bot.moderate(interaction, record, action, player, reason, gamemode)

    @mod.command(name="kick", description="Kick an online player")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_kick(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                       reason: app_commands.Range[str, 0, 200] | None = None, server: str | None = None):
        await self.run_moderation(interaction, server, "kick", player, reason)

    @mod.command(name="ban", description="Ban a player")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_ban(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                      reason: app_commands.Range[str, 0, 200] | None = None, server: str | None = None):
        await self.run_moderation(interaction, server, "ban", player, reason)

    @mod.command(name="unban", description="Unban a player")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_unban(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                        server: str | None = None):
        await self.run_moderation(interaction, server, "unban", player)

    @mod.command(name="op", description="Make a player an operator")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_op(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                     server: str | None = None):
        await self.run_moderation(interaction, server, "op", player)

    @mod.command(name="deop", description="Remove a player's operator status")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_deop(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                       server: str | None = None):
        await self.run_moderation(interaction, server, "deop", player)

    @mod.command(name="gamemode", description="Change a player's game mode")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def mod_gamemode(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                           mode: Literal["survival", "creative", "adventure", "spectator"], server: str | None = None):
        await self.run_moderation(interaction, server, "gamemode", player, gamemode=mode)

    @app_commands.guild_only()
    @app_commands.command(name="msg", description="Send a private message to an online player")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def msg(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                  message: app_commands.Range[str, 1, 256], server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "chat")
        if "message" not in session.capabilities:
            raise UserError(f"**{embeds.safe(record.name)}** needs a newer MCBridge plugin for that. "
                            "Ask the server owner to update it.")
        await interaction.response.defer(ephemeral=True)
        try:
            reply = await session.command(command("cmd.message", actor_of(interaction.user), player_name=player,
                                                  message=message.replace("\n", " ")))
            self.audit(interaction, record.server_id, "msg", f"{player}: {message[:80]}", "ok")
            await interaction.followup.send(f"✅ {embeds.safe(reply.get('result') or 'Sent')}", ephemeral=True)
        except CommandFailed as e:
            await interaction.followup.send(f"❌ {embeds.safe(e.message)}", ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="stats", description="Minecraft statistics for a player: kills, deaths, distance and more")
    @app_commands.autocomplete(name=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def stats(self, interaction: discord.Interaction, name: app_commands.Range[str, 3, 16],
                    server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "stats")
        await interaction.response.defer()
        try:
            reply = await session.command(command("cmd.player_stats", actor_of(interaction.user), player_name=name))
        except CommandFailed as e:
            raise UserError(e.message)
        await interaction.followup.send(embed=self.bot.brand(embeds.stats_embed(record.name, reply.get("data") or {}),
                                                             record.server_id))

    @app_commands.guild_only()
    @app_commands.command(name="inventory", description="A player's inventory, shulker boxes and ender chest")
    @app_commands.autocomplete(player=player_autocomplete, server=server_autocomplete)
    @app_commands.checks.cooldown(1, 5)
    async def inventory(self, interaction: discord.Interaction, player: app_commands.Range[str, 3, 16],
                        server: str | None = None):
        record = self.resolve(interaction, server)
        session = self.session(record, "inventory")
        await interaction.response.defer()
        try:
            reply = await session.command(command("cmd.inventory", actor_of(interaction.user), player_name=player))
        except CommandFailed as e:
            raise UserError(e.message)
        data = reply.get("data") or {}
        skin = await self.bot.skin(data["uuid"], "body") if data.get("uuid") else None
        accent = self.bot.accent(record.server_id)
        png = await asyncio.to_thread(images.inventory_card, data, server=record.name, skin=skin, accent=accent)
        e, f = self.card(record, png, "inventory.png")
        view = views.ContainerView(record.name, data, accent)
        await interaction.followup.send(embed=e, file=f, view=discord.utils.MISSING if view.empty else view)

    @rolesync.command(name="add", description="Link a permission group (LuckPerms or Vault) to a Discord role")
    @app_commands.describe(group="The permission group name, e.g. vip", role="The Discord role",
                           direction="Which way changes are copied")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rolesync_add(self, interaction: discord.Interaction, group: app_commands.Range[str, 1, 64],
                           role: discord.Role,
                           direction: Literal["both", "minecraft-to-discord", "discord-to-minecraft"] = "both",
                           server: str | None = None):
        record = self.resolve(interaction, server)
        if direction not in DIRECTIONS:
            raise UserError("Unknown direction.")
        if role.managed or role.is_default():
            raise UserError("That role can't be given out.")
        if role >= interaction.guild.me.top_role:
            raise UserError(f"I can't manage {role.mention}: move my role above it in Server Settings → Roles.")
        self.store.set_role_link(record.server_id, group.strip(), str(role.id), direction)
        self.audit(interaction, record.server_id, "rolesync_add", f"{group} {direction} @{role.name}")
        note = ""
        session = self.bot.gateway.sessions.get(record.server_id)
        if session is not None and "roles" not in session.capabilities:
            note = ("\n⚠️ The server isn't reporting LuckPerms or Vault yet. Install one, update MCBridge, and make "
                    "sure `allow.roles: true`.")
        await interaction.response.send_message(
            embed=embeds.rolesync_embed(record.name, self.store.role_links(record.server_id)),
            content=f"✅ Linked `{embeds.safe(group)}` and {role.mention}. Players sync when they next join.{note}",
            ephemeral=True)

    @rolesync.command(name="remove", description="Remove a role link")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rolesync_remove(self, interaction: discord.Interaction, group: app_commands.Range[str, 1, 64],
                              server: str | None = None):
        record = self.resolve(interaction, server)
        if not self.store.remove_role_link(record.server_id, group.strip()):
            raise UserError(f"`{embeds.safe(group)}` isn't linked. See `/rolesync list`.")
        self.audit(interaction, record.server_id, "rolesync_remove", group)
        await interaction.response.send_message(f"✅ Removed the link for `{embeds.safe(group)}`.", ephemeral=True)

    @rolesync.command(name="list", description="Show every role link")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def rolesync_list(self, interaction: discord.Interaction, server: str | None = None):
        record = self.resolve(interaction, server)
        await interaction.response.send_message(
            embed=self.bot.brand(embeds.rolesync_embed(record.name, self.store.role_links(record.server_id)),
                                 record.server_id), ephemeral=True)


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
