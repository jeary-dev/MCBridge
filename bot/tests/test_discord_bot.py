"""The Discord layer, tested without logging in to Discord: channels are faked."""
import asyncio
import base64

from aiohttp.test_utils import TestClient, TestServer

from mcbridge_bot.commands import MCBridgeCommands
from mcbridge_bot.config import Settings
from mcbridge_bot.discord_bot import MCBridgeBot
from mcbridge_bot.gateway import Gateway
from mcbridge_bot.protocol import Envelope, reply_ok
from mcbridge_bot.store import Store

SETTINGS = Settings(discord_token=None, dev_guild_id=None, host="", port=0, db_path=":memory:",
                    public_ws_url=None, chat_bridge=True, max_servers_per_guild=3)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20
HELLO = {"plugin_version": "t", "platform": "paper", "mc_version": "1.21.11",
         "capabilities": ["chat", "diagnostics", "link"], "icon": base64.b64encode(PNG).decode()}
DIAG = {"worlds": [{"name": "world", "chunks": 900, "entities": 5000, "tile_entities": 300, "players": 2}],
        "top_chunks": [{"world": "world", "x": 10, "z": -4, "entities": 1200, "tile_entities": 3}],
        "top_entities": [{"type": "ZOMBIE", "count": 900}]}


def heartbeat(tps, players=()):
    return {"tps": [tps, 19.0, 19.0], "mspt": 10.0, "players": list(players), "max_players": 20,
            "memory": {"used_mb": 1, "max_mb": 2}, "uptime_s": 1}


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, embed=None, allowed_mentions=None, view=None, files=None):
        self.sent.append((content, embed))


def make_bot(gateway, store):
    bot = MCBridgeBot(store, gateway, SETTINGS)
    channels = {"alerts": FakeChannel(), "chat": FakeChannel(), "feed": FakeChannel()}

    async def channel_for(record, kind):
        return channels.get(kind)

    async def ready():
        return None

    bot.channel_for = channel_for
    bot.wait_until_ready = ready
    return bot, channels


def test_slash_commands_are_registered_with_permissions():
    async def go():
        bot = MCBridgeBot(Store(":memory:"), Gateway(Store(":memory:")), SETTINGS)
        await bot.add_cog(MCBridgeCommands(bot))
        cmds = {c.name: c for c in bot.tree.get_commands()}
        assert set(cmds) == {"help", "setup", "settings", "servers", "status", "player", "top", "lag", "recap",
                             "whitelist-request", "account", "unlink", "whitelist", "console", "audit",
                             "mod", "msg", "stats", "inventory", "rolesync", "advancements"}
        assert all(c.guild_only for c in cmds.values())
        assert cmds["console"].default_permissions.administrator
        for staff in ("setup", "settings", "lag", "recap", "unlink", "whitelist", "audit", "mod", "msg", "rolesync"):
            assert cmds[staff].default_permissions.manage_guild, staff
        for everyone in ("status", "player", "top", "whitelist-request", "account", "stats", "inventory",
                         "advancements"):
            assert cmds[everyone].default_permissions is None, everyone
        assert {c.name for c in cmds["account"].commands} == {"link", "unlink"}
        assert {c.name for c in cmds["mod"].commands} == {"kick", "ban", "unban", "op", "deop", "gamemode"}
        assert {c.name for c in cmds["rolesync"].commands} == {"add", "remove", "list"}
        for c in cmds.values():
            c.to_dict(bot.tree)
    asyncio.run(go())


def test_events_become_discord_messages_and_stats():
    async def go():
        store = Store(":memory:")
        gw = Gateway(store, silence_timeout_s=60, lost_grace_s=0)
        bot, ch = make_bot(gw, store)
        rec, token = store.create_server("111", "Test SMP")
        store.set_setting(rec.server_id, "alert_role", "42")
        client = TestClient(TestServer(gw.make_app()))
        await client.start_server()
        try:
            async def plugin():
                ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
                await ws.send_str(Envelope(type="hello", data=HELLO).to_json())
                await ws.receive()
                return ws

            async def settle():
                for _ in range(20):
                    await asyncio.sleep(0.02)

            ws = await plugin()
            assert bot.icons[rec.server_id] == PNG
            p = {"uuid": "u", "name": "czrbyn"}
            await ws.send_str(Envelope(type="event.player_join", data={"player": p, "first_join": False}).to_json())
            await ws.send_str(Envelope(type="event.player_chat", data={"player": p, "message": "hi @everyone"}).to_json())
            await ws.send_str(Envelope(type="event.player_death", data={"player": p, "message": "czrbyn fell"}).to_json())
            for _ in range(3):
                await ws.send_str(Envelope(type="heartbeat", data=heartbeat(8.0, [p])).to_json())

            msg = await ws.receive()
            cmd = Envelope.from_json(msg.data)
            assert cmd.type == "cmd.diagnostics"
            await ws.send_str(reply_ok(cmd, "", DIAG).to_json())
            await settle()

            titles = [e.title for _, e in ch["alerts"].sent]
            assert titles[0] == "✅ Test SMP is linked!"
            lag_content, lag = ch["alerts"].sent[1]
            assert "lagging" in lag.title.lower() and lag_content == "<@&42>"
            assert any(f.name == "Busiest chunks" and "x 160, z -64" in f.value for f in lag.fields)
            assert "joined" in ch["feed"].sent[0][1].description
            assert ch["chat"].sent[0][0].startswith("**czrbyn**:") and "@everyone" not in ch["chat"].sent[0][0]
            assert store.samples(rec.server_id, 0)
            stats = store.player(rec.server_id, "czrbyn")
            assert stats["online"] and stats["deaths"] == 1

            await ws.close()
            await settle()
            assert "offline" in ch["alerts"].sent[-1][1].title.lower()
            assert store.player(rec.server_id, "czrbyn")["online"] is False

            ws = await plugin()
            await settle()
            assert "back online" in ch["alerts"].sent[-1][1].title.lower()
            assert sum(1 for _, e in ch["alerts"].sent if "is linked" in (e.title or "")) == 1
            await ws.close()
        finally:
            await client.close()
    asyncio.run(go())


def test_account_link_request_from_minecraft():
    async def go():
        store = Store(":memory:")
        gw = Gateway(store, silence_timeout_s=60, lost_grace_s=0)
        bot, _ = make_bot(gw, store)
        rec, token = store.create_server("111", "SMP")
        code = store.create_account_code("111", "1234")
        client = TestClient(TestServer(gw.make_app()))
        await client.start_server()
        try:
            ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
            await ws.send_str(Envelope(type="hello", data=HELLO).to_json())
            await ws.receive()
            player = {"uuid": "uuid-1", "name": "Steve"}

            await ws.send_str(Envelope(type="event.link_request", data={"player": player, "code": "WRONG1"}).to_json())
            bad = Envelope.from_json((await ws.receive()).data)
            assert bad.type == "cmd.link_result" and bad.data["ok"] is False
            await ws.send_str(reply_ok(bad).to_json())

            await ws.send_str(Envelope(type="event.link_request", data={"player": player, "code": code}).to_json())
            good = Envelope.from_json((await ws.receive()).data)
            assert good.data["ok"] is True and good.data["player_uuid"] == "uuid-1"
            await ws.send_str(reply_ok(good).to_json())
            assert store.linked_discord("111", "uuid-1") == "1234"
            await ws.close()
        finally:
            await client.close()
    asyncio.run(go())


def test_status_card_has_icon_and_chart():
    store = Store(":memory:")
    bot = MCBridgeBot(store, Gateway(store), SETTINGS)
    rec, _ = store.create_server("111", "SMP", address="play.example.com")
    import time
    now = int(time.time())
    store.add_sample(rec.server_id, now - 120, heartbeat(20))
    store.add_sample(rec.server_id, now - 60, heartbeat(19))
    bot.icons[rec.server_id] = PNG
    embed, files = bot.status_of(rec)
    assert {f.filename for f in files} == {"icon.png", "activity.png"}
    assert "play.example.com" in embed.description and "Offline" in embed.description
    assert embed.image.url == "attachment://activity.png"


def test_presence_text_counts_online_servers():
    store = Store(":memory:")
    gw = Gateway(store)
    bot = MCBridgeBot(store, gw, SETTINGS)
    assert bot.presence_text() == "Your Minecraft server, live in Discord · mcbridge.dev"
    gw.sessions["a"] = object()
    assert bot.presence_text() == "Watching 1 Minecraft server · mcbridge.dev"
    gw.sessions["b"] = object()
    assert bot.presence_text() == "Watching 2 Minecraft servers · mcbridge.dev"


def test_health_problem_before_login():
    store = Store(":memory:")
    gw = Gateway(store)
    MCBridgeBot(store, gw, SETTINGS)
    assert gw.health_check() == "not connected to discord yet"


def test_console_stream_filters_and_demo():
    import dataclasses

    async def go():
        store = Store(":memory:")
        gw = Gateway(store, silence_timeout_s=60, lost_grace_s=0)
        rec, token = store.create_server("111", "Demo SMP")
        settings = dataclasses.replace(SETTINGS, demo_server_id=rec.server_id)
        bot = MCBridgeBot(store, gw, settings)
        channels = {"alerts": FakeChannel(), "chat": FakeChannel(), "feed": FakeChannel(), "console": FakeChannel()}

        async def channel_for(record, kind):
            return channels.get(kind)

        async def ready():
            return None

        bot.channel_for = channel_for
        bot.wait_until_ready = ready
        gw.demo_origins = ("https://mcbridge.dev",)
        store.set_channel(rec.server_id, "console", "999")
        store.set_setting(rec.server_id, "feed_off", "leave")
        store.set_setting(rec.server_id, "chat_filter", "badword")
        client = TestClient(TestServer(gw.make_app()))
        await client.start_server()
        try:
            assert (await client.get("/v1/demo")).status == 200
            hello = dict(HELLO, capabilities=["chat", "console", "console_stream"])
            ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
            await ws.send_str(Envelope(type="hello", data=hello).to_json())
            await ws.receive()
            feature = Envelope.from_json((await ws.receive()).data)
            assert feature.type == "cmd.set_features" and feature.data == {"console_stream": True}
            await ws.send_str(reply_ok(feature).to_json())

            p = {"uuid": "u", "name": "czrbyn"}
            await ws.send_str(Envelope(type="event.console", data={
                "lines": ["[12:00:01 INFO]: czrbyn[/10.0.0.5:5555] logged in", "Done (3.2s)!"]}).to_json())
            await ws.send_str(Envelope(type="event.player_chat", data={"player": p, "message": "a BADWORD here"}).to_json())
            await ws.send_str(Envelope(type="event.player_chat", data={"player": p, "message": "hello"}).to_json())
            await ws.send_str(Envelope(type="event.player_join", data={"player": p, "first_join": False}).to_json())
            await ws.send_str(Envelope(type="event.player_leave",
                                       data={"player": p, "reason": "quit", "session_s": 5}).to_json())
            await ws.send_str(Envelope(type="heartbeat", data=heartbeat(20.0, [p])).to_json())
            for _ in range(20):
                await asyncio.sleep(0.02)

            await type(bot).console_loop.coro(bot)
            console_text = ch_text = "".join(c for c, _ in channels["console"].sent)
            assert "logged in" in console_text and "10.0.0.5" not in console_text and "[IP hidden]" in console_text
            ch_text = [c for c, _ in channels["chat"].sent]
            assert len(ch_text) == 1 and "hello" in ch_text[0]
            feed = [e.description for _, e in channels["feed"].sent]
            assert len(feed) == 1 and "joined" in feed[0]

            resp = await client.get("/v1/demo", headers={"Origin": "https://mcbridge.dev"})
            assert resp.headers["Access-Control-Allow-Origin"] == "https://mcbridge.dev"
            demo = await resp.json()
            assert demo["online"] and demo["name"] == "Demo SMP" and demo["players"]["online"] == 1
            assert [e["type"] for e in demo["events"]] == ["chat", "join", "leave"]
            evil = await client.get("/v1/demo", headers={"Origin": "https://evil.example"})
            assert "Access-Control-Allow-Origin" not in evil.headers
            await ws.close()
        finally:
            await client.close()
    asyncio.run(go())


def test_demo_404_without_config():
    async def go():
        store = Store(":memory:")
        gw = Gateway(store)
        MCBridgeBot(store, gw, SETTINGS)
        client = TestClient(TestServer(gw.make_app()))
        await client.start_server()
        try:
            assert (await client.get("/v1/demo")).status == 404
        finally:
            await client.close()
    asyncio.run(go())


class FakeRole:
    def __init__(self, rid, name):
        self.id, self.name = rid, name

    def __eq__(self, other):
        return getattr(other, "id", None) == self.id

    def __hash__(self):
        return self.id


class FakeMember:
    def __init__(self, roles):
        self.roles = roles
        self.display_name = "Corbyn"


class FakeGuild:
    name = "Test Discord"

    def __init__(self, members, roles):
        self.members, self.roles = members, roles

    def get_member(self, mid):
        return self.members.get(mid)

    async def fetch_member(self, mid):
        import discord
        raise discord.NotFound(type("R", (), {"status": 404, "reason": "x"})(), "Unknown Member")

    def get_role(self, rid):
        return self.roles.get(rid)


def test_join_requirements():
    async def go():
        store = Store(":memory:")
        bot = MCBridgeBot(store, Gateway(store), SETTINGS)
        rec, _ = store.create_server("111", "SMP")
        vip = FakeRole(7, "VIP")
        guild = FakeGuild({5: FakeMember([])}, {7: vip})
        bot.get_guild = lambda gid: guild if gid == 111 else None
        player = {"uuid": "u-1", "name": "czrbyn"}

        assert await bot.access_decision(rec, player) == {"allowed": True}
        store.set_setting(rec.server_id, "join_mode", "linked")
        result = await bot.access_decision(rec, player)
        assert result["allowed"] is False and result["reason"] == "not_linked" and len(result["code"]) == 6
        assert store.redeem_join_code("111", result["code"], "5")["uuid"] == "u-1"
        assert await bot.access_decision(rec, player) == {"allowed": True}

        store.set_setting(rec.server_id, "join_mode", "role")
        store.set_setting(rec.server_id, "join_role", "7")
        assert await bot.access_decision(rec, player) == {"allowed": False, "reason": "missing_role", "role": "VIP"}
        guild.members[5].roles.append(vip)
        assert await bot.access_decision(rec, player) == {"allowed": True}

        store.link_account("111", "6", "u-2", "gone")
        result = await bot.access_decision(rec, {"uuid": "u-2", "name": "gone"})
        assert result["reason"] == "not_in_discord"
    asyncio.run(go())


def test_join_requirement_is_pushed_to_new_plugins():
    async def go():
        store = Store(":memory:")
        bot = MCBridgeBot(store, Gateway(store), SETTINGS)
        rec, _ = store.create_server("111", "SMP")
        store.set_setting(rec.server_id, "join_mode", "linked")
        sent = []

        class S:
            server_id = rec.server_id
            capabilities = {"join_gate"}

            async def command(self, env, timeout=10):
                sent.append(env)
                return {"ok": True}
        await bot.push_features(S())
        assert sent[0].data == {"console_stream": False, "join_requirement": "linked"}
        S.capabilities = {"chat"}
        await bot.push_features(S())
        assert len(sent) == 1
    asyncio.run(go())


def test_branding():
    import discord
    from mcbridge_bot import embeds
    store = Store(":memory:")
    bot = MCBridgeBot(store, Gateway(store), SETTINGS)
    rec, _ = store.create_server("111", "SMP")
    e = bot.brand(discord.Embed(color=embeds.BLUE), rec.server_id)
    assert e.color.value == embeds.BLUE and e.footer.text is None
    store.set_setting(rec.server_id, "brand_color", "#FF0000")
    store.set_setting(rec.server_id, "brand_footer", "Cool SMP")
    e = bot.brand(discord.Embed(color=embeds.BLUE), rec.server_id)
    assert e.color.value == 0xFF0000 and e.footer.text == "Cool SMP"
    e = discord.Embed(color=embeds.GREEN)
    e.set_footer(text="MCBridge · plugin 1 · updated")
    bot.brand(e, rec.server_id)
    assert e.color.value == embeds.GREEN and e.footer.text == "Cool SMP · plugin 1 · updated"
    assert bot.accent(rec.server_id) == "#ff0000"


def test_inventory_menu_and_player_buttons():
    async def go():
        from mcbridge_bot import views
        data = {"name": "czrbyn", "hotbar": [{"type": "red_shulker_box", "contents": []}],
                "main": [None, {"type": "shulker_box", "name": "Loot", "contents": [None] * 27}],
                "ender_chest": [None] * 27}
        view = views.ContainerView("SMP", data, "#3987e5")
        assert [o.label for o in view.children[0].options] == ["#1 Red Shulker Box", "#2 Loot", "Ender chest"]
        assert views.ContainerView("SMP", {"name": "x"}, "#3987e5").empty
        buttons = views.player_actions("srv_abc123", "czrbyn", {"online": True, "op": True})
        ids = [b.item.custom_id for b in buttons.children]
        assert ids == ["mcb:pa:kick:srv_abc123:czrbyn", "mcb:pa:ban:srv_abc123:czrbyn", "mcb:pa:deop:srv_abc123:czrbyn"]
        assert all(views.PlayerAction.__discord_ui_compiled_template__.fullmatch(i) for i in ids)
    asyncio.run(go())
