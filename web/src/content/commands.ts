/**
 * Discord commands, in-game commands, plugin config and requirements.
 *
 * ⚠️ MUST MATCH docs/COMMANDS.md (the source of truth). When a command, option, permission or config key
 * changes there, change it here too. Option descriptions follow the bot's own `describe()` text in
 * bot/mcbridge_bot/commands.py. Examples are illustrative mock-ups with made-up names.
 */

export type Access = "everyone" | "staff" | "admin";

export const ACCESS_LABEL: Record<Access, string> = {
  everyone: "Everyone",
  staff: "Staff (Manage Server)",
  admin: "Admin (Administrator)",
};

export type CommandOption = {
  name: string;
  required: boolean;
  does: string;
};

export type EmbedTone = "green" | "red" | "amber" | "blue" | "grey";

export type MockEmbed = {
  tone?: EmbedTone;
  title: string;
  description?: string;
  /** Monospace block under the description (rendered like a Discord code block). */
  code?: string;
  fields?: { name: string; value: string; inline?: boolean }[];
  footer?: string;
};

export type MockMessage = {
  /** "bot" = the MCBridge app, otherwise the display name of a member. */
  from: "bot" | string;
  /** "Only you can see this" messages. */
  ephemeral?: boolean;
  /** The "used /command" line above a reply. */
  usedBy?: { user: string; command: string };
  text?: string;
  embed?: MockEmbed;
  /** Use the full live-status card (same component as the homepage hero). */
  statusCard?: boolean;
  buttons?: { label: string; style?: "primary" | "success" | "danger" | "secondary" }[];
};

export type Subcommand = {
  name: string;
  usage: string;
  does: string;
  options: CommandOption[];
  needs?: string[];
};

export type Command = {
  slug: string;
  name: string;
  access: Access;
  /** One line, shown in lists and as the page description. */
  summary: string;
  /** The "What it does" text from docs/COMMANDS.md. */
  does: string;
  usage: string[];
  options: CommandOption[];
  subcommands?: Subcommand[];
  /** The "Needs" column from docs/COMMANDS.md, plus extra permissions it mentions. */
  needs: string[];
  goodToKnow: string[];
  related: string[];
  example: MockMessage[];
};

const SERVER_OPTION: CommandOption = {
  name: "server",
  required: false,
  does: "Which linked Minecraft server. Only needed if this Discord has more than one.",
};

export const COMMANDS: Command[] = [
  /* ── Everyone ─────────────────────────────────────────────────────────── */
  {
    slug: "help",
    name: "/help",
    access: "everyone",
    summary: "Lists every command.",
    does: "Lists every command.",
    usage: ["/help"],
    options: [],
    needs: [],
    goodToKnow: ["This documentation has a page for every command, with options and examples."],
    related: ["status", "servers"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/help" },
        embed: {
          tone: "blue",
          title: "MCBridge",
          description: "Your Minecraft server, live in Discord.",
          fields: [
            { name: "Everyone", value: "/status · /servers · /player · /stats · /inventory · /top · /whitelist-request · /account" },
            { name: "Staff", value: "/setup · /settings · /lag · /recap · /whitelist · /mod · /msg · /rolesync · /audit · /unlink" },
          ],
        },
      },
    ],
  },
  {
    slug: "status",
    name: "/status",
    access: "everyone",
    summary: "Live TPS, MSPT, memory, players and a graph of the last hour.",
    does:
      "Live TPS, MSPT, memory, players, server icon and a graph of the last hour. live:True posts a message that updates itself every minute (needs Manage Server).",
    usage: ["/status", "/status live:True", "/status server:Survival"],
    options: [
      SERVER_OPTION,
      { name: "live", required: false, does: "Post a status message here that updates itself every minute. Needs Manage Server." },
    ],
    needs: ["A linked server", "Manage Server for live:True"],
    goodToKnow: [
      "A live status message keeps updating every minute. Delete the message to stop it.",
      "To post a live status, the bot needs Send Messages, Embed Links and Attach Files in that channel.",
      "You can also post the live status from /settings.",
    ],
    related: ["servers", "recap", "lag", "settings"],
    example: [{ from: "bot", usedBy: { user: "Aoi", command: "/status" }, statusCard: true }],
  },
  {
    slug: "servers",
    name: "/servers",
    access: "everyone",
    summary: "Lists the Minecraft servers linked to this Discord.",
    does: "Lists the Minecraft servers linked to this Discord, with players and TPS.",
    usage: ["/servers"],
    options: [],
    needs: [],
    goodToKnow: ["Link another server with /setup. Each server gets its own settings and channels."],
    related: ["status", "setup", "unlink"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Ren", command: "/servers" },
        embed: {
          tone: "blue",
          title: "Linked servers",
          description: "● Hinoki SMP · 6/20 players · TPS 19.9\n● Creative · 2/20 players · TPS 20.0\n○ Events · offline",
        },
      },
    ],
  },
  {
    slug: "player",
    name: "/player",
    access: "everyone",
    summary: "Playtime, sessions, deaths and last seen for a player.",
    does:
      "Playtime, sessions, deaths, first joined, last seen and linked Discord account, tracked by MCBridge.",
    usage: ["/player name:kiri_"],
    options: [
      { name: "name", required: true, does: "The player's Minecraft username." },
      SERVER_OPTION,
    ],
    needs: ["The player joined since MCBridge was added"],
    goodToKnow: [
      "MCBridge only knows about time played since the plugin was installed. For Minecraft's own all-time statistics, use /stats.",
    ],
    related: ["stats", "top", "account"],
    example: [
      {
        from: "bot",
        usedBy: { user: "nori", command: "/player name:kiri_" },
        embed: {
          tone: "blue",
          title: "kiri_",
          fields: [
            { name: "Playtime", value: "41h 12m", inline: true },
            { name: "Sessions", value: "63", inline: true },
            { name: "Deaths", value: "17", inline: true },
            { name: "First joined", value: "3 months ago", inline: true },
            { name: "Last seen", value: "Online now", inline: true },
            { name: "Discord", value: "@kiri", inline: true },
          ],
        },
      },
    ],
  },
  {
    slug: "stats",
    name: "/stats",
    access: "everyone",
    summary: "Minecraft's own statistics for a player.",
    does:
      "Minecraft's own statistics: play time, mob and player kills, deaths, distance travelled, damage, fish caught and more. Blocks mined and advancements are shown while the player is online.",
    usage: ["/stats name:kiri_"],
    options: [
      { name: "name", required: true, does: "The player's Minecraft username." },
      SERVER_OPTION,
    ],
    needs: ["Server online", "Plugin 0.3.0 or newer"],
    goodToKnow: ["5 second cooldown per person.", "Blocks mined and advancements only show while the player is online."],
    related: ["player", "inventory", "top"],
    example: [
      {
        from: "bot",
        usedBy: { user: "tetsu", command: "/stats name:kiri_" },
        embed: {
          tone: "blue",
          title: "kiri_ · statistics",
          fields: [
            { name: "Play time", value: "6d 2h", inline: true },
            { name: "Mob kills", value: "2,481", inline: true },
            { name: "Player kills", value: "4", inline: true },
            { name: "Deaths", value: "88", inline: true },
            { name: "Distance travelled", value: "412 km", inline: true },
            { name: "Fish caught", value: "57", inline: true },
          ],
        },
      },
    ],
  },
  {
    slug: "inventory",
    name: "/inventory",
    access: "everyone",
    summary: "What an online player is carrying.",
    does:
      "A player's armour, offhand, hotbar and backpack, with item counts, custom names and enchantments.",
    usage: ["/inventory player:kiri_"],
    options: [
      { name: "player", required: true, does: "The player's Minecraft username. They must be online." },
      SERVER_OPTION,
    ],
    needs: ["Server online", "The player is online", "Plugin 0.3.0 or newer"],
    goodToKnow: ["5 second cooldown per person."],
    related: ["stats", "player"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/inventory player:kiri_" },
        embed: {
          tone: "blue",
          title: "kiri_ · inventory",
          fields: [
            { name: "Armour", value: "Diamond helmet (Protection IV) · Iron chestplate · Iron leggings · Diamond boots (Feather Falling IV)" },
            { name: "Offhand", value: "Shield" },
            { name: "Hotbar", value: "Diamond pickaxe (Efficiency V) · Bow · Torch ×48 · Cooked beef ×21" },
            { name: "Backpack", value: "Cobblestone ×256 · Oak log ×64 · “Nether trip” Ender chest" },
          ],
        },
      },
    ],
  },
  {
    slug: "top",
    name: "/top",
    access: "everyone",
    summary: "The 10 most active players by playtime.",
    does: "The 10 most active players by playtime.",
    usage: ["/top"],
    options: [SERVER_OPTION],
    needs: [],
    goodToKnow: ["Playtime counts from when MCBridge was added to the server."],
    related: ["player", "stats", "recap"],
    example: [
      {
        from: "bot",
        usedBy: { user: "moss_block", command: "/top" },
        embed: {
          tone: "blue",
          title: "Most active · Hinoki SMP",
          description: "1. kiri_ · 41h 12m\n2. Aoi · 37h 40m\n3. moss_block · 29h 05m\n4. tetsu · 22h 51m\n5. Ren · 18h 33m",
        },
      },
    ],
  },
  {
    slug: "whitelist-request",
    name: "/whitelist-request",
    access: "everyone",
    summary: "Ask the staff to whitelist your Minecraft account.",
    does:
      "Ask the staff to whitelist your Minecraft account. Staff get Approve/Deny buttons and you get a DM with the answer. One pending request at a time, 30s cooldown.",
    usage: ["/whitelist-request player:kiri_"],
    options: [
      { name: "player", required: true, does: "Your Minecraft username." },
      SERVER_OPTION,
    ],
    needs: ["A whitelist requests or alerts channel"],
    goodToKnow: [
      "Requests go to the whitelist requests channel, or the alerts channel if none is set.",
      "Approving needs allow.whitelist in the plugin config.",
      "Make sure your DMs are open so you can get the answer.",
    ],
    related: ["whitelist", "settings"],
    example: [
      {
        from: "bot",
        embed: {
          tone: "amber",
          title: "Whitelist request",
          description: "kiri_ (requested by @kiri) wants to join Hinoki SMP.",
        },
        buttons: [
          { label: "Approve", style: "success" },
          { label: "Deny", style: "danger" },
        ],
      },
    ],
  },
  {
    slug: "account",
    name: "/account",
    access: "everyone",
    summary: "Link or unlink your Minecraft and Discord accounts.",
    does: "Link your Minecraft and Discord accounts, or unlink them.",
    usage: ["/account link", "/account unlink"],
    options: [],
    subcommands: [
      {
        name: "link",
        usage: "/account link",
        does:
          "Gives you a code. Type /discord link <code> in-game to link your Minecraft and Discord accounts. Codes expire after 10 minutes.",
        options: [],
      },
      {
        name: "unlink",
        usage: "/account unlink",
        does: "Unlinks your Minecraft account and removes linked roles.",
        options: [],
      },
    ],
    needs: ["A linked server"],
    goodToKnow: [
      "The code works once. Linking again replaces your old link.",
      "Staff can pick a role that linked members get automatically, in /settings.",
      "Role sync only works for members who linked their account.",
    ],
    related: ["rolesync", "player", "settings"],
    example: [
      {
        from: "bot",
        ephemeral: true,
        usedBy: { user: "kiri", command: "/account link" },
        embed: {
          tone: "blue",
          title: "Link your Minecraft account",
          description: "Join the server and type:",
          code: "/discord link 7XKQ2M",
          footer: "The code works once and expires in 10 minutes.",
        },
      },
    ],
  },

  /* ── Staff (Manage Server) ────────────────────────────────────────────── */
  {
    slug: "setup",
    name: "/setup",
    access: "staff",
    summary: "Make a link code for a new Minecraft server.",
    does: "Makes a one-time link code (10 minutes) for a new Minecraft server.",
    usage: ["/setup name:Survival SMP"],
    options: [{ name: "name", required: true, does: "A name for the server, e.g. 'Survival SMP'." }],
    needs: [],
    goodToKnow: [
      "Run /mcbridge link <code> in the server console, or in-game as an op.",
      "Keep the code private: anyone with it can link their server to your Discord.",
      "When it's linked, MCBridge posts in this channel with an Open settings button.",
    ],
    related: ["settings", "servers", "unlink"],
    example: [
      {
        from: "bot",
        ephemeral: true,
        usedBy: { user: "Aoi", command: "/setup name:Hinoki SMP" },
        embed: {
          tone: "blue",
          title: "Link Hinoki SMP",
          description:
            "1. Download MCBridge, put it in your server's plugins folder and restart the server.\n2. In the server console (or in-game as an op), run:",
          code: "mcbridge link K7PQ2X",
          fields: [{ name: "Code expires", value: "in 10 minutes (works once)" }],
          footer: "Keep this code private - anyone with it can link their server here.",
        },
      },
    ],
  },
  {
    slug: "settings",
    name: "/settings",
    access: "staff",
    summary: "The setup wizard: channels, roles, recap, live status and feed filters.",
    does:
      "The setup wizard: channels (alerts, chat, feed, whitelist requests, console, stat channel), roles, daily recap, server address, live status, feed filters.",
    usage: ["/settings"],
    options: [SERVER_OPTION],
    needs: ["A linked server"],
    goodToKnow: [
      "Everything is picked with menus. No config files and no IDs to copy.",
      "The Open settings button on the “linked” message opens the same wizard.",
    ],
    related: ["setup", "status", "recap"],
    example: [
      {
        from: "bot",
        ephemeral: true,
        usedBy: { user: "Aoi", command: "/settings" },
        embed: {
          tone: "blue",
          title: "Settings · Hinoki SMP",
          fields: [
            { name: "Alerts", value: "#server-alerts", inline: true },
            { name: "Chat bridge", value: "#minecraft-chat", inline: true },
            { name: "Player feed", value: "#minecraft-chat", inline: true },
            { name: "Daily recap", value: "On", inline: true },
            { name: "Live status", value: "#server-status", inline: true },
            { name: "Stat channel", value: "Not set", inline: true },
          ],
        },
      },
    ],
  },
  {
    slug: "lag",
    name: "/lag",
    access: "staff",
    summary: "What's using the server right now.",
    does:
      "What's using the server right now: loaded chunks, entities, the busiest chunks with coordinates, and the most common entities. 15s cooldown.",
    usage: ["/lag"],
    options: [SERVER_OPTION],
    needs: ["Server online"],
    goodToKnow: ["Lag alerts include the same diagnostics automatically."],
    related: ["status", "recap"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/lag" },
        embed: {
          tone: "amber",
          title: "What's using Hinoki SMP",
          fields: [
            { name: "Loaded chunks", value: "1,284", inline: true },
            { name: "Entities", value: "3,906", inline: true },
            { name: "Busiest chunks", value: "world 412, -88 · 611 entities\nworld -1024, 230 · 284 entities" },
            { name: "Most common", value: "item ×1,120 · cow ×402 · zombie ×188" },
          ],
        },
      },
    ],
  },
  {
    slug: "recap",
    name: "/recap",
    access: "staff",
    summary: "Stats and a graph for the last 24 hours.",
    does: "Stats and a graph for the last 24 hours.",
    usage: ["/recap"],
    options: [SERVER_OPTION],
    needs: [],
    goodToKnow: ["The same recap can be posted automatically once a day. Turn it on in /settings."],
    related: ["status", "top", "settings"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/recap" },
        embed: {
          tone: "blue",
          title: "Last 24 hours · Hinoki SMP",
          fields: [
            { name: "Peak players", value: "14", inline: true },
            { name: "Uptime", value: "100%", inline: true },
            { name: "Average TPS", value: "19.8", inline: true },
            { name: "Lag", value: "3 minutes", inline: true },
          ],
        },
      },
    ],
  },
  {
    slug: "whitelist",
    name: "/whitelist",
    access: "staff",
    summary: "Add or remove a player from the whitelist.",
    does: "Adds or removes a player from the whitelist.",
    usage: ["/whitelist action:add player:kiri_", "/whitelist action:remove player:kiri_"],
    options: [
      { name: "action", required: true, does: "add or remove." },
      { name: "player", required: true, does: "The player's Minecraft username." },
      SERVER_OPTION,
    ],
    needs: ["allow.whitelist in the plugin config"],
    goodToKnow: ["Members can ask to be whitelisted with /whitelist-request."],
    related: ["whitelist-request", "mod"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/whitelist action:add player:kiri_" },
        text: "✅ Added kiri_ to the whitelist on Hinoki SMP.",
      },
    ],
  },
  {
    slug: "mod",
    name: "/mod",
    access: "staff",
    summary: "Kick, ban, unban, op, deop and change game modes.",
    does: "Moderate players on your Minecraft server.",
    usage: [
      "/mod kick player:kiri_ reason:spam",
      "/mod ban player:kiri_ reason:griefing",
      "/mod unban player:kiri_",
      "/mod op player:kiri_",
      "/mod deop player:kiri_",
      "/mod gamemode player:kiri_ mode:creative",
    ],
    options: [],
    subcommands: [
      {
        name: "kick",
        usage: "/mod kick player:<name> reason:<text>",
        does: "Kicks an online player.",
        options: [
          { name: "player", required: true, does: "The player's Minecraft username." },
          { name: "reason", required: false, does: "Shown to the player." },
          SERVER_OPTION,
        ],
      },
      {
        name: "ban",
        usage: "/mod ban player:<name> reason:<text>",
        does: "Bans a player.",
        options: [
          { name: "player", required: true, does: "The player's Minecraft username." },
          { name: "reason", required: false, does: "Shown to the player." },
          SERVER_OPTION,
        ],
      },
      {
        name: "unban",
        usage: "/mod unban player:<name>",
        does: "Unbans a player.",
        options: [{ name: "player", required: true, does: "The player's Minecraft username." }, SERVER_OPTION],
      },
      {
        name: "op / deop",
        usage: "/mod op player:<name>",
        does: "Gives or removes operator status.",
        options: [{ name: "player", required: true, does: "The player's Minecraft username." }, SERVER_OPTION],
      },
      {
        name: "gamemode",
        usage: "/mod gamemode player:<name> mode:<mode>",
        does: "Changes a player's game mode (survival, creative, adventure, spectator).",
        options: [
          { name: "player", required: true, does: "The player's Minecraft username." },
          { name: "mode", required: true, does: "survival, creative, adventure or spectator." },
          SERVER_OPTION,
        ],
      },
    ],
    needs: ["allow.moderation in the plugin config (off by default)"],
    goodToKnow: ["Every moderation action is recorded in /audit."],
    related: ["whitelist", "audit", "console"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/mod kick player:moss_block reason:AFK farm" },
        text: "✅ Kicked moss_block from Hinoki SMP.",
      },
    ],
  },
  {
    slug: "msg",
    name: "/msg",
    access: "staff",
    summary: "Send a private message to an online player.",
    does: "Sends a private message to an online player.",
    usage: ["/msg player:kiri_ message:Server restarts in 5 minutes"],
    options: [
      { name: "player", required: true, does: "The player's Minecraft username. They must be online." },
      { name: "message", required: true, does: "What to send (up to 256 characters)." },
      SERVER_OPTION,
    ],
    needs: ["allow.chat in the plugin config"],
    goodToKnow: ["How the message looks in-game is set by messages.private-message in config.yml."],
    related: ["mod", "console"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/msg player:kiri_ message:Restart in 5 minutes" },
        text: "✅ Sent to kiri_.",
      },
    ],
  },
  {
    slug: "rolesync",
    name: "/rolesync",
    access: "staff",
    summary: "Link permission groups to Discord roles.",
    does: "Links a permissions group (LuckPerms or Vault) to a Discord role, removes links and lists them.",
    usage: ["/rolesync add group:vip role:@VIP direction:both", "/rolesync remove group:vip", "/rolesync list"],
    options: [],
    subcommands: [
      {
        name: "add",
        usage: "/rolesync add group:<group> role:<role> direction:<direction>",
        does:
          "Links a permissions group (LuckPerms or Vault) to a Discord role. Directions: both, minecraft-to-discord, discord-to-minecraft.",
        options: [
          { name: "group", required: true, does: "The permission group name, e.g. vip." },
          { name: "role", required: true, does: "The Discord role." },
          { name: "direction", required: false, does: "Which way changes are copied: both (default), minecraft-to-discord or discord-to-minecraft." },
          SERVER_OPTION,
        ],
        needs: ["LuckPerms or Vault", "allow.roles"],
      },
      {
        name: "remove",
        usage: "/rolesync remove group:<group>",
        does: "Removes a role link.",
        options: [{ name: "group", required: true, does: "The permission group name." }, SERVER_OPTION],
      },
      {
        name: "list",
        usage: "/rolesync list",
        does: "Shows every role link.",
        options: [SERVER_OPTION],
      },
    ],
    needs: ["LuckPerms or Vault (with a permissions plugin)", "allow.roles in the plugin config"],
    goodToKnow: [
      "Only roles and groups you link are ever touched.",
      "MCBridge's role must be above the roles it manages in Server Settings → Roles.",
      "Only players who linked their account with /account link are synced.",
    ],
    related: ["account", "settings"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/rolesync list" },
        embed: {
          tone: "blue",
          title: "Role links · Hinoki SMP",
          description: "vip ⇄ @VIP (both)\nbuilder → @Builder (minecraft-to-discord)\nevents ← @Event Team (discord-to-minecraft)",
        },
      },
    ],
  },
  {
    slug: "audit",
    name: "/audit",
    access: "staff",
    summary: "The last 15 MCBridge actions in this Discord.",
    does: "The last 15 MCBridge actions in this Discord.",
    usage: ["/audit"],
    options: [],
    needs: [],
    goodToKnow: ["Console commands, moderation, whitelist changes and setup changes are all recorded."],
    related: ["console", "mod", "settings"],
    example: [
      {
        from: "bot",
        ephemeral: true,
        usedBy: { user: "Aoi", command: "/audit" },
        embed: {
          tone: "grey",
          title: "Audit log",
          description: "21:04 · Aoi · whitelist add kiri_\n20:51 · Ren · mod kick moss_block\n18:12 · Aoi · status_live #server-status",
        },
      },
    ],
  },
  {
    slug: "unlink",
    name: "/unlink",
    access: "staff",
    summary: "Disconnect a Minecraft server.",
    does: "Disconnects a Minecraft server. Its token stops working and its settings and stats are deleted.",
    usage: ["/unlink"],
    options: [SERVER_OPTION],
    needs: [],
    goodToKnow: [
      "This can't be undone. To connect the server again, run /setup and link it with a new code.",
      "Removing the bot from your Discord also unlinks every server.",
    ],
    related: ["setup", "servers"],
    example: [
      {
        from: "bot",
        ephemeral: true,
        usedBy: { user: "Aoi", command: "/unlink" },
        text: "Unlink Hinoki SMP? Its settings and stats will be deleted.",
        buttons: [
          { label: "Unlink", style: "danger" },
          { label: "Cancel", style: "secondary" },
        ],
      },
    ],
  },

  /* ── Admin (Administrator) ────────────────────────────────────────────── */
  {
    slug: "console",
    name: "/console",
    access: "admin",
    summary: "Run a console command and see the output.",
    does:
      "Runs a console command and shows the output. Suggests commands and arguments as you type. Every command is logged.",
    usage: ["/console cmd:list"],
    options: [
      { name: "cmd", required: true, does: "The command, without a leading /." },
      SERVER_OPTION,
    ],
    needs: ["allow.console in the plugin config (off by default)"],
    goodToKnow: [
      "allow.console gives full control of the server. Only turn it on if you trust everyone with Administrator in your Discord.",
      "With a console channel set in /settings, admins can also type commands straight into that channel.",
    ],
    related: ["audit", "mod"],
    example: [
      {
        from: "bot",
        usedBy: { user: "Aoi", command: "/console cmd:list" },
        embed: {
          tone: "grey",
          title: "list",
          code: "There are 6 of a max of 20 players online: kiri_, Aoi, moss_block, tetsu, Ren, nori",
        },
      },
    ],
  },
];

export const COMMANDS_BY_ACCESS: Record<Access, Command[]> = {
  everyone: COMMANDS.filter((c) => c.access === "everyone"),
  staff: COMMANDS.filter((c) => c.access === "staff"),
  admin: COMMANDS.filter((c) => c.access === "admin"),
};

export function commandBySlug(slug: string) {
  return COMMANDS.find((c) => c.slug === slug);
}

/* ── In-game commands ──────────────────────────────────────────────────── */

export const INGAME_COMMANDS = [
  { command: "/mcbridge or /mcbridge status", permission: "mcbridge.admin", default: "op", does: "Connection status, and an update notice if a new version is out." },
  { command: "/mcbridge link <code>", permission: "mcbridge.admin", default: "op", does: "Links this server using a code from /setup. Also works in the console." },
  { command: "/mcbridge reload", permission: "mcbridge.admin", default: "op", does: "Reloads config.yml and reconnects." },
  { command: "/mcbridge help", permission: "mcbridge.admin", default: "op", does: "Lists the commands." },
  { command: "/discord link <code> (alias /dlink)", permission: "mcbridge.link", default: "everyone", does: "Links your account using a code from /account link." },
];

/* ── Plugin config (plugins/MCBridge/config.yml) ───────────────────────── */

export const CONFIG_KEYS = [
  { key: "bot-url", default: '"wss://bot.mcbridge.dev/v1/plugin"', does: "Where the bot is. Only change it if you host your own." },
  { key: "token", default: '""', does: "This server's secret. Filled in by /mcbridge link. Never share it." },
  { key: "update-check", default: "true", does: "Check GitHub for new versions every 6 hours and tell admins." },
  { key: "allow.chat", default: "true", does: "Discord chat and /msg show in-game." },
  { key: "allow.whitelist", default: "true", does: "/whitelist and whitelist requests." },
  { key: "allow.moderation", default: "false", does: "/mod kick, ban, unban, op, deop, gamemode." },
  { key: "allow.roles", default: "true", does: "Role sync can add and remove permission groups." },
  { key: "allow.console", default: "false", does: "/console and the console channel. Gives full control of the server." },
  { key: "messages.*", default: "", does: "Every message the plugin shows, in MiniMessage or & colour codes." },
];

/* ── Channels set in /settings ─────────────────────────────────────────── */

export const CHANNELS = [
  { channel: "Alerts", what: "Crashes, clean stops, lag (with diagnostics), back online, plugin disconnected, the daily recap, the “linked” message." },
  { channel: "Chat bridge", what: "Two-way chat. Minecraft messages show with each player's name and skin head (needs Manage Webhooks)." },
  { channel: "Player feed", what: "Joins, leaves, deaths and advancements. Falls back to the chat channel. Each event type can be turned off." },
  { channel: "Whitelist requests", what: "Requests with Approve/Deny buttons. Falls back to the alerts channel." },
  { channel: "Console", what: "The live server console, in batches. Admins can type commands straight into it. IP addresses are hidden. Needs allow.console." },
  { channel: "Stat channel", what: "A voice channel whose name shows the server status and player count, e.g. 🟢 12/50 online. Updated about every 10 minutes (Discord's rename limit)." },
];

/* ── Requirements ──────────────────────────────────────────────────────── */

export const BOT_PERMISSIONS = [
  "View Channels",
  "Send Messages",
  "Embed Links",
  "Attach Files",
  "Read Message History",
  "Add Reactions",
  "Manage Webhooks",
  "Manage Roles",
  "Manage Channels",
];

export const PERMISSIONS_NOTE =
  "Staff commands are hidden from members by default. Server admins can change who can use any command in Server Settings → Integrations → MCBridge.";
