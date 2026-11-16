# MCBridge command reference

The source of truth for every command, setting and in-game command. The website's guide is built from
this file, so keep it up to date when commands change.

Staff commands are hidden from members by default. Server admins can change who can use any command in
**Server Settings → Integrations → MCBridge**.

## Discord commands

### Everyone

| Command | Options | What it does | Needs |
|---|---|---|---|
| `/help` | | Lists every command. | |
| `/status` | `server`, `live` | Live TPS, MSPT, memory, players, server icon and a graph of the last hour. `live:True` posts a message that updates itself every minute (needs Manage Server). | A linked server |
| `/servers` | | Lists the Minecraft servers linked to this Discord, with players and TPS. | |
| `/player` | `name`, `server` | An image card with the player's skin, health, hunger, XP level, world, game mode, ping, playtime, sessions, deaths, first joined and last seen. Staff get **Kick**, **Ban/Unban** and **Op/Deop** buttons under it. | Health and the rest need the server online and plugin 0.4.0+ (they also work for offline players). Buttons need Manage Server and `allow.moderation` |
| `/stats` | `name`, `server` | Minecraft's own statistics: play time, mob and player kills, deaths, distance travelled, damage, fish caught and more. Blocks mined and advancements are shown while the player is online. | Server online, plugin 0.3.0+ |
| `/advancements` | `name`, `server` | An image card with progress for each advancement tab and the most recently completed advancements. Works for offline players. | Server online, plugin 0.4.0+ |
| `/inventory` | `player`, `server` | An image of the player's inventory: armour, offhand, hotbar, backpack, item counts, enchantments and durability, plus what's in their hand. A menu under it opens any **shulker box** they carry and their **ender chest**. Works for offline players. | Server online, plugin 0.3.0+ (offline players, shulkers and ender chest need 0.4.0+) |
| `/top` | `server` | The 10 most active players by playtime. | |
| `/whitelist-request` | `player`, `server` | Ask the staff to whitelist your Minecraft account. Staff get Approve/Deny buttons and you get a DM with the answer. One pending request at a time, 30s cooldown. | A requests or alerts channel |
| `/account link` | `code` | Without a code: gives you a code to type in-game with `/discord link <code>`. With a code: links the Minecraft account that was just stopped by a join requirement (the code is in the kick message). Codes expire after 10 minutes. | |
| `/account unlink` | | Unlinks your Minecraft account and removes linked roles. | |

### Staff (Manage Server)

| Command | Options | What it does | Needs |
|---|---|---|---|
| `/setup` | `name` | Makes a one-time link code (10 minutes) for a new Minecraft server. | |
| `/settings` | `server` | The setup wizard: channels (alerts, chat, feed, whitelist requests, console, stat channel), roles, daily recap, server address, live status, feed filters, join requirements, embed colour and footer. | A linked server |
| `/lag` | `server` | What's using the server right now: loaded chunks, entities, the busiest chunks with coordinates, and the most common entities. 15s cooldown. | Server online |
| `/recap` | `server` | Stats and a graph for the last 24 hours. | |
| `/whitelist` | `action` (add/remove), `player`, `server` | Adds or removes a player from the whitelist. | `allow.whitelist` |
| `/mod kick` | `player`, `reason`, `server` | Kicks an online player. | `allow.moderation` |
| `/mod ban` | `player`, `reason`, `server` | Bans a player. | `allow.moderation` |
| `/mod unban` | `player`, `server` | Unbans a player. | `allow.moderation` |
| `/mod op` / `/mod deop` | `player`, `server` | Gives or removes operator status. | `allow.moderation` |
| `/mod gamemode` | `player`, `mode`, `server` | Changes a player's game mode (survival, creative, adventure, spectator). | `allow.moderation` |
| `/msg` | `player`, `message`, `server` | Sends a private message to an online player. | `allow.chat` |
| `/rolesync add` | `group`, `role`, `direction`, `server` | Links a permissions group (LuckPerms or Vault) to a Discord role. Directions: `both`, `minecraft-to-discord`, `discord-to-minecraft`. | LuckPerms or Vault, `allow.roles` |
| `/rolesync remove` | `group`, `server` | Removes a role link. | |
| `/rolesync list` | `server` | Shows every role link. | |
| `/audit` | | The last 15 MCBridge actions in this Discord. | |
| `/unlink` | `server` | Disconnects a Minecraft server. Its token stops working and its settings and stats are deleted. | |

### Admin (Administrator)

| Command | Options | What it does | Needs |
|---|---|---|---|
| `/console` | `cmd`, `server` | Runs a console command and shows the output. Suggests commands and arguments as you type. Every command is logged. | `allow.console` |

## Channels (set in `/settings`)

| Channel | What goes there |
|---|---|
| Alerts | Crashes, clean stops, lag (with diagnostics), back online, plugin disconnected, the daily recap, the "linked" message. |
| Chat bridge | Two-way chat. Minecraft messages show with each player's name and skin head (needs Manage Webhooks). |
| Player feed | Joins, leaves, deaths and advancements. Falls back to the chat channel. Each event type can be turned off. |
| Whitelist requests | Requests with Approve/Deny buttons. Falls back to the alerts channel. |
| Console | The live server console, in batches. Admins can type commands straight into it. IP addresses are hidden. Needs `allow.console`. |
| Stat channel | A voice channel whose name shows the server status and player count, e.g. `🟢 12/50 online`. Updated about every 10 minutes (Discord's rename limit). |

## Join requirements (set in `/settings` → Access & branding)

| Setting | What happens |
|---|---|
| Anyone can join | Off. Nothing changes. |
| Must link their Discord account | Players who haven't linked are kicked with a code. They run `/account link code:<code>` in Discord, then rejoin. |
| Must link their Discord and have a role | Same, and they also need the role you pick. |

- Operators can always join.
- Players whose linked account has left the Discord are told to rejoin it.
- If the bot can't be reached, `join-requirement.when-bot-offline` in the plugin config decides: `recent` (default) lets in
  players who passed in the last 30 days, `allow` lets everyone in, `deny` keeps everyone out except operators.
- The kick messages are in the plugin config under `messages.join-*`.
- Needs plugin 0.4.0+.

## Branding (set in `/settings` → Access & branding)

Pick an embed colour (hex, e.g. `#3987E5`) and footer text. The colour is used for MCBridge's neutral messages (status
cards keep green, yellow and red) and as the accent on the image cards. The footer replaces "MCBridge" in footers.

## Role sync

Links permission groups to Discord roles for players who linked their account with `/account link`.

- **Minecraft → Discord**: when a linked player joins or their groups change (LuckPerms), MCBridge adds the Discord roles for groups they have and removes the ones they don't.
- **Discord → Minecraft**: when a linked player joins the server, MCBridge gives them the groups for Discord roles they have and removes groups for linked roles they don't.
- Only roles and groups you link are ever touched. MCBridge's role must be above the roles it manages.

## In-game commands

| Command | Permission (default) | What it does |
|---|---|---|
| `/mcbridge` or `/mcbridge status` | `mcbridge.admin` (op) | Connection status, and an update notice if a new version is out. |
| `/mcbridge link <code>` | `mcbridge.admin` (op) | Links this server using a code from `/setup`. Also works in the console. |
| `/mcbridge reload` | `mcbridge.admin` (op) | Reloads config.yml and reconnects. |
| `/mcbridge help` | `mcbridge.admin` (op) | Lists the commands. |
| `/discord link <code>` (alias `/dlink`) | `mcbridge.link` (everyone) | Links your account using a code from `/account link`. |

## Plugin config (`plugins/MCBridge/config.yml`)

| Key | Default | What it does |
|---|---|---|
| `bot-url` | `wss://bot.mcbridge.dev/v1/plugin` | Where the bot is. Only change it if you host your own. |
| `token` | `""` | This server's secret. Filled in by `/mcbridge link`. Never share it. |
| `update-check` | `true` | Check GitHub for new versions every 6 hours and tell admins. |
| `allow.chat` | `true` | Discord chat and `/msg` show in-game. |
| `allow.whitelist` | `true` | `/whitelist` and whitelist requests. |
| `allow.moderation` | `false` | `/mod` kick, ban, unban, op, deop, gamemode. |
| `allow.roles` | `true` | Role sync can add and remove permission groups. |
| `allow.console` | `false` | `/console` and the console channel. Gives full control of the server. |
| `join-requirement.when-bot-offline` | `recent` | What to do with join requirements when the bot can't be reached: `recent`, `allow` or `deny`. |
| `messages.*` | | Every message the plugin shows, in MiniMessage or `&` colour codes, including the join requirement kick messages. |

## Requirements

- Bot permissions: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Add Reactions,
  Manage Webhooks, Manage Roles, Manage Channels (invite permission number `805424208`).
- Paper or a Paper fork (e.g. Purpur) on Minecraft 1.21.x, Java 21. Spigot and Folia aren't supported.
- Role sync needs LuckPerms or Vault (with a permissions plugin).
