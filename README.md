# MCBridge

Connect your **Minecraft server** to **Discord** with a plugin and a bot that actually talk to each other.

Status bots can only *ping* your server. MCBridge runs inside it, so it knows what's really going on:

- 📊 **Live status card** with real **TPS, MSPT, RAM**, players, the server icon and a graph of the last hour
- 💥 **Crash vs restart detection**, lag alerts with role pings, and "back online" notices
- 🔍 **Lag diagnostics**: the busiest chunks (with coordinates) and most common entities, attached to lag alerts and on `/lag`
- 💬 **Two-way chat bridge** with each player's name and skin head, plus a join/leave/death/advancement feed
- 📝 **Whitelist requests** with Approve/Deny buttons and DMs to the player
- 🏆 **Player stats**: `/player` (playtime, sessions, deaths, last seen) and a `/top` leaderboard
- 🗓️ **Daily recap** with peak players, uptime, average TPS, lag minutes and a 24-hour graph
- 🔗 **Account linking** (`/account link` + `/discord link <code>` in-game) with an automatic role
- ⚙️ **Setup wizard**: `/settings` picks every channel and role with menus
- 🖥️ **Remote console** for admins (off by default in the plugin, fully audited)

> 🚧 **Early development.**

## How it works

```
 Minecraft server                                 MCBridge (hosted)                 Discord
┌──────────────────┐  WebSocket (JSON, token)  ┌────────────────────────┐        ┌──────────┐
│  MCBridge plugin │ ── events, heartbeats ──► │ gateway  ◄──►  bot     │ ◄────► │ servers  │
│  (Paper, Java)   │ ◄──── commands ────────── │ (one Python process)   │        └──────────┘
└──────────────────┘                           └────────────────────────┘
```

Server owners don't host anything. They add the bot, run `/setup`, and type the code into Minecraft
with `/mcbridge link <code>`. The plugin connects **out**, so the Minecraft server needs no open ports.
Every message follows one documented contract: **[docs/PROTOCOL.md](docs/PROTOCOL.md)**.

## Repository layout

| Folder    | What's in it |
|-----------|--------------|
| `docs/`   | The protocol specification (the source of truth for both halves) |
| `bot/`    | The Discord bot and WebSocket gateway (Python 3.10+, discord.py, aiohttp) |
| `plugin/` | The Paper plugin (Java 21, Maven). Built for Paper 1.21.x |

## Running the bot

1. **Discord Developer Portal** → your app → **Bot**: reset the token, and turn on **Message Content Intent** (for chat).
2. Invite it: **OAuth2 → URL Generator**, scopes `bot` + `applications.commands`, permissions
   View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions, Manage Webhooks and Manage Roles (permission number `805424192`).
3. Then:

```bash
cd bot
python -m venv venv
venv\Scripts\activate        # Windows  (Linux/macOS: source venv/bin/activate)
pip install -e ".[dev]"
copy .env.example .env       # Linux/macOS: cp .env.example .env   - then paste your token into .env
pytest
python -m mcbridge_bot run
```

`.env` holds your bot token and is in `.gitignore`. **Never commit it.**

## Building the plugin

```bash
cd plugin
mvn package
```

The jar ends up in `plugin/target/MCBridge-0.1.0.jar`.

## Discord commands

| Command | Who | What |
|---------|-----|------|
| `/setup name` | Manage Server | Get a link code for a new Minecraft server |
| `/settings` | Manage Server | Channels, roles, daily recap, server address, live status |
| `/status [live]` | everyone (`live` needs Manage Server) | Stats card with a graph of the last hour |
| `/player name` | everyone | Playtime, sessions, deaths, last seen |
| `/top` | everyone | Most active players |
| `/whitelist-request player` | everyone | Ask staff to whitelist you |
| `/account link` / `/account unlink` | everyone | Link your Minecraft account |
| `/servers` | everyone | List linked servers |
| `/lag` | Manage Server | What's using the server right now |
| `/recap` | Manage Server | Stats and graph for the last 24 hours |
| `/whitelist add/remove player` | Manage Server | Edit the whitelist |
| `/console cmd` | Administrator | Run a console command (plugin must allow it) |
| `/audit` | Manage Server | Recent actions |
| `/unlink` | Manage Server | Disconnect a server |

## Website

`site/` is the static site for mcbridge.dev (landing page, privacy policy, terms). Deploy it with Cloudflare Pages.

## Roadmap

- [x] Protocol v1
- [x] Gateway: auth, handshake, heartbeats, commands, crash detection
- [x] Multi-server hosting: link codes, per-server tokens
- [x] Paper plugin
- [x] Discord: `/setup`, `/status`, live status, alerts, chat bridge, feed, whitelist, console, audit
- [x] Whitelist requests, webhook chat with heads, stats, recaps, lag diagnostics, account linking, setup wizard
- [x] Public hosting (Cloudflare Tunnel, `wss://`)
- [ ] Fabric version of the plugin
- [ ] Premium tier
- [ ] Web dashboard

## License

[AGPL-3.0](LICENSE): free to use, self-host and modify. If you run a modified version as a public service, you must share your changes.
