"""POST /v1/link: the plugin swaps a short code for its secret token."""
import asyncio

from aiohttp.test_utils import TestClient, TestServer

from mcbridge_bot.gateway import Gateway
from mcbridge_bot.protocol import Envelope
from mcbridge_bot.store import Store

HELLO = {"plugin_version": "t", "platform": "paper", "mc_version": "1.21.11", "capabilities": []}


async def start():
    store = Store(":memory:")
    gw = Gateway(store)
    client = TestClient(TestServer(gw.make_app()))
    await client.start_server()
    return store, gw, client


def test_link_then_connect_with_the_token():
    async def go():
        store, gw, client = await start()
        try:
            code = store.create_link_code("guild-1", "Steve's SMP", created_by="u1")
            resp = await client.post("/v1/link", json={"code": code.lower()})
            assert resp.status == 200
            body = await resp.json()
            assert body["name"] == "Steve's SMP" and body["token"]

            ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {body['token']}"})
            await ws.send_str(Envelope(type="hello", data=HELLO).to_json())
            welcome = Envelope.from_json((await ws.receive()).data)
            assert welcome.data["server_id"] == body["server_id"]
            assert gw.sessions[body["server_id"]].record.guild_id == "guild-1"
            await ws.close()
        finally:
            await client.close()
    asyncio.run(go())


def test_code_only_works_once():
    async def go():
        store, gw, client = await start()
        try:
            code = store.create_link_code("g", "SMP", created_by="u")
            assert (await client.post("/v1/link", json={"code": code})).status == 200
            assert (await client.post("/v1/link", json={"code": code})).status == 404
        finally:
            await client.close()
    asyncio.run(go())


def test_bad_requests():
    async def go():
        store, gw, client = await start()
        try:
            assert (await client.post("/v1/link", data="not json")).status == 400
            assert (await client.post("/v1/link", json={"code": 123})).status == 400
            assert (await client.post("/v1/link", json={"nope": "x"})).status == 400
        finally:
            await client.close()
    asyncio.run(go())


def test_rate_limit_stops_brute_force():
    async def go():
        store, gw, client = await start()
        try:
            statuses = [(await client.post("/v1/link", json={"code": "AAA-AAA"})).status for _ in range(7)]
            assert statuses[:5] == [404] * 5
            assert statuses[5:] == [429, 429]
        finally:
            await client.close()
    asyncio.run(go())


def test_unlink_kicks_the_server():
    async def go():
        store, gw, client = await start()
        events = []

        @gw.on
        async def record(session, what, details):
            events.append((what, details))

        try:
            rec, token = store.create_server("g", "SMP")
            ws = await client.ws_connect("/v1/plugin", headers={"Authorization": f"Bearer {token}"})
            await ws.send_str(Envelope(type="hello", data=HELLO).to_json())
            await ws.receive()

            store.delete_server(rec.server_id)
            gw.disconnect_server(rec.server_id)
            for _ in range(100):
                if any(w == "lost" for w, _ in events):
                    break
                await asyncio.sleep(0.02)
            assert ("lost", {"reason": "unlinked"}) in events
            assert store.authenticate(token) is None
        finally:
            await client.close()
    asyncio.run(go())


def test_rate_limit_uses_cloudflare_ip_when_trusted():
    async def go():
        store = Store(":memory:")
        client = TestClient(TestServer(Gateway(store, trust_cloudflare=True).make_app()))
        await client.start_server()
        try:
            for _ in range(5):
                await client.post("/v1/link", json={"code": "AAA-AAA"}, headers={"CF-Connecting-IP": "1.1.1.1"})
            blocked = await client.post("/v1/link", json={"code": "AAA-AAA"}, headers={"CF-Connecting-IP": "1.1.1.1"})
            other = await client.post("/v1/link", json={"code": "AAA-AAA"}, headers={"CF-Connecting-IP": "2.2.2.2"})
            assert blocked.status == 429 and other.status == 404
        finally:
            await client.close()
    asyncio.run(go())


def test_cloudflare_header_ignored_when_not_trusted():
    async def go():
        store = Store(":memory:")
        client = TestClient(TestServer(Gateway(store).make_app()))
        await client.start_server()
        try:
            statuses = [(await client.post("/v1/link", json={"code": "AAA-AAA"},
                                           headers={"CF-Connecting-IP": f"9.9.9.{i}"})).status for i in range(6)]
            assert statuses[-1] == 429
        finally:
            await client.close()
    asyncio.run(go())
