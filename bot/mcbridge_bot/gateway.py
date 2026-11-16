"""The WebSocket gateway that mcbridge plugins connect to.

Responsibilities (see docs/PROTOCOL.md):
  * authenticate plugins by token (HTTP 401 if wrong)
  * hello -> welcome handshake
  * keep the latest heartbeat for each server
  * deliver events to listeners (the Discord side subscribes to these later)
  * send commands and wait for the matching reply
  * notice silent servers and decide: crashed, or just the plugin disconnected
  * POST /v1/link: swap a short link code (from /setup in Discord) for a server token
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from aiohttp import WSMsgType, web

from .protocol import Envelope, ProtocolError
from .store import ServerRecord, Store

LINK_ATTEMPTS_PER_MINUTE = 5

log = logging.getLogger("mcbridge.gateway")

HEARTBEAT_INTERVAL_S = 10
MISSED_HEARTBEATS_ALLOWED = 3
HELLO_TIMEOUT_S = 10
COMMAND_TIMEOUT_S = 10
LOST_GRACE_S = 30

Listener = Callable[["Session", str, dict], Awaitable[None]]
PingCheck = Callable[[str], Awaitable[bool]]


class CommandFailed(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code, self.message = code, message


@dataclass
class Session:
    record: ServerRecord
    ws: web.WebSocketResponse
    hello: dict
    connected_at: float = field(default_factory=time.monotonic)
    last_seen: float = field(default_factory=time.monotonic)
    heartbeat: dict | None = None
    clean_stop: bool = False
    unlinked: bool = False
    pending: dict[str, asyncio.Future] = field(default_factory=dict)

    @property
    def server_id(self) -> str:
        return self.record.server_id

    @property
    def capabilities(self) -> set[str]:
        return set(self.hello.get("capabilities", []))

    async def send(self, env: Envelope) -> None:
        await self.ws.send_str(env.to_json())

    async def command(self, env: Envelope, timeout: float = COMMAND_TIMEOUT_S) -> dict:
        fut = asyncio.get_running_loop().create_future()
        self.pending[env.id] = fut
        try:
            await self.send(env)
            reply: Envelope = await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            raise CommandFailed("TIMEOUT", f"no reply within {timeout}s") from None
        finally:
            self.pending.pop(env.id, None)
        if not reply.data["ok"]:
            err = reply.data["error"]
            raise CommandFailed(err["code"], err["message"])
        return reply.data


class Gateway:
    def __init__(self, store: Store, ping_check: PingCheck | None = None,
                 heartbeat_interval_s: int = HEARTBEAT_INTERVAL_S, silence_timeout_s: float | None = None,
                 trust_cloudflare: bool = False, lost_grace_s: float = LOST_GRACE_S):
        self.store = store
        self.health_check: Callable[[], str | None] | None = None
        self.lost_grace_s = lost_grace_s
        self._pending_lost: dict[str, asyncio.Task] = {}
        self.trust_cloudflare = trust_cloudflare
        self._link_attempts: dict[str, deque[float]] = defaultdict(deque)
        self.ping_check = ping_check
        self.heartbeat_interval_s = heartbeat_interval_s
        self.silence_timeout_s = silence_timeout_s or heartbeat_interval_s * MISSED_HEARTBEATS_ALLOWED
        self.sessions: dict[str, Session] = {}
        self._listeners: list[Listener] = []
        self._watchdog: asyncio.Task | None = None

    def on(self, listener: Listener) -> Listener:
        self._listeners.append(listener)
        return listener

    def make_app(self) -> web.Application:
        app = web.Application(client_max_size=4096)
        app.router.add_get("/v1/plugin", self._handle)
        app.router.add_post("/v1/link", self._handle_link)
        app.router.add_get("/health", self._handle_health)
        app.on_startup.append(self._start_watchdog)
        app.on_cleanup.append(self._stop_watchdog)
        return app

    async def _emit(self, session: Session, what: str, details: dict | None = None) -> None:
        for listener in self._listeners:
            try:
                await listener(session, what, details or {})
            except Exception:
                log.exception("listener failed on %s", what)

    def client_ip(self, request: web.Request) -> str:
        if self.trust_cloudflare and request.headers.get("CF-Connecting-IP"):
            return request.headers["CF-Connecting-IP"]
        return request.remote or "?"

    async def _handle_health(self, request: web.Request) -> web.Response:
        problem = self.health_check() if self.health_check else None
        if problem:
            return web.Response(status=503, text=f"unhealthy: {problem}")
        return web.Response(text="ok")

    async def _handle_link(self, request: web.Request) -> web.Response:
        ip = self.client_ip(request)
        now = time.monotonic()
        attempts = self._link_attempts[ip]
        while attempts and now - attempts[0] > 60:
            attempts.popleft()
        if len(attempts) >= LINK_ATTEMPTS_PER_MINUTE:
            return web.json_response({"error": "too many attempts, wait a minute"}, status=429)
        attempts.append(now)

        try:
            body = await request.json()
            code = body["code"]
            if not isinstance(code, str) or len(code) > 20:
                raise ValueError
        except Exception:
            return web.json_response({"error": "send JSON like {\"code\": \"K7P-2QX\"}"}, status=400)

        result = self.store.redeem_link_code(code)
        if result is None:
            return web.json_response({"error": "that code is wrong, used or expired - run /setup again"}, status=404)
        record, token = result
        log.info("linked %s (%s) to guild %s", record.name, record.server_id, record.guild_id)
        return web.json_response({"server_id": record.server_id, "name": record.name, "token": token})

    async def _handle(self, request: web.Request) -> web.StreamResponse:
        auth = request.headers.get("Authorization", "")
        record = self.store.authenticate(auth.removeprefix("Bearer ").strip()) if auth.startswith("Bearer ") else None
        if record is None:
            log.warning("rejected connection from %s: bad token", self.client_ip(request))
            return web.Response(status=401, text="invalid token")

        ws = web.WebSocketResponse(max_msg_size=64 * 1024, heartbeat=30)
        await ws.prepare(request)

        try:
            msg = await ws.receive(timeout=HELLO_TIMEOUT_S)
            hello = Envelope.from_json(msg.data) if msg.type == WSMsgType.TEXT else None
        except (asyncio.TimeoutError, ProtocolError):
            hello = None
        if hello is None or hello.type != "hello":
            await ws.close(code=1008, message=b"expected hello")
            return ws

        session = Session(record=record, ws=ws, hello=hello.data)
        pending = self._pending_lost.pop(record.server_id, None)
        if pending is not None:
            pending.cancel()
            log.info("%s came back within the grace period", record.server_id)
        old = self.sessions.get(record.server_id)
        self.sessions[record.server_id] = session
        if old is not None:
            await old.ws.close(code=1000, message=b"replaced by new connection")
        await session.send(Envelope(type="welcome", data={
            "server_id": record.server_id,
            "heartbeat_interval_s": self.heartbeat_interval_s,
            "features": {"chat_bridge": True, "whitelist": True, "console": "console" in session.capabilities},
        }))
        log.info("%s (%s) connected: %s", record.name, record.server_id, hello.data)
        await self._emit(session, "connected", hello.data)

        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    env = Envelope.from_json(msg.data)
                except ProtocolError as e:
                    log.warning("%s sent a bad message: %s", record.server_id, e)
                    continue
                session.last_seen = time.monotonic()
                await self._dispatch(session, env)
        finally:
            if self.sessions.get(record.server_id) is session:
                del self.sessions[record.server_id]
                for fut in session.pending.values():
                    if not fut.done():
                        fut.set_exception(CommandFailed("DISCONNECTED", "plugin disconnected"))
                if session.unlinked or session.clean_stop or self.lost_grace_s <= 0:
                    await self._on_lost(session)
                else:
                    self._pending_lost[record.server_id] = asyncio.create_task(self._lost_after_grace(session))
        return ws

    async def _lost_after_grace(self, session: Session) -> None:
        await asyncio.sleep(self.lost_grace_s)
        if self._pending_lost.get(session.server_id) is asyncio.current_task():
            del self._pending_lost[session.server_id]
        if session.server_id not in self.sessions:
            await self._on_lost(session)

    async def _dispatch(self, session: Session, env: Envelope) -> None:
        if not env.known:
            log.debug("ignoring unknown message type %s", env.type)
        elif env.type == "heartbeat":
            session.heartbeat = env.data
            await self._emit(session, "heartbeat", env.data)
        elif env.type == "reply":
            fut = session.pending.get(env.reply_to or "")
            if fut and not fut.done():
                fut.set_result(env)
        elif env.type == "event.server_stop":
            session.clean_stop = True
            await self._emit(session, env.type, env.data)
        elif env.type.startswith("event."):
            await self._emit(session, env.type, env.data)

    def disconnect_server(self, server_id: str) -> None:
        session = self.sessions.get(server_id)
        if session is not None:
            session.unlinked = True
            asyncio.ensure_future(session.ws.close(code=4001, message=b"unlinked"))

    async def _on_lost(self, session: Session) -> None:
        record = self.store.get_server(session.server_id) or session.record
        if session.unlinked:
            reason = "unlinked"
        elif session.clean_stop:
            reason = "stopped"
        elif self.ping_check and record.address:
            still_up = await self.ping_check(record.address)
            reason = "plugin_disconnected" if still_up else "crashed"
        else:
            reason = "disconnected"
        log.info("%s lost: %s", session.server_id, reason)
        await self._emit(session, "lost", {"reason": reason})

    async def _watchdog_loop(self) -> None:
        while True:
            await asyncio.sleep(self.silence_timeout_s / 6)
            now = time.monotonic()
            for session in list(self.sessions.values()):
                if now - session.last_seen > self.silence_timeout_s:
                    log.warning("%s silent for %.0fs, dropping it", session.server_id, self.silence_timeout_s)
                    await session.ws.close(code=1001, message=b"heartbeat timeout")

    async def _start_watchdog(self, app: web.Application) -> None:
        self._watchdog = asyncio.create_task(self._watchdog_loop())

    async def _stop_watchdog(self, app: web.Application) -> None:
        if self._watchdog:
            self._watchdog.cancel()
        for task in self._pending_lost.values():
            task.cancel()
        self._pending_lost.clear()
