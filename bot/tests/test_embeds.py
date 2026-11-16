from mcbridge_bot import embeds
from mcbridge_bot.alerts import AlertTracker

HB = {"tps": [19.98, 19.5, 18.2], "mspt": 12.4,
      "players": [{"uuid": "u1", "name": "czrbyn"}, {"uuid": "u2", "name": "_Steve_"}],
      "max_players": 20, "memory": {"used_mb": 2048, "max_mb": 6144}, "uptime_s": 8231}
HELLO = {"plugin_version": "0.1.0", "platform": "paper", "mc_version": "1.21.11", "capabilities": []}


def fields(e):
    return {f.name: f.value for f in e.fields}


def test_online_status():
    e = embeds.status_embed("SMP", HELLO, HB, online=True)
    f = fields(e)
    assert "Online" in e.description
    assert f["Players · 2/20"] == "czrbyn, \\_Steve\\_"
    assert "20.0" in f["TPS"] and "5m 19.5 · 15m 18.2" in f["TPS"]
    assert f["MSPT"].startswith("**12.4** ms")
    assert "up 2h 17m" in e.description and "Paper 1.21.11" in e.description
    assert "2.0** / 6.0 GB" in f["Memory"]
    assert "plugin 0.1.0" in e.footer.text


def test_offline_status_shows_reason():
    e = embeds.status_embed("SMP", None, None, online=False, offline_reason="crashed")
    assert "crashed" in e.description and e.color.value == embeds.RED


def test_lagging_status_is_yellow():
    e = embeds.status_embed("SMP", HELLO, HB, online=True, lagging=True)
    assert e.color.value == embeds.YELLOW and "Lagging" in e.description


def test_lots_of_players_are_cut_off():
    hb = dict(HB, players=[{"uuid": str(i), "name": f"p{i}"} for i in range(30)], max_players=50)
    assert "and 10 more" in fields(embeds.status_embed("SMP", HELLO, hb, online=True))["Players · 30/50"]


def test_fmt_duration():
    assert embeds.fmt_duration(59) == "0m"
    assert embeds.fmt_duration(3600) == "1h 0m"
    assert embeds.fmt_duration(90061) == "1d 1h"


def test_safe_blocks_mentions_and_markdown():
    out = embeds.safe("@everyone **hi**")
    assert "@everyone" not in out and "**" not in out


def test_feed_embeds():
    p = {"uuid": "u1", "name": "czrbyn"}
    assert "first time" in embeds.feed_embed("event.player_join", {"player": p, "first_join": True}).description
    assert "kicked" in embeds.feed_embed("event.player_leave",
                                         {"player": p, "reason": "kick", "session_s": 60}).description
    assert "fell" in embeds.feed_embed("event.player_death", {"player": p, "message": "czrbyn fell"}).description
    assert "Stone Age" in embeds.feed_embed("event.player_advancement",
                                            {"player": p, "key": "k", "title": "Stone Age"}).description
    assert embeds.feed_embed("event.server_start", {}) is None


def test_alert_embed():
    alert = AlertTracker().lost("s", "crashed")
    e = embeds.alert_embed("SMP", alert)
    assert e.author.name == "SMP" and "crashed" in e.title.lower()


def test_status_card_extras():
    e = embeds.status_embed("SMP", HELLO, HB, online=True, address="play.x.net", has_icon=True, has_chart=True)
    assert "play.x.net" in e.description and e.thumbnail.url == "attachment://icon.png"
    off = embeds.status_embed("SMP", None, None, online=False, offline_reason="crashed", last_seen=100)
    assert "<t:100:R>" in off.description


def test_player_top_recap_request_embeds():
    p = {"uuid": "u", "name": "Steve", "online": False, "last_seen": 10, "first_seen": 1, "playtime_s": 7200,
         "joins": 4, "deaths": 2}
    e = embeds.player_embed("SMP", p, "99")
    assert {f.name for f in e.fields} >= {"Playtime", "Discord"}
    t = embeds.top_embed("SMP", [{"uuid": "u", "name": "Steve", "playtime_s": 7200, "online": 1}])
    assert "🥇" in t.description and "🟢" in t.description
    r = {"online_minutes": 720, "window_minutes": 1440, "peak_players": 5, "unique_players": 3, "new_players": 1,
         "playtime_s": 3600, "avg_tps": 19.5, "lag_minutes": 0, "top": [{"name": "Steve", "playtime_s": 3600}]}
    rc = embeds.recap_embed("SMP", r)
    assert fields(rc)["Uptime"] == "**50.0%**" and "Steve" in fields(rc)["Most active"]
    w = embeds.whitelist_request_embed("SMP", "Steve", "1", status="approved", decided_by="2")
    assert "approved" in w.title
