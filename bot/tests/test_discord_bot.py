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
                             "whitelist-request", "account", "unlink", "whitelist", "console", "audit"}
        assert all(c.guild_only for c in cmds.values())
        assert cmds["console"].default_permissions.administrator
        for staff in ("setup", "settings", "lag", "recap", "unlink", "whitelist", "audit"):
            assert cmds[staff].default_permissions.manage_guild, staff
        for everyone in ("status", "player", "top", "whitelist-request", "account"):
            assert cmds[everyone].default_permissions is None, everyone
        assert {c.name for c in cmds["account"].commands} == {"link", "unlink"}
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
