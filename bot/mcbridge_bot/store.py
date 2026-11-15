"""Everything MCBridge remembers, in one SQLite database.

Multi-tenant from day one: every Minecraft server belongs to exactly one Discord
server ("guild"), and nothing is ever looked up without knowing who owns it.

Secrets (server tokens, link codes) are only stored as SHA-256 hashes.
SQLite is perfect while small; the schema moves to PostgreSQL unchanged later.
"""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass

LINK_CODE_TTL_S = 10 * 60
LINK_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

SCHEMA = """
CREATE TABLE IF NOT EXISTS servers (
    server_id   TEXT PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    name        TEXT NOT NULL,
    token_hash  TEXT NOT NULL UNIQUE,
    address     TEXT,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS servers_by_guild ON servers(guild_id);

CREATE TABLE IF NOT EXISTS link_codes (
    code_hash   TEXT PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    server_name TEXT NOT NULL,
    created_by  TEXT NOT NULL,
    channel_id  TEXT,
    expires_at  INTEGER NOT NULL,
    used        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS channels (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    PRIMARY KEY (server_id, kind)
);

CREATE INDEX IF NOT EXISTS channels_by_channel ON channels(channel_id, kind);

CREATE TABLE IF NOT EXISTS settings (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    PRIMARY KEY (server_id, key)
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          INTEGER NOT NULL,
    guild_id    TEXT NOT NULL,
    server_id   TEXT,
    actor_id    TEXT NOT NULL,
    actor_name  TEXT NOT NULL,
    action      TEXT NOT NULL,
    detail      TEXT,
    result      TEXT
);
"""


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def normalize_code(code: str) -> str:
    return "".join(ch for ch in code.upper() if ch.isalnum())


@dataclass(frozen=True)
class ServerRecord:
    server_id: str
    guild_id: str
    name: str
    token_hash: str
    address: str | None = None


class Store:
    def __init__(self, path: str = "mcbridge.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def create_server(self, guild_id: str, name: str, address: str | None = None) -> tuple[ServerRecord, str]:
        token = secrets.token_urlsafe(32)
        rec = ServerRecord(server_id="srv_" + secrets.token_hex(6), guild_id=guild_id,
                           name=name, token_hash=_hash(token), address=address)
        self.db.execute(
            "INSERT INTO servers (server_id, guild_id, name, token_hash, address, created_at) VALUES (?,?,?,?,?,?)",
            (rec.server_id, rec.guild_id, rec.name, rec.token_hash, rec.address, int(time.time())))
        self.db.commit()
        return rec, token

    def authenticate(self, token: str) -> ServerRecord | None:
        row = self.db.execute("SELECT * FROM servers WHERE token_hash = ?", (_hash(token),)).fetchone()
        return self._server(row)

    def get_server(self, server_id: str) -> ServerRecord | None:
        return self._server(self.db.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,)).fetchone())

    def servers_for_guild(self, guild_id: str) -> list[ServerRecord]:
        rows = self.db.execute("SELECT * FROM servers WHERE guild_id = ? ORDER BY created_at", (guild_id,))
        return [self._server(r) for r in rows]

    def set_address(self, server_id: str, address: str | None) -> None:
        self.db.execute("UPDATE servers SET address = ? WHERE server_id = ?", (address, server_id))
        self.db.commit()

    def delete_server(self, server_id: str) -> None:
        self.db.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
        self.db.commit()

    @staticmethod
    def _server(row) -> ServerRecord | None:
        if row is None:
            return None
        return ServerRecord(row["server_id"], row["guild_id"], row["name"], row["token_hash"], row["address"])

    def create_link_code(self, guild_id: str, server_name: str, created_by: str,
                         channel_id: str | None = None) -> str:
        raw = "".join(secrets.choice(LINK_CODE_ALPHABET) for _ in range(6))
        self.db.execute(
            "INSERT INTO link_codes (code_hash, guild_id, server_name, created_by, channel_id, expires_at) "
            "VALUES (?,?,?,?,?,?)",
            (_hash(raw), guild_id, server_name, created_by, channel_id, int(time.time()) + LINK_CODE_TTL_S))
        self.db.execute("DELETE FROM link_codes WHERE expires_at < ? OR used = 1", (int(time.time()),))
        self.db.commit()
        return f"{raw[:3]}-{raw[3:]}"

    def redeem_link_code(self, code: str) -> tuple[ServerRecord, str] | None:
        row = self.db.execute(
            "SELECT * FROM link_codes WHERE code_hash = ? AND used = 0 AND expires_at >= ?",
            (_hash(normalize_code(code)), int(time.time()))).fetchone()
        if row is None:
            return None
        self.db.execute("UPDATE link_codes SET used = 1 WHERE code_hash = ?", (row["code_hash"],))
        self.db.commit()
        rec, token = self.create_server(row["guild_id"], row["server_name"])
        if row["channel_id"]:
            self.set_channel(rec.server_id, "alerts", row["channel_id"])
        return rec, token

    def set_channel(self, server_id: str, kind: str, channel_id: str | None) -> None:
        if channel_id is None:
            self.db.execute("DELETE FROM channels WHERE server_id = ? AND kind = ?", (server_id, kind))
        else:
            self.db.execute("INSERT OR REPLACE INTO channels (server_id, kind, channel_id) VALUES (?,?,?)",
                            (server_id, kind, channel_id))
        self.db.commit()

    def get_channel(self, server_id: str, kind: str) -> str | None:
        row = self.db.execute("SELECT channel_id FROM channels WHERE server_id = ? AND kind = ?",
                              (server_id, kind)).fetchone()
        return row["channel_id"] if row else None

    def servers_for_channel(self, channel_id: str, kind: str) -> list[ServerRecord]:
        rows = self.db.execute(
            "SELECT s.* FROM servers s JOIN channels c ON c.server_id = s.server_id "
            "WHERE c.channel_id = ? AND c.kind = ?", (channel_id, kind))
        return [self._server(r) for r in rows]

    def set_setting(self, server_id: str, key: str, value: str | None) -> None:
        if value is None:
            self.db.execute("DELETE FROM settings WHERE server_id = ? AND key = ?", (server_id, key))
        else:
            self.db.execute("INSERT OR REPLACE INTO settings (server_id, key, value) VALUES (?,?,?)",
                            (server_id, key, value))
        self.db.commit()

    def get_setting(self, server_id: str, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM settings WHERE server_id = ? AND key = ?",
                              (server_id, key)).fetchone()
        return row["value"] if row else None

    def servers_with_setting(self, key: str) -> list[tuple[ServerRecord, str]]:
        rows = self.db.execute(
            "SELECT s.*, t.value AS setting_value FROM servers s JOIN settings t ON t.server_id = s.server_id "
            "WHERE t.key = ?", (key,))
        return [(self._server(r), r["setting_value"]) for r in rows]

    def delete_guild(self, guild_id: str) -> list[str]:
        ids = [r.server_id for r in self.servers_for_guild(guild_id)]
        self.db.execute("DELETE FROM servers WHERE guild_id = ?", (guild_id,))
        self.db.execute("DELETE FROM link_codes WHERE guild_id = ?", (guild_id,))
        self.db.commit()
        return ids

    def audit(self, guild_id: str, server_id: str | None, actor_id: str, actor_name: str,
              action: str, detail: str = "", result: str = "") -> None:
        self.db.execute(
            "INSERT INTO audit_log (ts, guild_id, server_id, actor_id, actor_name, action, detail, result) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (int(time.time()), guild_id, server_id, actor_id, actor_name, action, detail, result))
        self.db.commit()

    def recent_audit(self, guild_id: str, limit: int = 20) -> list[dict]:
        rows = self.db.execute("SELECT * FROM audit_log WHERE guild_id = ? ORDER BY id DESC LIMIT ?",
                               (guild_id, limit))
        return [dict(r) for r in rows]