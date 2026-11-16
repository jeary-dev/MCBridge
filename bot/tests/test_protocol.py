import json

import pytest

from mcbridge_bot.protocol import (
    Actor,
    Envelope,
    ErrorCode,
    ProtocolError,
    command,
    reply_error,
    reply_ok,
)

ME = Actor(discord_id="123", name="corbyn")
PLAYER = {"uuid": "f759806f-e772-4945-8b79-c19266849be4", "name": "czrbyn"}


def wire(type_, data, **extra):
    env = {"v": 1, "type": type_, "id": "abc", "ts": 1, "reply_to": None, "data": data}
    env.update(extra)
    return json.dumps(env)


HEARTBEAT = {"tps": [20.0, 19.9, 19.8], "mspt": 12.5, "players": [PLAYER], "max_players": 20,
             "memory": {"used_mb": 2000, "max_mb": 6000}, "uptime_s": 60}


def test_command_roundtrip():
    out = command("cmd.whitelist", ME, action="add", player_name="Steve")
    back = Envelope.from_json(out.to_json())
    assert back.type == "cmd.whitelist" and back.data["player_name"] == "Steve" and back.id == out.id


def test_reply_ok_and_error_roundtrip():
    cmd = command("cmd.chat_send", ME, message="hi")
    ok = Envelope.from_json(reply_ok(cmd, "sent").to_json())
    err = Envelope.from_json(reply_error(cmd, ErrorCode.FORBIDDEN, "disabled").to_json())
    assert ok.reply_to == cmd.id and ok.data["ok"] is True
    assert err.data["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("type_,data", [
    ("hello", {"plugin_version": "0.1.0", "platform": "paper", "mc_version": "1.21.11",
               "capabilities": ["chat", "whitelist"]}),
    ("heartbeat", HEARTBEAT),
    ("event.server_start", {"motd": "Hi", "max_players": 20}),
    ("event.server_stop", {"reason": "restart"}),
    ("event.player_join", {"player": PLAYER, "first_join": True}),
    ("event.player_leave", {"player": PLAYER, "reason": "quit", "session_s": 300}),
    ("event.player_chat", {"player": PLAYER, "message": "hello"}),
    ("event.player_death", {"player": PLAYER, "message": "czrbyn fell from a high place"}),
    ("event.player_advancement", {"player": PLAYER, "key": "story/mine_diamond", "title": "Diamonds!"}),
])
def test_valid_plugin_messages(type_, data):
    assert Envelope.from_json(wire(type_, data)).type == type_


def test_unknown_type_is_accepted_but_flagged():
    env = Envelope.from_json(wire("event.something_new", {"anything": 1}))
    assert env.known is False


def test_unknown_fields_are_ignored():
    data = dict(HEARTBEAT, future_field="x")
    assert Envelope.from_json(wire("heartbeat", data)).known


def test_wrong_protocol_version_rejected():
    with pytest.raises(ProtocolError, match="version"):
        Envelope.from_json(wire("heartbeat", HEARTBEAT, v=2))


@pytest.mark.parametrize("text", ["not json", "[1,2,3]", json.dumps({"v": 1})])
def test_garbage_rejected(text):
    with pytest.raises(ProtocolError):
        Envelope.from_json(text)


def test_bool_is_not_a_number():
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("event.server_start", {"motd": "x", "max_players": True}))


def test_bad_heartbeat_tps():
    with pytest.raises(ProtocolError, match="tps"):
        Envelope.from_json(wire("heartbeat", dict(HEARTBEAT, tps=[20, 20])))


def test_chat_too_long():
    with pytest.raises(ProtocolError, match="256"):
        Envelope.from_json(wire("event.player_chat", {"player": PLAYER, "message": "a" * 257}))


def test_console_rejects_leading_slash():
    with pytest.raises(ProtocolError, match="/"):
        command("cmd.console", ME, command="/op Steve")


def test_reply_needs_reply_to():
    with pytest.raises(ProtocolError, match="reply_to"):
        Envelope.from_json(wire("reply", {"ok": True}))


def test_reply_unknown_error_code():
    with pytest.raises(ProtocolError, match="error code"):
        Envelope.from_json(wire("reply", {"ok": False, "error": {"code": "NOPE", "message": "x"}},
                                reply_to="abc"))


def test_frame_size_limit():
    big = {"player": PLAYER, "message": "x" * 270000}
    with pytest.raises(ProtocolError, match="256 KiB"):
        Envelope.from_json(wire("event.player_death", big))


def test_new_message_types():
    Envelope.from_json(wire("event.link_request", {"player": PLAYER, "code": "ABC123"}))
    Envelope.from_json(wire("cmd.diagnostics", {"actor": ME.to_dict()}))
    Envelope.from_json(wire("cmd.link_result", {"player_uuid": "u", "ok": True, "message": "Linked!"}))
    hello = {"plugin_version": "0.2.0", "platform": "paper", "mc_version": "1.21.11",
             "capabilities": ["diagnostics", "link"], "icon": "iVBORw0KGgo=", "motd": "A server"}
    assert Envelope.from_json(wire("hello", hello)).data["icon"] == "iVBORw0KGgo="


def test_reply_can_carry_data():
    cmd = command("cmd.diagnostics", ME)
    back = Envelope.from_json(reply_ok(cmd, "", {"chunks": 10}).to_json())
    assert back.data["data"] == {"chunks": 10}
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("reply", {"ok": True, "data": "nope"}, reply_to="x"))


def test_icon_size_limit():
    hello = {"plugin_version": "x", "platform": "paper", "mc_version": "x", "capabilities": [],
             "icon": "a" * (25 * 1024)}
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("hello", hello))


def test_join_gate_and_cards_messages():
    Envelope.from_json(wire("event.access_request", {"player": PLAYER, "request_id": "r1"}))
    Envelope.from_json(wire("cmd.access_result", {"request_id": "r1", "allowed": True}))
    Envelope.from_json(wire("cmd.access_result", {"request_id": "r1", "allowed": False, "reason": "not_linked",
                                                  "code": "ABC123"}))
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("cmd.access_result", {"request_id": "r1", "allowed": False}))
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("cmd.access_result", {"request_id": "r1", "allowed": False, "reason": "nope"}))
    Envelope.from_json(wire("cmd.player_info", {"actor": ME.to_dict(), "player_name": "czrbyn"}))
    Envelope.from_json(wire("cmd.advancements", {"actor": ME.to_dict(), "player_name": "czrbyn"}))
    Envelope.from_json(wire("cmd.set_features", {"console_stream": False, "join_requirement": "role"}))
    with pytest.raises(ProtocolError):
        Envelope.from_json(wire("cmd.set_features", {"console_stream": False, "join_requirement": "maybe"}))
