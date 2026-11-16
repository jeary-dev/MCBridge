"""Start MCBridge, or poke the database while developing.

  python -m mcbridge_bot run                       # gateway + Discord bot (reads .env)
  python -m mcbridge_bot run --no-discord          # gateway only, for testing with tools/fake_plugin.py
  python -m mcbridge_bot link-code --name "Test SMP"
  python -m mcbridge_bot list-servers --guild 123
"""
from __future__ import annotations

import argparse
import asyncio
import logging

from aiohttp import web

from .config import Settings, load_env_file
from .gateway import Gateway
from .store import Store

log = logging.getLogger("mcbridge")


async def _mcping_check(address: str) -> bool:
    try:
        from mcping import ping
    except ImportError:
        return False
    return (await ping(address, timeout=3)).online


async def run(settings: Settings, with_discord: bool) -> None:
    store = Store(settings.db_path)
    gateway = Gateway(store, ping_check=_mcping_check, trust_cloudflare=settings.trust_cloudflare)

    if not with_discord:
        @gateway.on
        async def show(session, what, details):
            if what != "heartbeat":
                print(f"[{session.record.name}] {what}: {details}")

    runner = web.AppRunner(gateway.make_app())
    await runner.setup()
    await web.TCPSite(runner, settings.host, settings.port).start()
    log.info("gateway listening on ws://%s:%d/v1/plugin", settings.host, settings.port)

    try:
        if not with_discord:
            await asyncio.Event().wait()
            return
        import discord

        from .discord_bot import MCBridgeBot
        bot = MCBridgeBot(store, gateway, settings)
        try:
            async with bot:
                await bot.start(settings.discord_token)
        except discord.LoginFailure:
            log.error("Discord rejected the token. Check DISCORD_TOKEN in .env (reset it in the Developer Portal).")
        except discord.PrivilegedIntentsRequired:
            log.error("Turn on 'Message Content Intent' in the Developer Portal (Bot tab), "
                      "or set CHAT_BRIDGE=false in .env.")
    finally:
        await runner.cleanup()
        store.close()


def main() -> None:
    load_env_file()
    settings = Settings.from_env()

    parser = argparse.ArgumentParser(prog="mcbridge_bot")
    sub = parser.add_subparsers(dest="cmd", required=True)

    code = sub.add_parser("link-code", help="make a link code (what /setup does in Discord)")
    code.add_argument("--guild", default="dev-guild", help="Discord server id that will own the MC server")
    code.add_argument("--name", required=True, help="a name for the Minecraft server")

    ls = sub.add_parser("list-servers")
    ls.add_argument("--guild", default="dev-guild")

    r = sub.add_parser("run", help="start the gateway and the Discord bot")
    r.add_argument("--no-discord", action="store_true", help="gateway only")

    args = parser.parse_args()

    if args.cmd == "link-code":
        store = Store(settings.db_path)
        print(f"Link code for '{args.name}' (valid 10 minutes, works once): "
              f"{store.create_link_code(args.guild, args.name, created_by='cli')}")
    elif args.cmd == "list-servers":
        store = Store(settings.db_path)
        for rec in store.servers_for_guild(args.guild):
            print(f"{rec.server_id}  {rec.name}  {rec.address or '-'}")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
        with_discord = not args.no_discord
        if with_discord and not settings.discord_token:
            parser.error("DISCORD_TOKEN is missing. Copy .env.example to .env and paste your bot token in, "
                         "or use --no-discord.")
        try:
            asyncio.run(run(settings, with_discord))
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
