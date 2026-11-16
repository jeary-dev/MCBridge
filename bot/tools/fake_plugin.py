"""A pretend Minecraft plugin, for testing the gateway before the real Java plugin exists.

  python tools/fake_plugin.py --link K7P-2QX       (first time: swap a link code for a token)
  python tools/fake_plugin.py --token <token>      (after that)
  options: [--url ws://localhost:8765/v1/plugin] [--console]

It handshakes, sends heartbeats, makes up some player events, and answers commands.
Type 'stop' + Enter for a clean shutdown, 'lag' to toggle a lag spike, or 'link CODE' to link
the fake player czrbyn to your Discord (get CODE with /account link), or 'join' to test the
join requirement check. Ctrl+C "crashes" it.
"""
from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mcbridge_bot.protocol import Envelope, ErrorCode, ProtocolError, reply_error, reply_ok

PLAYERS = [{"uuid": "f759806f-e772-4945-8b79-c19266849be4", "name": "czrbyn"},
           {"uuid": "00000000-0000-4000-8000-000000000001", "name": "Steve"}]


FAKE_STATS = {"play_time_ticks": 20 * 60 * 60 * 37, "deaths": 12, "mob_kills": 845, "player_kills": 3,
              "blocks_mined": 21456, "distance_cm": 412_345_00, "jumps": 9120, "damage_dealt": 30120,
              "damage_taken": 8800, "fish_caught": 41, "animals_bred": 77, "villager_trades": 15, "items_enchanted": 9}
FAKE_INVENTORY = {
    "armor": [{"type": "diamond_helmet", "amount": 1, "enchantments": [{"id": "protection", "level": 4}]},
              {"type": "netherite_chestplate", "amount": 1, "durability": 512, "max_durability": 592}, None,
              {"type": "iron_boots", "amount": 1}],
    "offhand": {"type": "shield", "amount": 1},
    "hotbar": [{"type": "netherite_sword", "amount": 1, "name": "Excalibur",
                "enchantments": [{"id": "sharpness", "level": 5}, {"id": "looting", "level": 3}]},
               {"type": "bow", "amount": 1}, None, {"type": "cooked_beef", "amount": 48}, None, None, None, None,
               {"type": "torch", "amount": 64}],
    "main": [{"type": "cobblestone", "amount": 64, "block": True}, {"type": "oak_log", "amount": 32, "block": True},
             None, {"type": "diamond", "amount": 7},
             {"type": "purple_shulker_box", "amount": 1, "block": True,
              "contents": [{"type": "iron_ingot", "amount": 64}, {"type": "gold_ingot", "amount": 20}] + [None] * 25}],
    "selected_slot": 0,
    "online": True,
    "ender_chest": [{"type": "ender_pearl", "amount": 16}, {"type": "elytra", "amount": 1}] + [None] * 25,
}
FAKE_PLAYER_INFO = {"online": True, "health": 17.0, "max_health": 20.0, "food": 18, "saturation": 5.0, "level": 27,
                    "exp": 0.42, "world": "world", "environment": "normal", "gamemode": "survival", "ping": 35,
                    "op": False, "whitelisted": True, "banned": False, "first_played": 1_700_000_000_000,
                    "last_played": 1_700_000_000_000}
FAKE_ADVANCEMENTS = {"online": True, "done": 41, "total": 122,
                     "tabs": [{"id": "minecraft:story/root", "title": "Minecraft", "done": 11, "total": 16},
                              {"id": "minecraft:nether/root", "title": "Nether", "done": 9, "total": 24},
                              {"id": "minecraft:end/root", "title": "The End", "done": 2, "total": 9},
                              {"id": "minecraft:adventure/root", "title": "Adventure", "done": 12, "total": 46},
                              {"id": "minecraft:husbandry/root", "title": "Husbandry", "done": 7, "total": 27}],
                     "recent": [{"key": "minecraft:story/mine_diamond", "title": "Diamonds!",
                                 "tab": "minecraft:story/root", "tab_title": "Minecraft", "frame": "task",
                                 "ts": 1_700_000_000_000}]}
FAKE_DIAGNOSTICS = {
    "worlds": [{"name": "world", "chunks": 1840, "entities": 4210, "tile_entities": 960, "players": 2},
               {"name": "world_nether", "chunks": 212, "entities": 380, "tile_entities": 40, "players": 0}],
    "top_chunks": [{"world": "world", "x": 12, "z": -30, "entities": 1150, "tile_entities": 4},
                   {"world": "world", "x": -3, "z": 8, "entities": 240, "tile_entities": 310}],
    "top_entities": [{"type": "CHICKEN", "count": 1210}, {"type": "ITEM", "count": 840},
                     {"type": "ZOMBIE", "count": 320}],
}


class FakePlugin:
    def __init__(self, url: str, token: str, console: bool):
        self.url, self.token = url, token
        self.capabilities = ["chat", "whitelist", "diagnostics", "link", "moderation", "stats", "inventory", "message",
                             "roles", "player_info", "advancements", "join_gate"] + (["console", "console_stream"] if console else [])
        self.console_stream = False
        self.online: list[dict] = []
        self.lagging = False

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
            tps = round(random.uniform(8.0, 12.0) if self.lagging else random.uniform(18.5, 20.0), 2)
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
            if self.console_stream:
                await ws.send_str(Envelope(type="event.console", data={"lines": [
                    f"[{time.strftime('%H:%M:%S')} INFO]: {p['name']}[/127.0.0.1:{random.randint(40000, 60000)}] did something"
                ]}).to_json())
            if p not in self.online:
                self.online.append(p)
                env = Envelope(type="event.player_join", data={"player": p, "first_join": False})
                await ws.send_str(env.to_json())
                env = Envelope(type="event.player_groups", data={"player": p, "groups": ["default", "vip"],
                                                                  "reason": "join"})
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
            needs = {"cmd.chat_send": "chat", "cmd.whitelist": "whitelist", "cmd.console": "console",
                     "cmd.diagnostics": "diagnostics", "cmd.link_result": "link"}.get(env.type)
            if env.type == "cmd.diagnostics":
                out = reply_ok(env, "", FAKE_DIAGNOSTICS)
            elif env.type == "cmd.player_stats":
                out = reply_ok(env, "", {"name": env.data["player_name"], "uuid": PLAYERS[0]["uuid"], "online": True,
                                         "stats": FAKE_STATS, "advancements": {"done": 58, "total": 122}})
            elif env.type == "cmd.inventory":
                out = reply_ok(env, "", dict(FAKE_INVENTORY, name=env.data["player_name"], uuid=PLAYERS[0]["uuid"]))
            elif env.type == "cmd.player_info":
                out = reply_ok(env, "", dict(FAKE_PLAYER_INFO, name=env.data["player_name"], uuid=PLAYERS[0]["uuid"]))
            elif env.type == "cmd.advancements":
                out = reply_ok(env, "", dict(FAKE_ADVANCEMENTS, name=env.data["player_name"], uuid=PLAYERS[0]["uuid"]))
            elif env.type == "cmd.access_result":
                print("Join check:", env.data)
                out = reply_ok(env, "ok")
            elif env.type == "cmd.moderate":
                out = reply_ok(env, f"(fake) {env.data['action']} {env.data['player_name']}")
            elif env.type == "cmd.message":
                out = reply_ok(env, f"Sent to {env.data['player_name']}")
            elif env.type == "cmd.tab_complete":
                words = ["say", "list", "time", "weather", "whitelist", "gamemode", "give", "tp"]
                last = env.data["command"].split(" ")[-1]
                out = reply_ok(env, "", {"suggestions": [w for w in words if w.startswith(last)]})
            elif env.type == "cmd.set_features":
                self.console_stream = env.data["console_stream"]
                print("Console stream", "on" if self.console_stream else "off")
                out = reply_ok(env, "ok")
            elif env.type == "cmd.set_groups":
                print("Set groups:", env.data)
                out = reply_ok(env, "ok")
            elif env.type == "cmd.link_result":
                print("Link result for czrbyn:", env.data["message"])
                out = reply_ok(env, "sent")
            elif needs is None:
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
            if line.strip() == "lag":
                self.lagging = not self.lagging
                print("Lag spike", "on" if self.lagging else "off")
            elif line.strip() == "join":
                await ws.send_str(Envelope(type="event.access_request", data={
                    "player": PLAYERS[0], "request_id": "fake-1"}).to_json())
            elif line.strip().startswith("link "):
                await ws.send_str(Envelope(type="event.link_request", data={
                    "player": PLAYERS[0], "code": line.split()[1]}).to_json())
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
