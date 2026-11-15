"""Decides WHEN to alert. No Discord code in here, so it's easy to test.

Feed it what the gateway sees (connected / heartbeat / lost) and it returns an Alert,
or None when nothing is worth telling people about.
"""
from __future__ import annotations

from dataclasses import dataclass, field

LAG_TPS = 15.0
RECOVER_TPS = 18.0
STRIKES = 3

RED, ORANGE, YELLOW, GREEN, GREY = 0xE5484D, 0xF76B15, 0xF5D90A, 0x30A46C, 0x8B8D98


@dataclass(frozen=True)
class Alert:
    kind: str
    title: str
    description: str
    color: int
    ping: bool


LOST_ALERTS = {
    "crashed": ("💥 Server crashed", "It stopped answering and didn't shut down cleanly.", RED, True),
    "plugin_disconnected": ("🔌 Plugin disconnected",
                            "The server still answers pings, but the MCBridge plugin lost its connection. "
                            "Try `/mcbridge reload` in-game.", ORANGE, True),
    "disconnected": ("🔴 Server went offline", "The connection was lost without a clean shutdown.", RED, True),
    "stopped": ("⏹️ Server stopped", "It was shut down cleanly.", GREY, False),
}


@dataclass
class _Health:
    online: bool = False
    last_lost: str | None = None
    lagging: bool = False
    low: int = 0
    good: int = 0


@dataclass
class AlertTracker:
    lag_tps: float = LAG_TPS
    recover_tps: float = RECOVER_TPS
    strikes: int = STRIKES
    _servers: dict[str, _Health] = field(default_factory=dict)

    def _h(self, server_id: str) -> _Health:
        return self._servers.setdefault(server_id, _Health())

    def last_lost(self, server_id: str) -> str | None:
        return self._h(server_id).last_lost

    def is_lagging(self, server_id: str) -> bool:
        return self._h(server_id).lagging

    def connected(self, server_id: str) -> Alert | None:
        h = self._h(server_id)
        was_down = h.last_lost is not None
        h.online, h.last_lost, h.lagging, h.low, h.good = True, None, False, 0, 0
        if was_down:
            return Alert("back_online", "🟢 Server is back online", "MCBridge reconnected.", GREEN, False)
        return None

    def lost(self, server_id: str, reason: str) -> Alert | None:
        h = self._h(server_id)
        h.online, h.lagging, h.low, h.good = False, False, 0, 0
        if reason == "unlinked":
            self._servers.pop(server_id, None)
            return None
        h.last_lost = reason
        title, desc, color, ping = LOST_ALERTS.get(reason, LOST_ALERTS["disconnected"])
        return Alert(reason if reason in LOST_ALERTS else "disconnected", title, desc, color, ping)

    def heartbeat(self, server_id: str, hb: dict) -> Alert | None:
        h = self._h(server_id)
        tps = float(hb["tps"][0])
        if not h.lagging:
            h.low = h.low + 1 if tps < self.lag_tps else 0
            if h.low >= self.strikes:
                h.lagging, h.low, h.good = True, 0, 0
                return Alert("lagging", "🐢 Server is lagging",
                             f"TPS has been below {self.lag_tps:g} for {self.strikes} checks in a row "
                             f"(now **{tps:.1f}**, MSPT {hb['mspt']:.1f}).", YELLOW, True)
        else:
            h.good = h.good + 1 if tps >= self.recover_tps else 0
            if h.good >= self.strikes:
                h.lagging, h.good, h.low = False, 0, 0
                return Alert("recovered", "✅ Lag is over", f"TPS is back to **{tps:.1f}**.", GREEN, False)
        return None

    def forget(self, server_id: str) -> None:
        self._servers.pop(server_id, None)