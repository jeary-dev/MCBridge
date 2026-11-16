"""Gateway tests: a real aiohttp server + a scripted fake plugin, all in-process."""
import asyncio

import aiohttp
import pytest
from aiohttp.test_utils import TestClient, TestServer

from mcbridge_bot.gateway import CommandFailed, Gateway
from mcbridge_bot.protocol import Actor, Envelope, command, reply_error, reply_ok, ErrorCode
from mcbridge_bot.store import Store

ME = Actor(discord_id="1", name="corbyn")
HELLO = {"plugin_version": "t", "platform": "paper", "mc_version": "1.21.11", "capabilities": ["chat", "whitelist"]}
HEARTBEAT = {"tps": [20.0, 20.0, 20.0], "mspt": 5.0, "players": [], "max_players": 20,
             "memory": {"used_mb": 1, "max_mb": 2}, "uptime_s": 1}


def run(coro):
    return asyncio.run(coro)


async def start(gateway):
    client = TestClient(TestServer(gateway.make_app()))
    await client.start_server()
    return client


async def connect(client, token):
    ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
    await ws.send_str(Envelope(type="hello", data=HELLO).to_json())
    welcome = Envelope.from_json((await ws.receive()).data)
    return ws, welcome


def setup(**kw):
    store = Store(":memory:")
    rec, token = store.create_server("guild-1", "Test SMP", address="127.0.0.1:1")
    events = []
    kw.setdefault("lost_grace_s", 0)
    gw = Gateway(store, **kw)

    @gw.on
    async def record(session, what, details):
        events.append((what, details))

    return gw, rec, token, events


async def wait_for(predicate, timeout=2.0):
    end = asyncio.get_running_loop().time() + timeout
    while not predicate():
        if asyncio.get_running_loop().time() > end:
            raise AssertionError("condition never became true")
        await asyncio.sleep(0.01)


def test_bad_token_is_rejected():
    async def go():
        gw, *_ = setup()
        client = await start(gw)
        try:
            with pytest.raises(aiohttp.WSServerHandshakeError) as e:
                await client.ws_connect("/v1/plugin", headers={"Authorization": "Bearer nope"})
            assert e.value.status == 401
        finally:
            await client.close()
    run(go())


def test_handshake_and_events():
    async def go():
        gw, rec, token, events = setup()
        client = await start(gw)
        try:
            ws, welcome = await connect(client, token)
            assert welcome.type == "welcome" and welcome.data["server_id"] == rec.server_id
            assert welcome.data["features"]["console"] is False

            await ws.send_str(Envelope(type="heartbeat", data=HEARTBEAT).to_json())
            await ws.send_str(Envelope(type="event.player_join",
                                       data={"player": {"uuid": "u", "name": "Steve"}, "first_join": True}).to_json())
            await ws.send_str(Envelope(type="event.from_the_future", data={}).to_json())
            await wait_for(lambda: any(w == "event.player_join" for w, _ in events))

            assert gw.sessions[rec.server_id].heartbeat == HEARTBEAT
            assert [w for w, _ in events] == ["connected", "heartbeat", "event.player_join"]
            await ws.close()
        finally:
            await client.close()
    run(go())


def test_first_message_must_be_hello():
    async def go():
        gw, rec, token, _ = setup()
        client = await start(gw)
        try:
            ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
            await ws.send_str(Envelope(type="heartbeat", data=HEARTBEAT).to_json())
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.CLOSE and ws.close_code == 1008
            assert rec.server_id not in gw.sessions
        finally:
            await client.close()
    run(go())


async def answer_commands(ws, respond):
    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            env = Envelope.from_json(msg.data)
            if env.type.startswith("cmd."):
                out = respond(env)
                if out is not None:
                    await ws.send_str(out.to_json())


def test_command_reply_ok_and_error():
    async def go():
        gw, rec, token, _ = setup()
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)

            def respond(env):
                if env.type == "cmd.console":
                    return reply_error(env, ErrorCode.FORBIDDEN, "console disabled")
                return reply_ok(env, "done")

            task = asyncio.create_task(answer_commands(ws, respond))
            session = gw.sessions[rec.server_id]

            result = await session.command(command("cmd.whitelist", ME, action="add", player_name="Steve"))
            assert result["result"] == "done"

            with pytest.raises(CommandFailed) as e:
                await session.command(command("cmd.console", ME, command="say hi"))
            assert e.value.code == "FORBIDDEN"

            await ws.close()
            task.cancel()
        finally:
            await client.close()
    run(go())


def test_command_timeout():
    async def go():
        gw, rec, token, _ = setup()
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            task = asyncio.create_task(answer_commands(ws, lambda env: None))
            with pytest.raises(CommandFailed) as e:
                await gw.sessions[rec.server_id].command(command("cmd.chat_send", ME, message="hi"), timeout=0.2)
            assert e.value.code == "TIMEOUT"
            await ws.close()
            task.cancel()
        finally:
            await client.close()
    run(go())


def test_clean_stop_is_reported_as_stopped():
    async def go():
        gw, rec, token, events = setup()
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            await ws.send_str(Envelope(type="event.server_stop", data={"reason": "shutdown"}).to_json())
            await ws.close()
            await wait_for(lambda: any(w == "lost" for w, _ in events))
            assert ("lost", {"reason": "stopped"}) in events
        finally:
            await client.close()
    run(go())


@pytest.mark.parametrize("server_answers_ping,expected", [(False, "crashed"), (True, "plugin_disconnected")])
def test_sudden_disconnect_uses_ping_to_decide(server_answers_ping, expected):
    async def go():
        async def fake_ping(address):
            return server_answers_ping

        gw, rec, token, events = setup(ping_check=fake_ping)
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            await ws.close()
            await wait_for(lambda: any(w == "lost" for w, _ in events))
            assert ("lost", {"reason": expected}) in events
        finally:
            await client.close()
    run(go())


def test_watchdog_drops_silent_servers():
    async def go():
        gw, rec, token, events = setup(silence_timeout_s=0.3)
        client = await start(gw)
        try:
            ws, welcome = await connect(client, token)
            await wait_for(lambda: any(w == "lost" for w, _ in events), timeout=3)
            assert rec.server_id not in gw.sessions
        finally:
            await client.close()
    run(go())


def test_reconnect_replaces_session_without_lost_event():
    async def go():
        gw, rec, token, events = setup()
        client = await start(gw)
        try:
            ws1, _ = await connect(client, token)
            ws2, _ = await connect(client, token)
            await asyncio.sleep(0.1)
            assert gw.sessions[rec.server_id].ws is not None
            assert not any(w == "lost" for w, _ in events)
            assert [w for w, _ in events].count("connected") == 2
            await ws2.close()
        finally:
            await client.close()
    run(go())


def test_quick_reconnect_inside_grace_is_not_reported_as_lost():
    async def go():
        gw, rec, token, events = setup(lost_grace_s=0.5)
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            await ws.close()
            await asyncio.sleep(0.1)
            ws, _ = await connect(client, token)
            await asyncio.sleep(0.7)
            assert not any(w == "lost" for w, _ in events)
            assert rec.server_id in gw.sessions
            await ws.close()
        finally:
            await client.close()
    run(go())


def test_lost_is_reported_after_grace_if_it_stays_gone():
    async def go():
        gw, rec, token, events = setup(lost_grace_s=0.3)
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            await ws.close()
            await asyncio.sleep(0.1)
            assert not any(w == "lost" for w, _ in events)
            await wait_for(lambda: any(w == "lost" for w, _ in events))
        finally:
            await client.close()
    run(go())


def test_clean_stop_skips_the_grace_period():
    async def go():
        gw, rec, token, events = setup(lost_grace_s=60)
        client = await start(gw)
        try:
            ws, _ = await connect(client, token)
            await ws.send_str(Envelope(type="event.server_stop", data={"reason": "shutdown"}).to_json())
            await ws.close()
            await wait_for(lambda: ("lost", {"reason": "stopped"}) in events)
        finally:
            await client.close()
    run(go())
