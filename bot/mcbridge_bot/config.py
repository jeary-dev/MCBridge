"""Settings come from environment variables, usually loaded from a `.env` file.

The `.env` file holds the Discord bot token, so it is in .gitignore and must NEVER be committed.
Copy `.env.example` to `.env` and fill it in.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(path: str | Path = ".env") -> None:
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    discord_token: str | None
    dev_guild_id: int | None
    host: str
    port: int
    db_path: str
    public_ws_url: str | None
    chat_bridge: bool
    max_servers_per_guild: int
    trust_cloudflare: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        guild = os.environ.get("DEV_GUILD_ID", "").strip()
        return cls(
            discord_token=os.environ.get("DISCORD_TOKEN") or None,
            dev_guild_id=int(guild) if guild.isdigit() else None,
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(os.environ.get("PORT", "8765")),
            db_path=os.environ.get("DB_PATH", "mcbridge.db"),
            public_ws_url=os.environ.get("PUBLIC_WS_URL") or None,
            chat_bridge=_bool(os.environ.get("CHAT_BRIDGE"), True),
            max_servers_per_guild=int(os.environ.get("MAX_SERVERS_PER_GUILD", "3")),
            trust_cloudflare=_bool(os.environ.get("TRUST_CLOUDFLARE"), False),
        )