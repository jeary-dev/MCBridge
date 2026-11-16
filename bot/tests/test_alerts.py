from mcbridge_bot.alerts import AlertTracker


def hb(tps, mspt=50.0):
    return {"tps": [tps, 19.0, 19.0], "mspt": mspt}


def test_first_connect_is_quiet_then_crash_then_back():
    t = AlertTracker()
    assert t.connected("s") is None
    crash = t.lost("s", "crashed")
    assert crash.kind == "crashed" and crash.ping
    assert t.last_lost("s") == "crashed"
    back = t.connected("s")
    assert back.kind == "back_online" and not back.ping
    assert t.last_lost("s") is None


def test_clean_stop_does_not_ping():
    t = AlertTracker()
    t.connected("s")
    assert t.lost("s", "stopped").ping is False


def test_unlink_is_silent():
    t = AlertTracker()
    t.connected("s")
    assert t.lost("s", "unlinked") is None


def test_unknown_reason_falls_back():
    assert AlertTracker().lost("s", "weird").kind == "disconnected"


def test_lag_needs_three_bad_heartbeats_in_a_row():
    t = AlertTracker()
    t.connected("s")
    assert t.heartbeat("s", hb(10)) is None
    assert t.heartbeat("s", hb(10)) is None
    assert t.heartbeat("s", hb(19.9)) is None
    assert t.heartbeat("s", hb(10)) is None
    assert t.heartbeat("s", hb(10)) is None
    lag = t.heartbeat("s", hb(10))
    assert lag.kind == "lagging" and lag.ping and t.is_lagging("s")
    assert t.heartbeat("s", hb(10)) is None


def test_lag_recovers_after_three_good_heartbeats():
    t = AlertTracker()
    for _ in range(3):
        t.heartbeat("s", hb(5))
    assert t.heartbeat("s", hb(19.5)) is None
    assert t.heartbeat("s", hb(16)) is None
    assert t.heartbeat("s", hb(19.5)) is None
    assert t.heartbeat("s", hb(19.5)) is None
    assert t.heartbeat("s", hb(19.5)).kind == "recovered"
    assert not t.is_lagging("s")


def test_servers_are_tracked_separately():
    t = AlertTracker()
    for _ in range(3):
        t.heartbeat("a", hb(5))
    assert t.is_lagging("a") and not t.is_lagging("b")
