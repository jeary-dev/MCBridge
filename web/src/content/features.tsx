/**
 * Feature guides for /docs/features/*.
 *
 * ⚠️ MUST MATCH docs/COMMANDS.md (the source of truth for commands, channels, role sync and config keys).
 * Numbers that aren't in COMMANDS.md (lag thresholds, crash wait) come from bot/mcbridge_bot/alerts.py
 * and docs/PROTOCOL.md; update them here if those change.
 */
import Link from "next/link";
import type { DocPage } from "./doc-types";
import { Callout, CodeBlock, DataTable } from "@/components/docs/Prose";
import { CHANNELS, PERMISSIONS_NOTE } from "./commands";

const EDIT = "web/src/content/features.tsx";
const cmd = (slug: string, label = `/${slug}`) => (
  <Link href={`/docs/commands/${slug}`}>
    <code>{label}</code>
  </Link>
);

export const FEATURE_PAGES: DocPage[] = [
  {
    href: "/docs/features/status",
    title: "Status & graphs",
    description: "Live TPS, MSPT, memory and players in Discord, with a graph of the last hour and a self-updating status message.",
    editPath: EDIT,
    intro: (
      <p>
        {cmd("status")} shows what your server is doing right now, measured from inside the server: real TPS, MSPT and
        memory, who&apos;s online, your server icon and a graph of the last hour.
      </p>
    ),
    sections: [
      {
        id: "whats-on-the-card",
        title: "What's on the card",
        body: (
          <ul>
            <li><strong>TPS</strong>: ticks per second, the 1, 5 and 15 minute averages. 20 is perfect.</li>
            <li><strong>MSPT</strong>: milliseconds per tick. Anything over 50 ms means the server can&apos;t keep up 20 TPS.</li>
            <li><strong>Memory</strong>: used and maximum heap.</li>
            <li><strong>Players</strong>: who&apos;s online, out of the server&apos;s max.</li>
            <li><strong>Graph</strong>: players and TPS over the last hour.</li>
          </ul>
        ),
      },
      {
        id: "live-status-message",
        title: "Live status message",
        body: (
          <>
            <p>
              <code>/status live:True</code> posts a status message in the current channel that updates itself every
              minute. It needs Manage Server, and the bot needs Send Messages, Embed Links and Attach Files in that
              channel. You can also post it from {cmd("settings")}. Delete the message to stop it.
            </p>
            <CodeBlock lines="/status live:True" />
          </>
        ),
      },
      {
        id: "more-than-one-server",
        title: "More than one server",
        body: (
          <p>
            Every command has a <code>server</code> option. You only need it when more than one Minecraft server is
            linked to the Discord. {cmd("servers")} lists them all.
          </p>
        ),
      },
    ],
  },
  {
    href: "/docs/features/alerts",
    title: "Alerts & crash detection",
    description: "Crash vs clean stop, lag alerts with diagnostics, back-online notices and role pings.",
    editPath: EDIT,
    intro: (
      <p>
        Alerts go to the <strong>alerts channel</strong> you pick in {cmd("settings")}, and can ping a role you choose.
      </p>
    ),
    sections: [
      {
        id: "what-gets-an-alert",
        title: "What gets an alert",
        body: (
          <ul>
            <li><strong>Crashed</strong>: the server stopped answering and didn&apos;t shut down cleanly.</li>
            <li><strong>Stopped</strong>: a clean shutdown. This one doesn&apos;t ping anyone.</li>
            <li><strong>Plugin disconnected</strong>: the server still answers pings but the plugin lost its connection.</li>
            <li><strong>Lag</strong>: TPS below 15 for 3 checks in a row, with the busiest chunks and entities attached.</li>
            <li><strong>Back online</strong>: after any of the above.</li>
          </ul>
        ),
      },
      {
        id: "crash-or-restart",
        title: "How it tells a crash from a restart",
        body: (
          <p>
            The plugin sends a heartbeat every few seconds and a stop message when the server shuts down cleanly. If the
            heartbeats stop without a stop message, MCBridge checks whether the server still answers a status ping to
            decide between <em>crashed</em> and <em>plugin disconnected</em>. A quick reconnect doesn&apos;t cause a false alert.
          </p>
        ),
      },
      {
        id: "lag",
        title: "Lag alerts",
        body: (
          <p>
            A lag alert fires when TPS stays below 15 for 3 checks in a row, and clears once TPS is back to 18 or more
            for 3 checks. It includes the same diagnostics as {cmd("lag")}. See{" "}
            <Link href="/docs/features/lag-diagnostics">Lag diagnostics</Link>.
          </p>
        ),
      },
    ],
  },
  {
    href: "/docs/features/lag-diagnostics",
    title: "Lag diagnostics",
    description: "Find the chunks and entities slowing your server down, with coordinates.",
    editPath: EDIT,
    intro: <p>{cmd("lag")} shows what&apos;s using the server right now. Lag alerts include the same report automatically.</p>,
    sections: [
      {
        id: "whats-in-the-report",
        title: "What's in the report",
        body: (
          <ul>
            <li>Loaded chunks and entities.</li>
            <li>The busiest chunks, with world and coordinates, so you can teleport straight there.</li>
            <li>The most common entities (dropped items, mobs, minecarts and so on).</li>
          </ul>
        ),
      },
      {
        id: "who-can-use-it",
        title: "Who can use it",
        body: <p>Staff (Manage Server). The server must be online. There&apos;s a 15 second cooldown.</p>,
      },
    ],
  },
  {
    href: "/docs/features/chat-bridge",
    title: "Chat bridge",
    description: "Two-way chat between Discord and Minecraft, with player names and skin heads.",
    editPath: EDIT,
    intro: <p>Pick a <strong>chat bridge</strong> channel in {cmd("settings")}. Messages go both ways.</p>,
    sections: [
      {
        id: "minecraft-to-discord",
        title: "Minecraft to Discord",
        body: (
          <p>
            Minecraft messages show with each player&apos;s name and skin head. For that the bot needs{" "}
            <strong>Manage Webhooks</strong> in the channel; without it, messages show as the bot.
          </p>
        ),
      },
      {
        id: "discord-to-minecraft",
        title: "Discord to Minecraft",
        body: (
          <>
            <p>
              Discord messages show in-game when <code>allow.chat</code> is on (it is by default). How they look is set by{" "}
              <code>messages.discord-chat</code> in <code>config.yml</code>, with the placeholders <code>&lt;author&gt;</code>{" "}
              and <code>&lt;message&gt;</code>.
            </p>
            <p>
              Staff can also send a private message to one player with {cmd("msg")}.
            </p>
          </>
        ),
      },
    ],
  },
  {
    href: "/docs/features/player-feed",
    title: "Player feed & filters",
    description: "Joins, leaves, deaths and advancements in a Discord channel, and how to turn each one off.",
    editPath: EDIT,
    intro: <p>Pick a <strong>player feed</strong> channel in {cmd("settings")}. If you don&apos;t, the feed goes to the chat channel.</p>,
    sections: [
      {
        id: "events",
        title: "Events",
        body: <p>Joins, leaves, deaths and advancements.</p>,
      },
      {
        id: "filters",
        title: "Filters",
        body: <p>Each event type can be turned off in the feed filters in {cmd("settings")}.</p>,
      },
    ],
  },
  {
    href: "/docs/features/whitelist-requests",
    title: "Whitelist requests",
    description: "Members ask from Discord, staff approve or deny with one button, and the player gets a DM.",
    editPath: EDIT,
    intro: <p>Members run {cmd("whitelist-request")} with their Minecraft username. Staff get Approve/Deny buttons.</p>,
    sections: [
      {
        id: "how-it-works",
        title: "How it works",
        body: (
          <ol>
            <li>A member runs <code>/whitelist-request player:&lt;name&gt;</code>.</li>
            <li>The request is posted in the whitelist requests channel, or the alerts channel if none is set.</li>
            <li>Staff click Approve or Deny. The member gets a DM with the answer.</li>
          </ol>
        ),
      },
      {
        id: "limits",
        title: "Limits",
        body: <p>One pending request per member at a time, and a 30 second cooldown. Approving needs <code>allow.whitelist</code>.</p>,
      },
      {
        id: "manual",
        title: "Adding players directly",
        body: <p>Staff can add or remove players without a request using {cmd("whitelist")}.</p>,
      },
    ],
  },
  {
    href: "/docs/features/stats-recap",
    title: "Stats & daily recap",
    description: "Player playtime, Minecraft statistics, leaderboards and a daily summary of your server.",
    editPath: EDIT,
    sections: [
      {
        id: "player-stats",
        title: "Player stats",
        body: (
          <ul>
            <li>{cmd("player")}: playtime, sessions, deaths, first joined, last seen and linked Discord account, tracked by MCBridge.</li>
            <li>{cmd("stats")}: Minecraft&apos;s own statistics, like kills, distance travelled and fish caught (plugin 0.3.0+).</li>
            <li>{cmd("inventory")}: what an online player is carrying (plugin 0.3.0+).</li>
            <li>{cmd("top")}: the 10 most active players by playtime.</li>
          </ul>
        ),
      },
      {
        id: "daily-recap",
        title: "Daily recap",
        body: (
          <p>
            Once a day MCBridge can post peak players, uptime, average TPS, minutes of lag and a 24-hour graph to the
            alerts channel. Turn it on or off in {cmd("settings")}. Staff can see the same report any time with{" "}
            {cmd("recap")}.
          </p>
        ),
      },
    ],
  },
  {
    href: "/docs/features/account-linking",
    title: "Account linking",
    description: "Link Discord members to their Minecraft accounts, with an automatic role.",
    editPath: EDIT,
    sections: [
      {
        id: "how-to-link",
        title: "How to link",
        body: (
          <>
            <ol>
              <li>Run {cmd("account", "/account link")} in Discord. You get a code that works once and expires after 10 minutes.</li>
              <li>Join the Minecraft server and type the code:</li>
            </ol>
            <CodeBlock lines="/discord link <code>" />
            <p>
              <code>/dlink</code> is a shorter alias. The in-game command needs <code>mcbridge.link</code>, which everyone
              has by default.
            </p>
          </>
        ),
      },
      {
        id: "linked-role",
        title: "Linked role",
        body: <p>Pick a role in {cmd("settings")} and linked members get it automatically.</p>,
      },
      {
        id: "unlinking",
        title: "Unlinking",
        body: <p><code>/account unlink</code> unlinks your Minecraft account and removes linked roles.</p>,
      },
    ],
  },
  {
    href: "/docs/features/role-sync",
    title: "Role sync",
    description: "Keep LuckPerms or Vault groups and Discord roles in step for linked players.",
    editPath: EDIT,
    intro: (
      <p>
        Role sync links permission groups to Discord roles for players who linked their account with{" "}
        {cmd("account", "/account link")}. Set it up with {cmd("rolesync")}.
      </p>
    ),
    sections: [
      {
        id: "directions",
        title: "Directions",
        body: (
          <ul>
            <li>
              <strong>minecraft-to-discord</strong>: when a linked player joins or their groups change (LuckPerms),
              MCBridge adds the Discord roles for groups they have and removes the ones they don&apos;t.
            </li>
            <li>
              <strong>discord-to-minecraft</strong>: when a linked player joins the server, MCBridge gives them the
              groups for Discord roles they have and removes groups for linked roles they don&apos;t.
            </li>
            <li><strong>both</strong> (the default): both of the above.</li>
          </ul>
        ),
      },
      {
        id: "example",
        title: "Example",
        body: <CodeBlock lines={["/rolesync add group:vip role:@VIP direction:both", "/rolesync list"]} />,
      },
      {
        id: "requirements",
        title: "Requirements",
        body: (
          <ul>
            <li>LuckPerms or Vault (with a permissions plugin) on the Minecraft server.</li>
            <li><code>allow.roles</code> on in the plugin config (it is by default).</li>
            <li>MCBridge&apos;s role must be above the roles it manages, in Server Settings → Roles.</li>
            <li>Only roles and groups you link are ever touched.</li>
          </ul>
        ),
      },
    ],
  },
  {
    href: "/docs/features/console-channel",
    title: "Console channel",
    description: "Stream the server console into Discord and run commands from it.",
    editPath: EDIT,
    intro: (
      <Callout title="Full control" tone="warn">
        The console gives full control of the server. It&apos;s off by default. Only turn on <code>allow.console</code> if
        you trust everyone with Administrator in your Discord.
      </Callout>
    ),
    sections: [
      {
        id: "turn-it-on",
        title: "Turn it on",
        body: (
          <ol>
            <li>Set <code>allow.console: true</code> in <code>plugins/MCBridge/config.yml</code> and run <code>/mcbridge reload</code>.</li>
            <li>Pick a console channel in {cmd("settings")}. Make it private to admins.</li>
          </ol>
        ),
      },
      {
        id: "how-it-works",
        title: "How it works",
        body: (
          <p>
            The live console is posted in batches. IP addresses are hidden. Admins can type commands straight into the
            channel, or run one from anywhere with {cmd("console")}. Every command is logged in {cmd("audit")}.
          </p>
        ),
      },
    ],
  },
  {
    href: "/docs/features/stat-channel",
    title: "Stat channel",
    description: "A voice channel whose name shows your server's status and player count.",
    editPath: EDIT,
    sections: [
      {
        id: "what-it-is",
        title: "What it is",
        body: (
          <p>
            A voice channel whose name shows the server status and player count, e.g. <code>🟢 12/50 online</code>. Pick
            it in {cmd("settings")}.
          </p>
        ),
      },
      {
        id: "update-speed",
        title: "Update speed",
        body: <p>It&apos;s updated about every 10 minutes, because Discord limits how often a channel can be renamed.</p>,
      },
      {
        id: "permissions",
        title: "Permissions",
        body: (
          <p>
            Renaming the channel needs <strong>Manage Channels</strong>. If you added the bot before it needed that
            permission, re-invite it with the current invite link.
          </p>
        ),
      },
    ],
  },
  {
    href: "/docs/features/moderation",
    title: "Moderation",
    description: "Kick, ban, op and change game modes from Discord, and manage the whitelist.",
    editPath: EDIT,
    intro: (
      <p>
        {cmd("mod")} lets staff moderate players without joining the game. It&apos;s off until you set{" "}
        <code>allow.moderation: true</code> in the plugin config.
      </p>
    ),
    sections: [
      {
        id: "commands",
        title: "Commands",
        body: (
          <DataTable
            caption="Moderation commands"
            head={["Command", "What it does"]}
            rows={[
              ["/mod kick", "Kicks an online player."],
              ["/mod ban", "Bans a player."],
              ["/mod unban", "Unbans a player."],
              ["/mod op / deop", "Gives or removes operator status."],
              ["/mod gamemode", "Changes a player's game mode (survival, creative, adventure, spectator)."],
              ["/whitelist", "Adds or removes a player from the whitelist (needs allow.whitelist)."],
            ]}
          />
        ),
      },
      {
        id: "who-can-use-it",
        title: "Who can use it",
        body: <p>Staff (Manage Server). {PERMISSIONS_NOTE} Every action is recorded in {cmd("audit")}.</p>,
      },
    ],
  },
];

/** The channel table, shared by the overview and settings pages. */
export function ChannelTable() {
  return <DataTable caption="Channels you can set in /settings" head={["Channel", "What goes there"]} rows={CHANNELS.map((c) => [c.channel, c.what])} />;
}
