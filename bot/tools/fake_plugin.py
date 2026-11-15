"""A pretend Minecraft plugin, for testing the gateway before the real Java plugin exists.

  python tools/fake_plugin.py --link K7P-2QX       (first time: swap a link code for a token)
  python tools/fake_plugin.py --token <token>      (after that)
  options: [--url ws://localhost:8765/v1/plugin] [--console]

It handshakes, sends heartbeats, makes up some player events, and answers commands.
Press Ctrl+C to "crash" it (no stop event), or type 'stop' + Enter for a clean shutdown.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcbridge_bot.protocol import Envelope, ErrorCode, ProtocolError, reply_error, reply_ok

PLAYERS = [{"uuid": "f759806f-e772-4945-8b79-c19266849be4", "name": "czrbyn"},
           {"uuid": "00000000-0000-4000-8000-000000000001", "name": "Steve"}]


class FakePlugin:
    def __init__(self, url: str, token: str, console: bool):
        self.url, self.token = url, token
        self.capabilities = ["chat", "whitelist"] + (["console"] if console else [])
        self.online: list[dict] = []

    async def run(self):
        async with aiohttp.ClientSession() as http:
            async with http.ws_connect(self.url, headers={"Authorization": f"Bearer {self.token}"}) as ws:
                await ws.send_str(Envelope(type="hello", data={
                    "plugin_version": "0.0.0-fake", "platform": "paper",
                    "mc_version": "1.21.11", "capabilities": self.capabilities}).to_json())
                welcome = Envelope.from_json((await ws.receive()).data)
                interval = welcome.data["heartbeat_interval_s"]
                print("Connected:", welcome.data)

                await ws.send_str(Envelope(type="event.server_start",
                                           data={"motd": "Fake server", "max_players": 20}).to_json())
                background = [asyncio.create_task(c) for c in
                              (self._heartbeats(ws, interval), self._events(ws), self._stdin(ws))]
                await self._commands(ws)
                for task in background:
                    task.cancel()
                print("Disconnected.")

    async def _heartbeats(self, ws, interval):
        uptime = 0
        while not ws.closed:
            tps = round(random.uniform(17.5, 20.0), 2)
            await ws.send_str(Envelope(type="heartbeat", data={
                "tps": [tps, 19.9, 19.95], "mspt": round(random.uniform(8, 45), 1),
                "players": self.online, "max_players": 20,
                "memory": {"used_mb": random.randint(1500, 4000), "max_mb": 6144},
                "uptime_s": uptime}).to_json())
            await asyncio.sleep(interval)
            uptime += interval

    async def _events(self, ws):
        while not ws.closed:
            await asyncio.sleep(random.uniform(4, 9))
            p = random.choice(PLAYERS)
            if p not in self.online:
                self.online.append(p)
                env = Envelope(type="event.player_join", data={"player": p, "first_join": False})
            elif random.random() < 0.5:
                env = Envelope(type="event.player_chat", data={"player": p, "message": "hello from the fake server"})
            else:
                self.online.remove(p)
                env = Envelope(type="event.player_leave", data={"player": p, "reason": "quit", "session_s": 42})
            await ws.send_str(env.to_json())

    async def _commands(self, ws):
        async for msg in ws:
            if msg.type != aiohttp.WSMsgType.TEXT:
                continue
            try:
                env = Envelope.from_json(msg.data)
            except ProtocolError as e:
                print("Bad message from bot:", e)
                continue
            if not env.type.startswith("cmd."):
                continue
            print("Command:", env.type, env.data)
            needs = {"cmd.chat_send": "chat", "cmd.whitelist": "whitelist", "cmd.console": "console"}.get(env.type)
            if needs is None:
                out = reply_error(env, ErrorCode.UNKNOWN_COMMAND, env.type)
            elif needs not in self.capabilities:
                out = reply_error(env, ErrorCode.FORBIDDEN, f"{needs} is disabled in config.yml")
            else:
                out = reply_ok(env, f"(fake) did {env.type}")
            await ws.send_str(out.to_json())

    async def _stdin(self, ws):
        loop = asyncio.get_running_loop()
        while not ws.closed:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if line == "":
                return
            if line.strip() == "stop":
                await ws.send_str(Envelope(type="event.server_stop", data={"reason": "shutdown"}).to_json())
                await ws.close()
                return


async def link(ws_url: str, code: str) -> str:
    http_url = ws_url.replace("wss://", "https://").replace("ws://", "http://").replace("/v1/plugin", "/v1/link")
    async with aiohttp.ClientSession() as http:
        async with http.post(http_url, json={"code": code}) as resp:
            body = await resp.json()
            if resp.status != 200:
                raise SystemExit(f"Linking failed: {body.get('error')}")
            print(f"Linked as '{body['name']}' ({body['server_id']})")
            return body["token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8765/v1/plugin")
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--token", help="an existing server token")
    who.add_argument("--link", metavar="CODE", help="a link code from /setup (or: python -m mcbridge_bot link-code)")
    ap.add_argument("--console", action="store_true", help="advertise the console capability")
    args = ap.parse_args()
    try:
        token = args.token or asyncio.run(link(args.url, args.link))
        asyncio.run(FakePlugin(args.url, token, args.console).run())
    except KeyboardInterrupt:
        print("\n'Crashed' (no stop event sent)")


if __name__ == "__main__":
    main()