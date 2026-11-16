/**
 * Guide pages for /docs: overview, quick start, commands index, plugin and help.
 *
 * ⚠️ MUST MATCH docs/COMMANDS.md (commands, in-game commands, config keys, requirements) and
 * plugin/src/main/resources/config.yml (message keys and colour-code examples).
 */
import Link from "next/link";
import type { DocPage } from "./doc-types";
import { Callout, CodeBlock, DataTable, Step, Steps } from "@/components/docs/Prose";
import { BridgeDiagram } from "@/components/BridgeDiagram";
import {
  ACCESS_LABEL,
  BOT_PERMISSIONS,
  COMMANDS_BY_ACCESS,
  CONFIG_KEYS,
  INGAME_COMMANDS,
  PERMISSIONS_NOTE,
  type Access,
} from "./commands";
import { ChannelTable, FEATURE_PAGES } from "./features";
import { FAQ } from "./home";
import { DOWNLOAD_URL, INVITE_PERMISSIONS, INVITE_URL, SUPPORT_INVITE } from "@/config";

const cmd = (slug: string, label = `/${slug}`) => (
  <Link href={`/docs/commands/${slug}`}>
    <code>{label}</code>
  </Link>
);

function LinkGrid({ items }: { items: { href: string; title: string; body: string }[] }) {
  return (
    <ul className="not-prose my-6 grid gap-px border border-line bg-line sm:grid-cols-2">
      {items.map((i) => (
        <li key={i.href} className="bg-ink">
          <Link href={i.href} className="group block h-full p-5 transition-colors hover:bg-ink-2 focus-visible:bg-ink-2">
            <span className="flex items-center justify-between gap-3 font-display text-[1.02rem] font-medium tracking-tight text-paper">
              {i.title}
              <span aria-hidden className="text-mute transition-transform duration-300 group-hover:translate-x-1">
                →
              </span>
            </span>
            <span className="mt-1.5 block text-[0.9rem] leading-relaxed text-paper-dim">{i.body}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

/* ── /docs ──────────────────────────────────────────────────────────────── */

export const OVERVIEW: DocPage = {
  href: "/docs",
  title: "MCBridge documentation",
  navTitle: "Overview",
  description:
    "What MCBridge is, how the plugin and the hosted bot work together, and where to find every command and setting.",
  editPath: "web/src/content/guides.tsx",
  intro: (
    <p className="text-[1.1rem]">
      MCBridge connects your Minecraft server to Discord. A Paper plugin runs inside your server and talks to a bot we
      host, so Discord sees real TPS, crashes, chat and players, not just a ping.
    </p>
  ),
  sections: [
    {
      id: "how-it-works",
      title: "How it works",
      body: (
        <>
          <p>
            The plugin opens one secure WebSocket <strong>out</strong> to the MCBridge bot. The bot talks to Discord.
            You don&apos;t host anything, and your server needs no open ports or port forwarding.
          </p>
          <div className="not-prose my-8">
            <BridgeDiagram />
          </div>
          <p>
            You link the two with a one-time code: {cmd("setup")} in Discord gives you the code, and{" "}
            <code>mcbridge link &lt;code&gt;</code> in the server console uses it.
          </p>
        </>
      ),
    },
    {
      id: "start-here",
      title: "Start here",
      body: (
        <LinkGrid
          items={[
            { href: "/docs/quick-start", title: "Quick start", body: "Add the bot, install the plugin and link them in about two minutes." },
            { href: "/docs/commands", title: "Commands", body: "Every Discord command, who can use it and what it needs." },
            { href: "/docs/plugin", title: "Plugin & config", body: "Install, config.yml reference, permissions and messages." },
            { href: "/docs/help", title: "Troubleshooting", body: "Fixes for the most common problems, and the FAQ." },
          ]}
        />
      ),
    },
    {
      id: "features",
      title: "Features",
      body: <LinkGrid items={FEATURE_PAGES.map((f) => ({ href: f.href, title: f.title, body: f.description }))} />,
    },
    {
      id: "channels",
      title: "Channels",
      body: (
        <>
          <p>Everything is set with menus in {cmd("settings")}. These are the channels you can pick:</p>
          <ChannelTable />
        </>
      ),
    },
    {
      id: "get-help",
      title: "Get help",
      body: (
        <p>
          Ask in the <a href={SUPPORT_INVITE}>MCBridge Discord</a>, or see <Link href="/docs/help">Troubleshooting</Link>.
        </p>
      ),
    },
  ],
};

/* ── /docs/quick-start ──────────────────────────────────────────────────── */

export const QUICK_START: DocPage = {
  href: "/docs/quick-start",
  title: "Quick start",
  description: "Add the bot, run /setup, install the plugin, link it with one code and post a live status. About two minutes.",
  editPath: "web/src/content/guides.tsx",
  intro: (
    <p>
      You need <strong>Manage Server</strong> in your Discord and access to your Minecraft server&apos;s files and
      console. The server must run Paper or a Paper fork (e.g. Purpur) on 1.21.x with Java 21.
    </p>
  ),
  sections: [
    {
      id: "steps",
      title: "Steps",
      body: (
        <Steps>
          <Step title="Add the bot">
            <p>
              <a href={INVITE_URL}>Add MCBridge to your Discord</a>. The invite asks for the permissions the bot needs
              (permission number <code>{INVITE_PERMISSIONS}</code>).
            </p>
          </Step>
          <Step title="Run /setup">
            <p>In any channel, run {cmd("setup")} with a name for your server. You get a link code that works once and expires after 10 minutes.</p>
            <CodeBlock lines="/setup name:Survival SMP" />
          </Step>
          <Step title="Install the plugin">
            <p>
              <a href={DOWNLOAD_URL}>Download the plugin</a>, put the jar in your server&apos;s <code>plugins</code> folder and
              restart the server.
            </p>
          </Step>
          <Step title="Link the server">
            <p>In the server console, run the command with your code. In-game, ops can run it with a leading slash.</p>
            <CodeBlock lines="mcbridge link <code>" label="Server console" />
          </Step>
          <Step title="Open settings">
            <p>
              MCBridge posts a “linked” message with an <strong>Open settings</strong> button. Click it (or run{" "}
              {cmd("settings")}) to pick channels for alerts, the chat bridge, the player feed and whitelist requests, and a
              role to ping.
            </p>
          </Step>
          <Step title="Try a live status">
            <p>In the channel where you want it, run:</p>
            <CodeBlock lines="/status live:True" />
            <p>The message updates itself every minute.</p>
          </Step>
        </Steps>
      ),
    },
    {
      id: "next",
      title: "What next",
      body: (
        <ul>
          <li><Link href="/docs/features/chat-bridge">Set up the chat bridge</Link></li>
          <li><Link href="/docs/features/account-linking">Let players link their accounts</Link></li>
          <li><Link href="/docs/plugin#config">Choose what the bot is allowed to do</Link> in <code>config.yml</code></li>
        </ul>
      ),
    },
  ],
};

/* ── /docs/commands ─────────────────────────────────────────────────────── */

const ACCESS_INTRO: Record<Access, string> = {
  everyone: "Any member can use these.",
  staff: "Need Manage Server. Hidden from members by default.",
  admin: "Need Administrator.",
};

export const COMMANDS_INDEX: DocPage = {
  href: "/docs/commands",
  title: "Commands",
  navTitle: "All commands",
  description: "Every MCBridge Discord command, grouped by who can use it.",
  editPath: "docs/COMMANDS.md",
  intro: <p>{PERMISSIONS_NOTE}</p>,
  sections: (["everyone", "staff", "admin"] as Access[]).map((a) => ({
    id: a,
    title: ACCESS_LABEL[a],
    body: (
      <>
        <p>{ACCESS_INTRO[a]}</p>
        <ul className="not-prose my-5 divide-y divide-line border-y border-line">
          {COMMANDS_BY_ACCESS[a].map((c) => (
            <li key={c.slug}>
              <Link
                href={`/docs/commands/${c.slug}`}
                className="group grid gap-1 py-3.5 transition-colors hover:bg-ink-2 sm:grid-cols-[12rem_1fr] sm:gap-6 sm:px-2"
              >
                <code className="font-mono text-[0.9rem] text-paper">{c.name}</code>
                <span className="text-[0.92rem] text-paper-dim group-hover:text-paper">{c.summary}</span>
              </Link>
            </li>
          ))}
        </ul>
      </>
    ),
  })),
};

/* ── /docs/plugin ───────────────────────────────────────────────────────── */

export const PLUGIN: DocPage = {
  href: "/docs/plugin",
  title: "Plugin & config",
  description: "Install the MCBridge plugin, the full config.yml reference, permissions, in-game commands and message formatting.",
  editPath: "plugin/src/main/resources/config.yml",
  sections: [
    {
      id: "install",
      title: "Install",
      body: (
        <ol>
          <li><a href={DOWNLOAD_URL}>Download the latest jar</a>.</li>
          <li>Put it in your server&apos;s <code>plugins</code> folder and restart the server.</li>
          <li>Link it with the code from {cmd("setup")}: <code>mcbridge link &lt;code&gt;</code> in the console.</li>
        </ol>
      ),
    },
    {
      id: "requirements",
      title: "Requirements",
      body: (
        <>
          <ul>
            <li>Paper or a Paper fork (e.g. Purpur) on Minecraft 1.21.x.</li>
            <li>Java 21.</li>
            <li>Spigot and Folia aren&apos;t supported.</li>
            <li>Role sync needs LuckPerms or Vault (with a permissions plugin).</li>
          </ul>
          <p>The bot needs these Discord permissions: {BOT_PERMISSIONS.join(", ")} (invite permission number <code>{INVITE_PERMISSIONS}</code>).</p>
        </>
      ),
    },
    {
      id: "config",
      title: "Config reference",
      body: (
        <>
          <p>
            <code>plugins/MCBridge/config.yml</code>. After editing, run <code>/mcbridge reload</code>; no restart needed.
            The <code>allow</code> keys are checked by the plugin itself, so the bot can never do more than you allow.
          </p>
          <DataTable
            caption="config.yml keys"
            head={["Key", "Default", "What it does"]}
            mono={[1]}
            rows={CONFIG_KEYS.map((k) => [k.key, k.default || "-", k.does])}
          />
          <Callout title="Keep the token secret" tone="warn">
            <code>token</code> is filled in by <code>/mcbridge link</code>. Anyone with it can pretend to be your server.
            If it leaks, run {cmd("unlink")} and link again.
          </Callout>
        </>
      ),
    },
    {
      id: "permissions",
      title: "Permissions",
      body: (
        <DataTable
          caption="Plugin permissions"
          head={["Permission", "Default", "Gives"]}
          rows={[
            ["mcbridge.admin", "op", "/mcbridge status, link, reload and help"],
            ["mcbridge.link", "everyone", "/discord link (account linking)"],
          ]}
        />
      ),
    },
    {
      id: "in-game-commands",
      title: "In-game commands",
      body: (
        <DataTable
          caption="In-game commands"
          head={["Command", "Permission (default)", "What it does"]}
          rows={INGAME_COMMANDS.map((c) => [c.command, `${c.permission} (${c.default})`, c.does])}
        />
      ),
    },
    {
      id: "messages",
      title: "Messages and colour codes",
      body: (
        <>
          <p>
            Every message the plugin shows is under <code>messages</code> in <code>config.yml</code>. Use classic{" "}
            <code>&amp;</code> colour codes, MiniMessage tags, or both in the same line. Delete a line to go back to the
            built-in default. Write <code>\&lt;code&gt;</code> to show a literal <code>&lt;code&gt;</code>.
          </p>
          <DataTable
            caption="Colour code examples"
            head={["Write", "Gives"]}
            mono={[]}
            rows={[
              ["&8 · &a · &7 · &f", "Dark grey, green, grey, white"],
              ["&l · &r", "Bold, reset"],
              ["&#3ddc84", "Any hex colour"],
              ["<gray> · <#3ddc84>", "MiniMessage colours"],
              ["<gradient:#3ddc84:#3987e5>text</gradient>", "A gradient"],
              ["<hover:show_text:'hi'>…</hover>", "Text shown on hover"],
              ["<click:suggest_command:'/cmd'>…</click>", "Click to fill in a command"],
            ]}
          />
          <p>Two of the defaults, as examples:</p>
          <CodeBlock
            label="config.yml"
            lines={[
              'prefix: "&8[&#3ddc84MCBridge&8] "',
              'private-message: "&8[&9Discord&8] &7<author> &8→ &7you&8: &f<message>"',
            ]}
          />
          <p>
            Placeholders depend on the message: <code>discord-chat</code> and <code>private-message</code> use{" "}
            <code>&lt;author&gt;</code> and <code>&lt;message&gt;</code>; <code>update-available</code> uses{" "}
            <code>&lt;current&gt;</code> and <code>&lt;latest&gt;</code>. The full MiniMessage format is documented at{" "}
            <a href="https://docs.advntr.dev/minimessage/format.html">docs.advntr.dev</a>.
          </p>
        </>
      ),
    },
    {
      id: "updates",
      title: "Update notifications",
      body: (
        <p>
          With <code>update-check: true</code> (the default) the plugin checks GitHub for a new version every 6 hours.
          Admins see a clickable “Update available” line, and <code>/mcbridge status</code> shows it too. Set it to{" "}
          <code>false</code> to turn it off.
        </p>
      ),
    },
  ],
};

/* ── /docs/help ─────────────────────────────────────────────────────────── */

export const HELP: DocPage = {
  href: "/docs/help",
  title: "Troubleshooting & FAQ",
  navTitle: "Troubleshooting & FAQ",
  description: "Fixes for the most common MCBridge problems: missing bot, chat as the bot, expired codes, missing commands, console and role sync.",
  editPath: "web/src/content/guides.tsx",
  sections: [
    {
      id: "bot-not-in-member-list",
      title: "The bot isn't in the member list",
      body: (
        <p>
          It was added without the <code>bot</code> scope, so only its commands were installed. Add it again with the{" "}
          <a href={INVITE_URL}>invite link</a>, which includes the <code>bot</code> and{" "}
          <code>applications.commands</code> scopes.
        </p>
      ),
    },
    {
      id: "chat-shows-as-the-bot",
      title: "Minecraft chat shows as the bot",
      body: (
        <p>
          Player names and skin heads need <strong>Manage Webhooks</strong> in the chat bridge channel. Give the bot that
          permission, or re-invite it with the current invite link.
        </p>
      ),
    },
    {
      id: "link-code-expired",
      title: "The link code expired or didn't work",
      body: (
        <p>
          Codes work once and expire after 10 minutes. Run {cmd("setup")} again for a new server code, or{" "}
          {cmd("account", "/account link")} again for an account code.
        </p>
      ),
    },
    {
      id: "commands-not-showing",
      title: "Commands aren't showing",
      body: (
        <ul>
          <li>Staff commands are hidden from members who don&apos;t have Manage Server. That&apos;s on purpose.</li>
          <li>An admin may have changed who can use them in Server Settings → Integrations → MCBridge.</li>
          <li>If no MCBridge commands show at all, add the bot again with the invite link (it needs the <code>applications.commands</code> scope).</li>
        </ul>
      ),
    },
    {
      id: "console-channel-empty",
      title: "The console channel is empty",
      body: (
        <p>
          The console is off by default. Set <code>allow.console: true</code> in <code>plugins/MCBridge/config.yml</code>{" "}
          and run <code>/mcbridge reload</code>. See <Link href="/docs/features/console-channel">Console channel</Link>.
        </p>
      ),
    },
    {
      id: "role-sync-not-working",
      title: "Role sync isn't working",
      body: (
        <ul>
          <li>Install LuckPerms, or Vault with a permissions plugin.</li>
          <li>Check <code>allow.roles</code> is <code>true</code> in the plugin config.</li>
          <li>Move MCBridge&apos;s role above the roles it manages, in Server Settings → Roles.</li>
          <li>Only players who linked their account with <code>/account link</code> are synced.</li>
        </ul>
      ),
    },
    {
      id: "faq",
      title: "FAQ",
      body: (
        <dl className="not-prose my-4 divide-y divide-line border-y border-line">
          {FAQ.map((f) => (
            <div key={f.q} className="py-5">
              <dt className="font-display text-[1.05rem] font-medium tracking-tight text-paper">{f.q}</dt>
              <dd className="mt-2 leading-relaxed text-paper-dim">{f.a}</dd>
            </div>
          ))}
        </dl>
      ),
    },
    {
      id: "still-stuck",
      title: "Still stuck?",
      body: (
        <p>
          Ask in the <a href={SUPPORT_INVITE}>MCBridge Discord</a>. Running <code>/mcbridge</code> in-game shows whether
          the plugin is connected.
        </p>
      ),
    },
  ],
};
