# mcbridge protocol — v1

The contract between the **plugin** (runs inside a Minecraft server) and the **bot** (runs the Discord side).
Both halves are written against this document. If code and this document disagree, this document wins.

## 1. Transport

- **WebSocket**, plugin connects **out** to the bot. Production uses `wss://` (TLS).
- Endpoint: `/v1/plugin`
- Authentication happens in the WebSocket handshake:
  `Authorization: Bearer <server-token>`
  The bot rejects the upgrade (HTTP 401) if the token is unknown. Tokens are 32+ random bytes, one per Minecraft server.
- Every frame is a UTF-8 **text** frame containing one JSON object (an *envelope*). Max size **64 KiB**.

### Linking (getting a token)
Server owners never copy tokens by hand. Instead:

1. In Discord, `/setup` creates a **link code** like `K7P-2QX`: 6 characters, single-use, valid **10 minutes**, stored hashed.
2. In-game, `/mcbridge link K7P-2QX` makes the plugin call:

```
POST /v1/link            (same host as the WebSocket; ws:// -> http://, wss:// -> https://)
Content-Type: application/json

{"code": "K7P-2QX"}
```

| Status | Body | Meaning |
|--------|------|---------|
| 200 | `{"server_id": "srv_...", "name": "Steve's SMP", "token": "..."}` | Linked. The plugin saves `token` to its config and connects. |
| 400 | `{"error": "..."}` | Malformed request. |
| 404 | `{"error": "..."}` | Code wrong, already used, or expired. |
| 429 | `{"error": "..."}` | More than 5 attempts per minute from this IP. |

Codes are case-insensitive, and `-` or spaces are ignored. The token is only ever sent in this one response.

### Live demo
`GET /v1/demo` returns public JSON for the one server set as `DEMO_SERVER_ID` (status, players, TPS, the last hour of samples and the last 30 chat/feed events), for the live demo on mcbridge.dev. CORS allows the origins in `DEMO_ORIGINS`. 404 if no demo server is configured.

### Health check
`GET /health` answers `200 ok` when the gateway is running and the Discord bot is connected, or `503 unhealthy: <reason>` otherwise. Point an uptime monitor at it.

## 2. Envelope

Every message has the same outer shape:

```json
{
  "v": 1,
  "type": "event.player_join",
  "id": "8f2c6a4e-...",
  "ts": 1794303836123,
  "reply_to": null,
  "data": { }
}
```

| Field      | Type            | Meaning |
|------------|-----------------|---------|
| `v`        | int             | Protocol version. Always `1` for this spec. |
| `type`     | string          | What kind of message (see below). |
| `id`       | string (UUID)   | Unique per message. Used to match replies. |
| `ts`       | int             | Sender's time, Unix epoch **milliseconds**. |
| `reply_to` | string or null  | Set only on `reply` messages: the `id` being answered. |
| `data`     | object          | Type-specific payload. Always an object, never null. |

### Compatibility rules
1. Receivers **ignore unknown `type`s** and **unknown fields** (log at debug level). This lets either side be upgraded first.
2. Within v1, fields may be **added** but never removed, renamed or changed in meaning.
3. Anything that breaks rule 2 becomes protocol **v2** on a new endpoint (`/v2/plugin`).

## 3. Common objects

**Player**
```json
{ "uuid": "f759806f-e772-4945-8b79-c19266849be4", "name": "czrbyn" }
```

**Actor** (a Discord user who caused a command)
```json
{ "discord_id": "123456789012345678", "name": "corbyn" }
```

## 4. Connection lifecycle

```
plugin                                  bot
  | --- WebSocket upgrade + token ------> |   (401 if bad token)
  | --- hello --------------------------> |
  | <-- welcome ------------------------- |
  | --- heartbeat (every N s) ----------> |
  | --- event.* ------------------------> |
  | <-- cmd.* --------------------------- |
  | --- reply --------------------------> |
```

### `hello` (plugin → bot, first message)
```json
{
  "plugin_version": "0.1.0",
  "platform": "paper",
  "mc_version": "1.21.11",
  "capabilities": ["chat", "whitelist", "console"]
}
```
`capabilities` = what this plugin **allows** according to its own config. Console is **off by default** in the plugin config.
Plugins that support them also advertise `diagnostics` and `link` (see below).

Optional fields (added in plugin 0.2.0):
- `motd`: the server's MOTD as plain text.
- `icon`: the server's `server-icon.png`, base64-encoded (max 24 KiB of base64). Shown on status cards.

### `welcome` (bot → plugin)
```json
{
  "server_id": "srv_7Q2xK9",
  "heartbeat_interval_s": 10,
  "features": { "chat_bridge": true, "console": false, "whitelist": true }
}
```
`features` = what the bot will actually use for this server (config + premium). The plugin should only send event types for enabled features (e.g. skip chat events if `chat_bridge` is false).

### `heartbeat` (plugin → bot, every `heartbeat_interval_s`)
```json
{
  "tps": [19.98, 19.95, 19.90],
  "mspt": 12.4,
  "players": [{ "uuid": "...", "name": "czrbyn" }],
  "max_players": 20,
  "memory": { "used_mb": 2140, "max_mb": 6144 },
  "uptime_s": 8231
}
```
`tps` = 1, 5 and 15 minute averages. The bot treats the plugin as **gone** after **3 missed heartbeats**, then uses a status ping to decide between *crashed* and *plugin disconnected*.

### Reconnecting
If the connection drops, the plugin reconnects with exponential backoff: 1s, 2s, 4s… up to 60s, plus random jitter of 0–1s. It sends `hello` again each time.
The bot waits **30 seconds** after a connection drops before treating the server as gone, so a quick reconnect (network blip, proxy recycling the connection) causes no alerts. A clean stop (`event.server_stop`) is reported immediately.

## 5. Events (plugin → bot)

No reply is expected.

| `type`                     | `data` |
|----------------------------|--------|
| `event.server_start`       | `{ "motd": str, "max_players": int }` |
| `event.server_stop`        | `{ "reason": "shutdown" \| "restart" }` (sent during a clean stop; no stop event + lost heartbeats = crash) |
| `event.player_join`        | `{ "player": Player, "first_join": bool }` |
| `event.player_leave`       | `{ "player": Player, "reason": "quit" \| "kick" \| "ban", "session_s": int }` |
| `event.player_chat`        | `{ "player": Player, "message": str }` (max 256 chars) |
| `event.player_death`       | `{ "player": Player, "message": str }` (plain-text death message) |
| `event.player_advancement` | `{ "player": Player, "key": str, "title": str }` |
| `event.console`            | `{ "lines": [str] }` (max 200 lines). Only sent after `cmd.set_features` turns the stream on. |
| `event.player_groups`      | `{ "player": Player, "groups": [str], "reason": "join" \| "change" }`. Sent on join and when groups change (LuckPerms). |
| `event.link_request`       | `{ "player": Player, "code": str }` (max 12 chars). A player typed `/discord link <code>`; the bot answers with `cmd.link_result`. |

## 6. Commands (bot → plugin)

Every command **must** get exactly one `reply`. The bot gives up waiting after 10 seconds.

| `type`          | `data` | Needs capability |
|-----------------|--------|------------------|
| `cmd.chat_send` | `{ "actor": Actor, "message": str }` (max 256 chars) | `chat` |
| `cmd.whitelist` | `{ "actor": Actor, "action": "add" \| "remove", "player_name": str }` | `whitelist` |
| `cmd.console`   | `{ "actor": Actor, "command": str }` (max 1000 chars, no leading `/`) | `console` |
| `cmd.diagnostics` | `{ "actor": Actor }`. Reply `data` is described below. | `diagnostics` |
| `cmd.moderate` | `{ "actor": Actor, "action": "kick" \| "ban" \| "unban" \| "op" \| "deop" \| "gamemode", "player_name": str, "reason"?: str, "gamemode"?: str }` | `moderation` |
| `cmd.tab_complete` | `{ "actor": Actor, "command": str }`. Reply data: `{ "suggestions": [str] }` | `console` |
| `cmd.player_stats` | `{ "actor": Actor, "player_name": str }`. Reply data: name, uuid, online, stats, advancements | `stats` |
| `cmd.inventory` | `{ "actor": Actor, "player_name": str }`. Reply data: armor, offhand, hotbar, main (online players only) | `inventory` |
| `cmd.message` | `{ "actor": Actor, "player_name": str, "message": str }` | `message` |
| `cmd.set_features` | `{ "console_stream": bool }` | `console_stream` |
| `cmd.set_groups` | `{ "player_uuid": str, "add": [str], "remove": [str] }` | `roles` |
| `cmd.link_result` | `{ "player_uuid": str, "ok": bool, "message": str }` (max 256 chars). Tell a player how linking went. | `link` |

The **plugin enforces its own capabilities** even if the bot asks: a `cmd.console` to a plugin that didn't advertise `console` is rejected with `FORBIDDEN`. Both sides check permissions independently.

### `reply` (plugin → bot)
```json
{ "type": "reply", "reply_to": "<command id>",
  "data": { "ok": true, "result": "Added czrbyn to the whitelist" } }
```
A successful reply may carry structured data in an optional `data` object. `cmd.diagnostics` uses it:
```json
{ "ok": true, "result": "", "data": {
    "worlds": [{ "name": "world", "chunks": 1840, "entities": 4210, "tile_entities": 960, "players": 2 }],
    "top_chunks": [{ "world": "world", "x": 12, "z": -30, "entities": 1150, "tile_entities": 4 }],
    "top_entities": [{ "type": "CHICKEN", "count": 1210 }] } }
```
`x` and `z` are chunk coordinates (multiply by 16 for block coordinates).

On failure:
```json
{ "data": { "ok": false, "error": { "code": "FORBIDDEN", "message": "Console is disabled in config.yml" } } }
```

| Error code         | Meaning |
|--------------------|---------|
| `UNKNOWN_COMMAND`  | Plugin doesn't know this `cmd.*` type (older version). |
| `FORBIDDEN`        | Capability disabled in the plugin config. |
| `INVALID`          | Bad or missing fields. |
| `PLAYER_NOT_FOUND` | Named player doesn't exist (e.g. whitelist). |
| `INTERNAL`         | Something broke inside the plugin. |

## 7. Security notes

- One token per Minecraft server; the token decides `server_id`. The plugin never claims which Discord it belongs to.
- Tokens are stored **hashed** in the bot's database.
- Console commands are logged by the bot (who, what, when, result) before being sent.
- Text from Discord shown in-game is sent as **plain text**; the plugin must not interpret formatting codes from it.
