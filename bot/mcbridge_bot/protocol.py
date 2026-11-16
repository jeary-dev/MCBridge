"""mcbridge protocol v1 - Python side. See docs/PROTOCOL.md for the spec.

Everything that crosses the WebSocket goes through `Envelope.from_json` (incoming)
or `Envelope.to_json` (outgoing), so malformed messages are caught in one place.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 256 * 1024
MAX_CHAT_LEN = 256
MAX_CONSOLE_LEN = 1000
MAX_ICON_CHARS = 24 * 1024


class ProtocolError(Exception):
    pass


class ErrorCode(str, Enum):
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    FORBIDDEN = "FORBIDDEN"
    INVALID = "INVALID"
    PLAYER_NOT_FOUND = "PLAYER_NOT_FOUND"
    INTERNAL = "INTERNAL"


def _require(data: dict, key: str, kind: type | tuple[type, ...]) -> Any:
    if key not in data:
        raise ProtocolError(f"missing field '{key}'")
    value = data[key]
    if isinstance(value, bool) and kind in (int, float, (int, float)):
        raise ProtocolError(f"field '{key}' has wrong type")
    if not isinstance(value, kind):
        raise ProtocolError(f"field '{key}' has wrong type")
    return value


def _require_choice(data: dict, key: str, choices: set[str]) -> str:
    value = _require(data, key, str)
    if value not in choices:
        raise ProtocolError(f"field '{key}' must be one of {sorted(choices)}")
    return value


def _require_text(data: dict, key: str, max_len: int) -> str:
    value = _require(data, key, str)
    if not value.strip():
        raise ProtocolError(f"field '{key}' is empty")
    if len(value) > max_len:
        raise ProtocolError(f"field '{key}' is longer than {max_len} characters")
    return value


@dataclass(frozen=True)
class Player:
    uuid: str
    name: str

    @classmethod
    def from_dict(cls, d: Any) -> "Player":
        if not isinstance(d, dict):
            raise ProtocolError("player must be an object")
        return cls(uuid=_require(d, "uuid", str), name=_require(d, "name", str))

    def to_dict(self) -> dict:
        return {"uuid": self.uuid, "name": self.name}


@dataclass(frozen=True)
class Actor:
    discord_id: str
    name: str

    @classmethod
    def from_dict(cls, d: Any) -> "Actor":
        if not isinstance(d, dict):
            raise ProtocolError("actor must be an object")
        return cls(discord_id=_require(d, "discord_id", str), name=_require(d, "name", str))

    def to_dict(self) -> dict:
        return {"discord_id": self.discord_id, "name": self.name}


def _v_hello(d):
    _require(d, "plugin_version", str)
    _require_choice(d, "platform", {"paper", "fabric", "neoforge", "velocity"})
    _require(d, "mc_version", str)
    caps = _require(d, "capabilities", list)
    if not all(isinstance(c, str) for c in caps):
        raise ProtocolError("capabilities must be strings")
    if "icon" in d and d["icon"] is not None:
        icon = _require(d, "icon", str)
        if len(icon) > MAX_ICON_CHARS:
            raise ProtocolError("icon is too large")
    if "motd" in d and d["motd"] is not None:
        _require(d, "motd", str)


def _v_welcome(d):
    _require(d, "server_id", str)
    if _require(d, "heartbeat_interval_s", int) < 1:
        raise ProtocolError("heartbeat_interval_s must be >= 1")
    _require(d, "features", dict)


def _v_heartbeat(d):
    tps = _require(d, "tps", list)
    if len(tps) != 3 or not all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in tps):
        raise ProtocolError("tps must be 3 numbers")
    _require(d, "mspt", (int, float))
    for p in _require(d, "players", list):
        Player.from_dict(p)
    _require(d, "max_players", int)
    mem = _require(d, "memory", dict)
    _require(mem, "used_mb", int)
    _require(mem, "max_mb", int)
    _require(d, "uptime_s", int)


def _v_player_only(d):
    Player.from_dict(_require(d, "player", dict))


VALIDATORS: dict[str, Callable[[dict], None]] = {
    "hello": _v_hello,
    "welcome": _v_welcome,
    "heartbeat": _v_heartbeat,
    "event.server_start": lambda d: (_require(d, "motd", str), _require(d, "max_players", int)),
    "event.server_stop": lambda d: _require_choice(d, "reason", {"shutdown", "restart"}),
    "event.player_join": lambda d: (_v_player_only(d), _require(d, "first_join", bool)),
    "event.player_leave": lambda d: (_v_player_only(d),
                                     _require_choice(d, "reason", {"quit", "kick", "ban"}),
                                     _require(d, "session_s", int)),
    "event.player_chat": lambda d: (_v_player_only(d), _require_text(d, "message", MAX_CHAT_LEN)),
    "event.player_death": lambda d: (_v_player_only(d), _require(d, "message", str)),
    "event.player_advancement": lambda d: (_v_player_only(d), _require(d, "key", str), _require(d, "title", str)),
    "cmd.chat_send": lambda d: (Actor.from_dict(_require(d, "actor", dict)),
                                _require_text(d, "message", MAX_CHAT_LEN)),
    "cmd.whitelist": lambda d: (Actor.from_dict(_require(d, "actor", dict)),
                                _require_choice(d, "action", {"add", "remove"}),
                                _require_text(d, "player_name", 16)),
    "event.link_request": lambda d: (_v_player_only(d), _require_text(d, "code", 12)),
    "event.console": lambda d: _v_console_lines(d),
    "event.player_groups": lambda d: (_v_player_only(d), _v_string_list(d, "groups", 200),
                                      _optional_choice(d, "reason", {"join", "change"})),
    "cmd.console": lambda d: _v_console(d),
    "cmd.diagnostics": lambda d: Actor.from_dict(_require(d, "actor", dict)),
    "cmd.moderate": lambda d: _v_moderate(d),
    "cmd.tab_complete": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _v_max_len(d, "command", MAX_CONSOLE_LEN)),
    "cmd.player_stats": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _require_text(d, "player_name", 16)),
    "cmd.inventory": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _require_text(d, "player_name", 16)),
    "cmd.message": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _require_text(d, "player_name", 16),
                              _require_text(d, "message", MAX_CHAT_LEN)),
    "cmd.set_groups": lambda d: (_require(d, "player_uuid", str), _v_string_list(d, "add", 50),
                                 _v_string_list(d, "remove", 50)),
    "cmd.player_info": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _require_text(d, "player_name", 16)),
    "cmd.advancements": lambda d: (Actor.from_dict(_require(d, "actor", dict)), _require_text(d, "player_name", 16)),
    "cmd.set_features": lambda d: (_require(d, "console_stream", bool),
                                   _optional_choice(d, "join_requirement", JOIN_MODES)),
    "event.access_request": lambda d: (_v_player_only(d), _require_text(d, "request_id", 64)),
    "cmd.access_result": lambda d: _v_access_result(d),
    "cmd.link_result": lambda d: (_require(d, "player_uuid", str), _require(d, "ok", bool),
                                  _require_text(d, "message", 256)),
    "reply": lambda d: _v_reply(d),
}


JOIN_MODES = {"off", "linked", "role"}
ACCESS_REASONS = {"not_linked", "missing_role", "not_in_discord", "error"}


def _v_access_result(d):
    _require_text(d, "request_id", 64)
    allowed = _require(d, "allowed", bool)
    if not allowed:
        _require_choice(d, "reason", ACCESS_REASONS)
    for key in ("code", "role", "discord"):
        if key in d and d[key] is not None:
            _v_max_len(d, key, 100)


MODERATION_ACTIONS = {"kick", "ban", "unban", "op", "deop", "gamemode"}
GAMEMODES = {"survival", "creative", "adventure", "spectator"}
MAX_CONSOLE_LINES = 200


def _v_moderate(d):
    Actor.from_dict(_require(d, "actor", dict))
    action = _require_choice(d, "action", MODERATION_ACTIONS)
    _require_text(d, "player_name", 16)
    if "reason" in d and d["reason"] is not None:
        _v_max_len(d, "reason", 200)
    if action == "gamemode":
        _require_choice(d, "gamemode", GAMEMODES)


def _v_max_len(d, key, max_len):
    value = _require(d, key, str)
    if len(value) > max_len:
        raise ProtocolError(f"field '{key}' is longer than {max_len} characters")
    return value


def _v_string_list(d, key, max_items):
    items = _require(d, key, list)
    if len(items) > max_items or not all(isinstance(i, str) and len(i) <= 100 for i in items):
        raise ProtocolError(f"field '{key}' must be a list of up to {max_items} short strings")
    return items


def _optional_choice(d, key, choices):
    if key in d and d[key] is not None:
        _require_choice(d, key, choices)


def _v_console_lines(d):
    lines = _require(d, "lines", list)
    if len(lines) > MAX_CONSOLE_LINES or not all(isinstance(line, str) and len(line) <= 4000 for line in lines):
        raise ProtocolError("lines must be a list of up to 200 strings")


def _v_console(d):
    Actor.from_dict(_require(d, "actor", dict))
    command = _require_text(d, "command", MAX_CONSOLE_LEN)
    if command.startswith("/"):
        raise ProtocolError("console command must not start with '/'")


def _v_reply(d):
    ok = _require(d, "ok", bool)
    if "data" in d and d["data"] is not None:
        _require(d, "data", dict)
    if not ok:
        err = _require(d, "error", dict)
        code = _require(err, "code", str)
        if code not in ErrorCode._value2member_map_:
            raise ProtocolError(f"unknown error code '{code}'")
        _require(err, "message", str)


@dataclass
class Envelope:
    type: str
    data: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: int = field(default_factory=lambda: int(time.time() * 1000))
    reply_to: str | None = None
    v: int = PROTOCOL_VERSION

    @property
    def known(self) -> bool:
        return self.type in VALIDATORS

    def validate(self) -> "Envelope":
        if self.type == "reply" and not self.reply_to:
            raise ProtocolError("reply must have reply_to")
        if self.known:
            VALIDATORS[self.type](self.data)
        return self

    def to_json(self) -> str:
        self.validate()
        text = json.dumps({"v": self.v, "type": self.type, "id": self.id, "ts": self.ts,
                           "reply_to": self.reply_to, "data": self.data}, separators=(",", ":"))
        if len(text.encode()) > MAX_FRAME_BYTES:
            raise ProtocolError("message is larger than 256 KiB")
        return text

    @classmethod
    def from_json(cls, text: str) -> "Envelope":
        if len(text.encode()) > MAX_FRAME_BYTES:
            raise ProtocolError("message is larger than 256 KiB")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"not valid JSON: {e}") from None
        if not isinstance(raw, dict):
            raise ProtocolError("envelope must be a JSON object")
        if _require(raw, "v", int) != PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version {raw['v']}")
        reply_to = raw.get("reply_to")
        if reply_to is not None and not isinstance(reply_to, str):
            raise ProtocolError("reply_to must be a string or null")
        env = cls(type=_require(raw, "type", str), data=_require(raw, "data", dict),
                  id=_require(raw, "id", str), ts=_require(raw, "ts", int), reply_to=reply_to)
        return env.validate()


def command(cmd_type: str, actor: Actor, **fields) -> Envelope:
    return Envelope(type=cmd_type, data={"actor": actor.to_dict(), **fields}).validate()


def reply_ok(to: Envelope, result: str = "", data: dict | None = None) -> Envelope:
    payload = {"ok": True, "result": result}
    if data is not None:
        payload["data"] = data
    return Envelope(type="reply", reply_to=to.id, data=payload).validate()


def reply_error(to: Envelope, code: ErrorCode, message: str) -> Envelope:
    return Envelope(type="reply", reply_to=to.id,
                    data={"ok": False, "error": {"code": code.value, "message": message}}).validate()
