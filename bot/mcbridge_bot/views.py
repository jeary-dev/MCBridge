"""Buttons, menus and pop-ups: the /settings wizard and the buttons that survive bot restarts."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import discord

from . import embeds
from .store import ServerRecord

if TYPE_CHECKING:
    from .discord_bot import MCBridgeBot

CHANNEL_KINDS = {
    "alerts": ("🚨", "Alerts", "crashes, lag, back online, daily recap"),
    "chat": ("💬", "Chat bridge", "two-way chat with player heads"),
    "feed": ("👋", "Player feed", "joins, leaves, deaths, advancements"),
    "requests": ("📝", "Whitelist requests", "Approve/Deny buttons for staff"),
}
RECAP_HOURS = list(range(0, 24, 1))
PLAYER_NAME = re.compile(r"^[A-Za-z0-9_]{3,16}$")


def can_manage(interaction: discord.Interaction) -> bool:
    perms = getattr(interaction.user, "guild_permissions", None)
    return bool(perms and perms.manage_guild)


def settings_embed(bot: "MCBridgeBot", record: ServerRecord, page: str) -> discord.Embed:
    store = bot.store
    e = discord.Embed(title=f"⚙️ Settings · {record.name}", color=embeds.BLUE)
    if page == "channels":
        e.description = "Pick a channel for each feature. Clear a menu to turn that feature off."
        for kind, (emoji, label, what) in CHANNEL_KINDS.items():
            cid = store.get_channel(record.server_id, kind)
            value = f"<#{cid}>" if cid else "*off*"
            if kind == "requests" and not cid:
                value = "*uses the alerts channel*"
            e.add_field(name=f"{emoji} {label}", value=f"{value}\n-# {what}", inline=True)
    else:
        role = store.get_setting(record.server_id, "alert_role")
        link_role = store.get_setting(record.server_id, "link_role")
        recap = store.get_setting(record.server_id, "recap") != "off"
        hour = int(store.get_setting(record.server_id, "recap_hour") or 9)
        live = store.get_setting(record.server_id, "status_message")
        e.description = "Roles, the daily recap, and the live status message."
        e.add_field(name="🔔 Alert ping role", value=f"<@&{role}>" if role else "*no ping*")
        e.add_field(name="🔗 Linked account role", value=f"<@&{link_role}>" if link_role else "*none*")
        e.add_field(name="📊 Daily recap", value=f"On, at {hour:02d}:00 UTC" if recap else "*off*")
        e.add_field(name="🌐 Server address", value=f"`{embeds.safe(record.address)}`" if record.address
                    else "*not set* (shown on the status card, and used to tell a crash from a plugin problem)")
        e.add_field(name="📺 Live status", value=f"<#{live.split(':')[0]}>" if live else "*not posted*")
    e.set_footer(text="Changes save instantly")
    return e


class SettingsView(discord.ui.View):
    def __init__(self, bot: "MCBridgeBot", server_id: str, owner_id: int, page: str = "channels"):
        super().__init__(timeout=600)
        self.bot, self.server_id, self.owner_id, self.page = bot, server_id, owner_id, page
        self.build()

    @property
    def record(self) -> ServerRecord:
        return self.bot.store.get_server(self.server_id)

    def build(self) -> None:
        self.clear_items()
        store = self.bot.store
        if self.page == "channels":
            for row, (kind, (emoji, label, _)) in enumerate(CHANNEL_KINDS.items()):
                cid = store.get_channel(self.server_id, kind)
                select = discord.ui.ChannelSelect(
                    placeholder=f"{emoji} {label} channel", min_values=0, max_values=1, row=row,
                    channel_types=[discord.ChannelType.text, discord.ChannelType.news],
                    default_values=[discord.Object(id=int(cid))] if cid else [])
                select.callback = self._channel_callback(kind, select)
                self.add_item(select)
            self.add_item(self._button("More settings →", discord.ButtonStyle.primary, 4, self._go("more")))
        else:
            role = store.get_setting(self.server_id, "alert_role")
            alert_role = discord.ui.RoleSelect(placeholder="🔔 Role to ping on crashes and lag", min_values=0,
                                               max_values=1, row=0,
                                               default_values=[discord.Object(id=int(role))] if role else [])
            alert_role.callback = self._role_callback("alert_role", alert_role)
            self.add_item(alert_role)

            link_role = store.get_setting(self.server_id, "link_role")
            linked = discord.ui.RoleSelect(placeholder="🔗 Role for players who link their account", min_values=0,
                                           max_values=1, row=1,
                                           default_values=[discord.Object(id=int(link_role))] if link_role else [])
            linked.callback = self._role_callback("link_role", linked)
            self.add_item(linked)

            hour = int(store.get_setting(self.server_id, "recap_hour") or 9)
            recap_on = store.get_setting(self.server_id, "recap") != "off"
            options = [discord.SelectOption(label="Daily recap: off", value="off", default=not recap_on)]
            options += [discord.SelectOption(label=f"Daily recap at {h:02d}:00 UTC", value=str(h),
                                             default=recap_on and h == hour) for h in RECAP_HOURS]
            recap = discord.ui.Select(placeholder="📊 Daily recap", options=options, row=2)
            recap.callback = self._recap_callback(recap)
            self.add_item(recap)

            self.add_item(self._button("Set server address", discord.ButtonStyle.secondary, 3, self._address))
            self.add_item(self._button("Post live status here", discord.ButtonStyle.success, 3, self._live))
            self.add_item(self._button("← Channels", discord.ButtonStyle.primary, 4, self._go("channels")))

    def _button(self, label, style, row, callback) -> discord.ui.Button:
        b = discord.ui.Button(label=label, style=style, row=row)
        b.callback = callback
        return b

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id or not can_manage(interaction):
            await interaction.response.send_message("Only the person who opened these settings can use them.",
                                                    ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction, note: str | None = None) -> None:
        if self.record is None:
            await interaction.response.edit_message(content="This server was unlinked.", embed=None, view=None)
            return
        self.build()
        e = settings_embed(self.bot, self.record, self.page)
        if note:
            e.add_field(name="⚠️ Heads up", value=note, inline=False)
        if interaction.response.is_done():
            await interaction.edit_original_response(embed=e, view=self)
        else:
            await interaction.response.edit_message(embed=e, view=self)

    def _go(self, page: str):
        async def callback(interaction: discord.Interaction):
            self.page = page
            await self.refresh(interaction)
        return callback

    def _channel_callback(self, kind: str, select: discord.ui.ChannelSelect):
        async def callback(interaction: discord.Interaction):
            note = None
            if select.values:
                channel = interaction.guild.get_channel(select.values[0].id)
                perms = channel.permissions_for(interaction.guild.me) if channel else None
                if not perms or not (perms.view_channel and perms.send_messages and perms.embed_links):
                    await self.refresh(interaction, f"I need **View Channel**, **Send Messages** and **Embed Links** "
                                                    f"in <#{select.values[0].id}>. Nothing was changed.")
                    return
                if kind == "chat" and not perms.manage_webhooks:
                    note = (f"Give me **Manage Webhooks** in <#{channel.id}> so chat shows each player's name and "
                            "head. Until then I'll post chat as myself.")
                self.bot.store.set_channel(self.server_id, kind, str(channel.id))
                if kind == "chat":
                    self.bot.store.set_setting(self.server_id, "chat_webhook", None)
            else:
                self.bot.store.set_channel(self.server_id, kind, None)
            self.bot.store.audit(str(interaction.guild_id), self.server_id, str(interaction.user.id),
                                 interaction.user.name, "settings", f"{kind} channel")
            await self.refresh(interaction, note)
        return callback

    def _role_callback(self, key: str, select: discord.ui.RoleSelect):
        async def callback(interaction: discord.Interaction):
            note = None
            if select.values:
                role = select.values[0]
                if key == "link_role" and (role >= interaction.guild.me.top_role or role.managed):
                    await self.refresh(interaction, f"I can't give out {role.mention}: move my role above it in "
                                                    "Server Settings → Roles. Nothing was changed.")
                    return
                if key == "alert_role" and not role.mentionable and not interaction.guild.me.guild_permissions.mention_everyone:
                    note = f"{role.mention} isn't mentionable, so pings won't notify anyone. Turn on " \
                           "*Allow anyone to @mention this role* in its settings."
                self.bot.store.set_setting(self.server_id, key, str(role.id))
            else:
                self.bot.store.set_setting(self.server_id, key, None)
            await self.refresh(interaction, note)
        return callback

    def _recap_callback(self, select: discord.ui.Select):
        async def callback(interaction: discord.Interaction):
            value = select.values[0]
            if value == "off":
                self.bot.store.set_setting(self.server_id, "recap", "off")
            else:
                self.bot.store.set_setting(self.server_id, "recap", None)
                self.bot.store.set_setting(self.server_id, "recap_hour", value)
            await self.refresh(interaction)
        return callback

    async def _address(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddressModal(self))

    async def _live(self, interaction: discord.Interaction):
        channel = interaction.channel
        perms = channel.permissions_for(interaction.guild.me)
        if not (perms.send_messages and perms.embed_links and perms.attach_files):
            await self.refresh(interaction, "I need **Send Messages**, **Embed Links** and **Attach Files** in this "
                                            "channel to post the live status.")
            return
        await interaction.response.defer()
        embed, files = self.bot.status_of(self.record)
        message = await channel.send(embed=embed, files=files)
        self.bot.store.set_setting(self.server_id, "status_message", f"{channel.id}:{message.id}")
        await self.refresh(interaction)


class AddressModal(discord.ui.Modal, title="Server address"):
    address = discord.ui.TextInput(label="The address players join with", placeholder="play.example.com",
                                   required=False, max_length=100)

    def __init__(self, settings: SettingsView):
        super().__init__()
        self.settings = settings
        self.address.default = settings.record.address or ""

    async def on_submit(self, interaction: discord.Interaction):
        value = self.address.value.strip() or None
        if value and not re.fullmatch(r"[A-Za-z0-9.\-]+(:\d{1,5})?", value):
            await interaction.response.send_message("That doesn't look like a server address.", ephemeral=True)
            return
        self.settings.bot.store.set_address(self.settings.server_id, value)
        await self.settings.refresh(interaction)


class ConfigureButton(discord.ui.DynamicItem[discord.ui.Button], template=r"mcb:cfg:(?P<sid>srv_[0-9a-f]+)"):
    def __init__(self, server_id: str):
        super().__init__(discord.ui.Button(label="Open settings", emoji="⚙️", style=discord.ButtonStyle.primary,
                                           custom_id=f"mcb:cfg:{server_id}"))
        self.server_id = server_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["sid"])

    async def callback(self, interaction: discord.Interaction):
        bot: MCBridgeBot = interaction.client
        record = bot.store.get_server(self.server_id)
        if record is None or record.guild_id != str(interaction.guild_id):
            await interaction.response.send_message("This server isn't linked anymore.", ephemeral=True)
            return
        if not can_manage(interaction):
            await interaction.response.send_message("You need **Manage Server** to change settings.", ephemeral=True)
            return
        view = SettingsView(bot, self.server_id, interaction.user.id)
        await interaction.response.send_message(embed=settings_embed(bot, record, "channels"), view=view,
                                                ephemeral=True)


class WhitelistDecision(discord.ui.DynamicItem[discord.ui.Button],
                        template=r"mcb:wl:(?P<action>approve|deny):(?P<rid>[0-9]+)"):
    def __init__(self, action: str, request_id: int):
        approve = action == "approve"
        super().__init__(discord.ui.Button(
            label="Approve" if approve else "Deny", emoji="✅" if approve else "✖️",
            style=discord.ButtonStyle.success if approve else discord.ButtonStyle.danger,
            custom_id=f"mcb:wl:{action}:{request_id}"))
        self.action, self.request_id = action, request_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        return cls(match["action"], int(match["rid"]))

    async def callback(self, interaction: discord.Interaction):
        bot: MCBridgeBot = interaction.client
        await bot.decide_whitelist(interaction, self.request_id, self.action == "approve")


def whitelist_buttons(request_id: int) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(WhitelistDecision("approve", request_id))
    view.add_item(WhitelistDecision("deny", request_id))
    return view


def configure_button(server_id: str) -> discord.ui.View:
    view = discord.ui.View(timeout=None)
    view.add_item(ConfigureButton(server_id))
    return view
