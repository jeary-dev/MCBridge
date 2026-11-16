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

CREATE TABLE IF NOT EXISTS samples (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    ts          INTEGER NOT NULL,
    tps         REAL NOT NULL,
    mspt        REAL NOT NULL,
    players     INTEGER NOT NULL,
    mem_used    INTEGER NOT NULL,
    mem_max     INTEGER NOT NULL,
    PRIMARY KEY (server_id, ts)
);

CREATE TABLE IF NOT EXISTS players (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    uuid        TEXT NOT NULL,
    name        TEXT NOT NULL,
    first_seen  INTEGER NOT NULL,
    last_seen   INTEGER NOT NULL,
    playtime_s  INTEGER NOT NULL DEFAULT 0,
    joins       INTEGER NOT NULL DEFAULT 0,
    deaths      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (server_id, uuid)
);
CREATE INDEX IF NOT EXISTS players_by_name ON players(server_id, name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS open_sessions (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    uuid        TEXT NOT NULL,
    name        TEXT NOT NULL,
    joined_at   INTEGER NOT NULL,
    PRIMARY KEY (server_id, uuid)
);

CREATE TABLE IF NOT EXISTS session_log (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    uuid        TEXT NOT NULL,
    name        TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    ended_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS session_log_by_time ON session_log(server_id, ended_at);

CREATE TABLE IF NOT EXISTS account_links (
    guild_id    TEXT NOT NULL,
    discord_id  TEXT NOT NULL,
    uuid        TEXT NOT NULL,
    name        TEXT NOT NULL,
    linked_at   INTEGER NOT NULL,
    PRIMARY KEY (guild_id, discord_id),
    UNIQUE (guild_id, uuid)
);

CREATE TABLE IF NOT EXISTS account_codes (
    code_hash   TEXT PRIMARY KEY,
    guild_id    TEXT NOT NULL,
    discord_id  TEXT NOT NULL,
    expires_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS whitelist_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    discord_id  TEXT NOT NULL,
    player      TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  INTEGER NOT NULL,
    decided_by  TEXT,
    channel_id  TEXT,
    message_id  TEXT
);

CREATE TABLE IF NOT EXISTS role_links (
    server_id   TEXT NOT NULL REFERENCES servers(server_id) ON DELETE CASCADE,
    group_name  TEXT NOT NULL,
    role_id     TEXT NOT NULL,
    direction   TEXT NOT NULL,
    PRIMARY KEY (server_id, group_name)
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
        self.db.execute("DELETE FROM account_links WHERE guild_id = ?", (guild_id,))
        self.db.execute("DELETE FROM account_codes WHERE guild_id = ?", (guild_id,))
        self.db.commit()
        return ids

    def add_sample(self, server_id: str, ts: int, heartbeat: dict) -> None:
        mem = heartbeat["memory"]
        self.db.execute(
            "INSERT OR REPLACE INTO samples (server_id, ts, tps, mspt, players, mem_used, mem_max) "
            "VALUES (?,?,?,?,?,?,?)",
            (server_id, ts, float(heartbeat["tps"][0]), float(heartbeat["mspt"]), len(heartbeat["players"]),
             int(mem["used_mb"]), int(mem["max_mb"])))
        self.db.commit()

    def samples(self, server_id: str, since: int, until: int | None = None) -> list[dict]:
        rows = self.db.execute(
            "SELECT ts, tps, mspt, players, mem_used, mem_max FROM samples "
            "WHERE server_id = ? AND ts >= ? AND ts <= ? ORDER BY ts",
            (server_id, since, until if until is not None else 2**62))
        return [dict(r) for r in rows]

    def prune(self, older_than: int) -> None:
        self.db.execute("DELETE FROM samples WHERE ts < ?", (older_than,))
        self.db.execute("DELETE FROM session_log WHERE ended_at < ?", (older_than,))
        self.db.execute("DELETE FROM account_codes WHERE expires_at < ?", (int(time.time()),))
        self.db.commit()

    def player_joined(self, server_id: str, uuid: str, name: str, ts: int) -> None:
        self.db.execute(
            "INSERT INTO players (server_id, uuid, name, first_seen, last_seen, joins) VALUES (?,?,?,?,?,1) "
            "ON CONFLICT (server_id, uuid) DO UPDATE SET name = excluded.name, last_seen = excluded.last_seen, "
            "joins = joins + 1", (server_id, uuid, name, ts, ts))
        self.db.execute("INSERT OR IGNORE INTO open_sessions (server_id, uuid, name, joined_at) VALUES (?,?,?,?)",
                        (server_id, uuid, name, ts))
        self.db.commit()

    def player_left(self, server_id: str, uuid: str, ts: int) -> None:
        row = self.db.execute("SELECT * FROM open_sessions WHERE server_id = ? AND uuid = ?",
                              (server_id, uuid)).fetchone()
        if row is None:
            return
        self._close_session(row, ts)
        self.db.commit()

    def _close_session(self, row, ts: int) -> None:
        played = max(0, ts - row["joined_at"])
        self.db.execute("DELETE FROM open_sessions WHERE server_id = ? AND uuid = ?", (row["server_id"], row["uuid"]))
        self.db.execute("UPDATE players SET playtime_s = playtime_s + ?, last_seen = ? WHERE server_id = ? AND uuid = ?",
                        (played, ts, row["server_id"], row["uuid"]))
        self.db.execute("INSERT INTO session_log (server_id, uuid, name, started_at, ended_at) VALUES (?,?,?,?,?)",
                        (row["server_id"], row["uuid"], row["name"], row["joined_at"], ts))

    def player_died(self, server_id: str, uuid: str) -> None:
        self.db.execute("UPDATE players SET deaths = deaths + 1 WHERE server_id = ? AND uuid = ?", (server_id, uuid))
        self.db.commit()

    def sync_online(self, server_id: str, online: list[dict], ts: int) -> None:
        online_ids = {p["uuid"] for p in online}
        for row in self.db.execute("SELECT * FROM open_sessions WHERE server_id = ?", (server_id,)).fetchall():
            if row["uuid"] not in online_ids:
                self._close_session(row, ts)
        open_ids = {r["uuid"] for r in self.db.execute("SELECT uuid FROM open_sessions WHERE server_id = ?",
                                                        (server_id,))}
        self.db.commit()
        for p in online:
            if p["uuid"] not in open_ids:
                self.player_joined(server_id, p["uuid"], p["name"], ts)

    def close_all_sessions(self, server_id: str, ts: int) -> None:
        for row in self.db.execute("SELECT * FROM open_sessions WHERE server_id = ?", (server_id,)).fetchall():
            self._close_session(row, ts)
        self.db.commit()

    def player(self, server_id: str, name_or_uuid: str, now: int | None = None) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM players WHERE server_id = ? AND (uuid = ? OR name = ? COLLATE NOCASE) "
            "ORDER BY last_seen DESC LIMIT 1", (server_id, name_or_uuid, name_or_uuid)).fetchone()
        if row is None:
            return None
        out = dict(row)
        live = self.db.execute("SELECT joined_at FROM open_sessions WHERE server_id = ? AND uuid = ?",
                               (server_id, row["uuid"])).fetchone()
        out["online"] = live is not None
        if live is not None:
            out["playtime_s"] += max(0, (now or int(time.time())) - live["joined_at"])
        return out

    def player_names(self, server_id: str, prefix: str, limit: int = 25) -> list[str]:
        rows = self.db.execute(
            "SELECT name FROM players WHERE server_id = ? AND name LIKE ? ESCAPE '\\' ORDER BY last_seen DESC LIMIT ?",
            (server_id, prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%", limit))
        return [r["name"] for r in rows]

    def top_players(self, server_id: str, limit: int = 10, now: int | None = None) -> list[dict]:
        now = now or int(time.time())
        rows = self.db.execute(
            "SELECT p.uuid, p.name, p.playtime_s + COALESCE(? - o.joined_at, 0) AS playtime_s, "
            "o.joined_at IS NOT NULL AS online "
            "FROM players p LEFT JOIN open_sessions o ON o.server_id = p.server_id AND o.uuid = p.uuid "
            "WHERE p.server_id = ? ORDER BY playtime_s DESC LIMIT ?", (now, server_id, limit))
        return [dict(r) for r in rows]

    def recap(self, server_id: str, since: int, until: int) -> dict:
        samples = self.samples(server_id, since, until)
        played: dict[str, dict] = {}
        rows = list(self.db.execute(
            "SELECT uuid, name, started_at, ended_at FROM session_log "
            "WHERE server_id = ? AND ended_at > ? AND started_at < ?", (server_id, since, until)))
        rows += [{"uuid": r["uuid"], "name": r["name"], "started_at": r["joined_at"], "ended_at": until}
                 for r in self.db.execute("SELECT * FROM open_sessions WHERE server_id = ?", (server_id,))]
        for r in rows:
            secs = max(0, min(r["ended_at"], until) - max(r["started_at"], since))
            entry = played.setdefault(r["uuid"], {"uuid": r["uuid"], "name": r["name"], "playtime_s": 0})
            entry["playtime_s"] += secs
        new_players = self.db.execute(
            "SELECT COUNT(*) FROM players WHERE server_id = ? AND first_seen >= ? AND first_seen < ?",
            (server_id, since, until)).fetchone()[0]
        tps = [s["tps"] for s in samples]
        return {
            "samples": samples,
            "online_minutes": len(samples),
            "window_minutes": max(1, (until - since) // 60),
            "peak_players": max((s["players"] for s in samples), default=0),
            "avg_tps": sum(tps) / len(tps) if tps else None,
            "lag_minutes": sum(1 for t in tps if t < 15),
            "unique_players": len(played),
            "new_players": new_players,
            "playtime_s": sum(p["playtime_s"] for p in played.values()),
            "top": sorted(played.values(), key=lambda p: p["playtime_s"], reverse=True)[:3],
        }

    def create_account_code(self, guild_id: str, discord_id: str) -> str:
        raw = "".join(secrets.choice(LINK_CODE_ALPHABET) for _ in range(6))
        self.db.execute("DELETE FROM account_codes WHERE guild_id = ? AND discord_id = ?", (guild_id, discord_id))
        self.db.execute("INSERT INTO account_codes (code_hash, guild_id, discord_id, expires_at) VALUES (?,?,?,?)",
                        (_hash(guild_id + ":" + raw), guild_id, discord_id, int(time.time()) + LINK_CODE_TTL_S))
        self.db.commit()
        return raw

    def redeem_account_code(self, guild_id: str, code: str, uuid: str, name: str) -> str | None:
        key = _hash(guild_id + ":" + normalize_code(code))
        row = self.db.execute("SELECT * FROM account_codes WHERE code_hash = ? AND expires_at >= ?",
                              (key, int(time.time()))).fetchone()
        if row is None:
            return None
        self.db.execute("DELETE FROM account_codes WHERE code_hash = ?", (key,))
        self.db.execute("DELETE FROM account_links WHERE guild_id = ? AND (discord_id = ? OR uuid = ?)",
                        (guild_id, row["discord_id"], uuid))
        self.db.execute("INSERT INTO account_links (guild_id, discord_id, uuid, name, linked_at) VALUES (?,?,?,?,?)",
                        (guild_id, row["discord_id"], uuid, name, int(time.time())))
        self.db.commit()
        return row["discord_id"]

    def linked_account(self, guild_id: str, discord_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM account_links WHERE guild_id = ? AND discord_id = ?",
                              (guild_id, discord_id)).fetchone()
        return dict(row) if row else None

    def linked_discord(self, guild_id: str, uuid: str) -> str | None:
        row = self.db.execute("SELECT discord_id FROM account_links WHERE guild_id = ? AND uuid = ?",
                              (guild_id, uuid)).fetchone()
        return row["discord_id"] if row else None

    def unlink_account(self, guild_id: str, discord_id: str) -> bool:
        cur = self.db.execute("DELETE FROM account_links WHERE guild_id = ? AND discord_id = ?", (guild_id, discord_id))
        self.db.commit()
        return cur.rowcount > 0

    def create_whitelist_request(self, server_id: str, discord_id: str, player: str) -> int:
        cur = self.db.execute(
            "INSERT INTO whitelist_requests (server_id, discord_id, player, created_at) VALUES (?,?,?,?)",
            (server_id, discord_id, player, int(time.time())))
        self.db.commit()
        return cur.lastrowid

    def pending_whitelist_request(self, server_id: str, discord_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM whitelist_requests WHERE server_id = ? AND discord_id = ? AND status = 'pending'",
            (server_id, discord_id)).fetchone()
        return dict(row) if row else None

    def whitelist_request(self, request_id: int) -> dict | None:
        row = self.db.execute("SELECT * FROM whitelist_requests WHERE id = ?", (request_id,)).fetchone()
        return dict(row) if row else None

    def set_whitelist_request_message(self, request_id: int, channel_id: str, message_id: str) -> None:
        self.db.execute("UPDATE whitelist_requests SET channel_id = ?, message_id = ? WHERE id = ?",
                        (channel_id, message_id, request_id))
        self.db.commit()

    def decide_whitelist_request(self, request_id: int, status: str, decided_by: str) -> bool:
        cur = self.db.execute(
            "UPDATE whitelist_requests SET status = ?, decided_by = ? WHERE id = ? AND status = 'pending'",
            (status, decided_by, request_id))
        self.db.commit()
        return cur.rowcount == 1

    def reopen_whitelist_request(self, request_id: int) -> None:
        self.db.execute("UPDATE whitelist_requests SET status = 'pending', decided_by = NULL WHERE id = ?",
                        (request_id,))
        self.db.commit()

    def set_role_link(self, server_id: str, group: str, role_id: str, direction: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO role_links (server_id, group_name, role_id, direction) VALUES (?,?,?,?)",
                        (server_id, group.lower(), role_id, direction))
        self.db.commit()

    def remove_role_link(self, server_id: str, group: str) -> bool:
        cur = self.db.execute("DELETE FROM role_links WHERE server_id = ? AND group_name = ?",
                              (server_id, group.lower()))
        self.db.commit()
        return cur.rowcount > 0

    def role_links(self, server_id: str) -> list[dict]:
        rows = self.db.execute("SELECT group_name, role_id, direction FROM role_links WHERE server_id = ? "
                               "ORDER BY group_name", (server_id,))
        return [dict(r) for r in rows]

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
