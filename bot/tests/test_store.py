import time

import pytest

from mcbridge_bot import store as store_module
from mcbridge_bot.store import Store, normalize_code


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


def test_tokens_are_hashed_and_authenticate(store):
    rec, token = store.create_server("g1", "SMP")
    assert token not in rec.token_hash
    assert store.authenticate(token) == rec
    assert store.authenticate("wrong") is None


def test_servers_belong_to_their_guild(store):
    a, _ = store.create_server("guild-A", "A's server")
    b, _ = store.create_server("guild-B", "B's server")
    assert store.servers_for_guild("guild-A") == [a]
    assert store.servers_for_guild("guild-B") == [b]


def test_link_code_format_and_redeem(store):
    code = store.create_link_code("g1", "My SMP", created_by="user1")
    assert len(code) == 7 and code[3] == "-"
    rec, token = store.redeem_link_code(code)
    assert rec.guild_id == "g1" and rec.name == "My SMP"
    assert store.authenticate(token) == rec


@pytest.mark.parametrize("variant", [str.lower, lambda c: c.replace("-", ""), lambda c: c.replace("-", " ")])
def test_link_code_is_forgiving_about_typing(store, variant):
    code = store.create_link_code("g1", "SMP", created_by="u")
    assert store.redeem_link_code(variant(code)) is not None


def test_link_code_works_only_once(store):
    code = store.create_link_code("g1", "SMP", created_by="u")
    assert store.redeem_link_code(code) is not None
    assert store.redeem_link_code(code) is None


def test_link_code_expires(store, monkeypatch):
    code = store.create_link_code("g1", "SMP", created_by="u")
    real_time = time.time
    monkeypatch.setattr(store_module.time, "time", lambda: real_time() + store_module.LINK_CODE_TTL_S + 1)
    assert store.redeem_link_code(code) is None


def test_wrong_code(store):
    assert store.redeem_link_code("AAA-AAA") is None


def test_normalize_code():
    assert normalize_code(" k7p-2qx ") == "K7P2QX"


def test_delete_server_kills_token_and_channels(store):
    rec, token = store.create_server("g1", "SMP")
    store.set_channel(rec.server_id, "alerts", "999")
    store.delete_server(rec.server_id)
    assert store.authenticate(token) is None
    assert store.get_channel(rec.server_id, "alerts") is None


def test_channels(store):
    rec, _ = store.create_server("g1", "SMP")
    store.set_channel(rec.server_id, "status", "111")
    assert store.get_channel(rec.server_id, "status") == "111"
    store.set_channel(rec.server_id, "status", "222")
    assert store.get_channel(rec.server_id, "status") == "222"
    store.set_channel(rec.server_id, "status", None)
    assert store.get_channel(rec.server_id, "status") is None


def test_audit_log_is_per_guild(store):
    store.audit("g1", None, "1", "corbyn", "console", "say hi", "ok")
    store.audit("g2", None, "2", "other", "console", "op x", "FORBIDDEN")
    entries = store.recent_audit("g1")
    assert len(entries) == 1 and entries[0]["actor_name"] == "corbyn"


def test_link_code_sets_alert_channel(store):
    code = store.create_link_code("g1", "SMP", created_by="u", channel_id="555")
    rec, _ = store.redeem_link_code(code)
    assert store.get_channel(rec.server_id, "alerts") == "555"


def test_servers_for_channel(store):
    a, _ = store.create_server("g1", "A")
    b, _ = store.create_server("g1", "B")
    store.set_channel(a.server_id, "chat", "777")
    store.set_channel(b.server_id, "feed", "777")
    assert store.servers_for_channel("777", "chat") == [a]


def test_settings(store):
    rec, _ = store.create_server("g1", "SMP")
    store.set_setting(rec.server_id, "status_message", "1:2")
    assert store.get_setting(rec.server_id, "status_message") == "1:2"
    assert store.servers_with_setting("status_message") == [(rec, "1:2")]
    store.set_setting(rec.server_id, "status_message", None)
    assert store.get_setting(rec.server_id, "status_message") is None


def test_delete_guild(store):
    a, token = store.create_server("g1", "A")
    store.create_server("g2", "B")
    store.set_setting(a.server_id, "alert_role", "1")
    assert store.delete_guild("g1") == [a.server_id]
    assert store.authenticate(token) is None and store.get_setting(a.server_id, "alert_role") is None
    assert len(store.servers_for_guild("g2")) == 1


HB = {"tps": [19.5, 19, 19], "mspt": 20.0, "players": [{"uuid": "u1", "name": "A"}], "max_players": 20,
      "memory": {"used_mb": 1000, "max_mb": 4000}, "uptime_s": 1}


def test_samples_and_prune(store):
    rec, _ = store.create_server("g1", "SMP")
    store.add_sample(rec.server_id, 60, HB)
    store.add_sample(rec.server_id, 120, HB)
    assert [s["ts"] for s in store.samples(rec.server_id, 0)] == [60, 120]
    store.prune(100)
    assert [s["ts"] for s in store.samples(rec.server_id, 0)] == [120]


def test_playtime_tracking(store):
    rec, _ = store.create_server("g1", "SMP")
    sid = rec.server_id
    store.player_joined(sid, "u1", "Steve", 1000)
    store.player_left(sid, "u1", 1600)
    store.player_joined(sid, "u1", "Steve", 2000)
    p = store.player(sid, "steve", now=2100)
    assert p["online"] and p["playtime_s"] == 700 and p["joins"] == 2
    store.player_died(sid, "u1")
    store.close_all_sessions(sid, 2300)
    p = store.player(sid, "u1", now=9999)
    assert not p["online"] and p["playtime_s"] == 900 and p["deaths"] == 1
    assert store.player(sid, "nobody") is None


def test_sync_online_opens_and_closes(store):
    rec, _ = store.create_server("g1", "SMP")
    sid = rec.server_id
    store.player_joined(sid, "gone", "Gone", 0)
    store.sync_online(sid, [{"uuid": "u1", "name": "A"}], 100)
    assert store.player(sid, "Gone")["online"] is False
    assert store.player(sid, "A", now=150)["online"] is True


def test_top_and_recap(store):
    rec, _ = store.create_server("g1", "SMP")
    sid = rec.server_id
    store.player_joined(sid, "a", "Alice", 0)
    store.player_left(sid, "a", 3600)
    store.player_joined(sid, "b", "Bob", 1800)
    for ts in range(0, 3600, 60):
        store.add_sample(sid, ts, dict(HB, tps=[12 if ts < 600 else 20, 20, 20]))
    top = store.top_players(sid, now=6000)
    assert [t["name"] for t in top] == ["Bob", "Alice"]
    r = store.recap(sid, 0, 3600)
    assert r["unique_players"] == 2 and r["new_players"] == 2
    assert r["playtime_s"] == 3600 + 1800 and r["top"][0]["name"] == "Alice"
    assert r["lag_minutes"] == 10 and r["online_minutes"] == 60 and r["peak_players"] == 1


def test_account_links(store):
    code = store.create_account_code("g1", "discord-1")
    assert store.redeem_account_code("g2", code, "uuid-1", "Steve") is None
    assert store.redeem_account_code("g1", code.lower(), "uuid-1", "Steve") == "discord-1"
    assert store.redeem_account_code("g1", code, "uuid-1", "Steve") is None
    assert store.linked_account("g1", "discord-1")["name"] == "Steve"
    assert store.linked_discord("g1", "uuid-1") == "discord-1"
    code = store.create_account_code("g1", "discord-2")
    store.redeem_account_code("g1", code, "uuid-1", "Steve")
    assert store.linked_account("g1", "discord-1") is None
    assert store.unlink_account("g1", "discord-2") and not store.unlink_account("g1", "discord-2")


def test_whitelist_requests(store):
    rec, _ = store.create_server("g1", "SMP")
    rid = store.create_whitelist_request(rec.server_id, "d1", "Steve")
    assert store.pending_whitelist_request(rec.server_id, "d1")["id"] == rid
    assert store.decide_whitelist_request(rid, "approved", "mod")
    assert not store.decide_whitelist_request(rid, "denied", "mod2")
    assert store.whitelist_request(rid)["status"] == "approved"
    assert store.pending_whitelist_request(rec.server_id, "d1") is None
