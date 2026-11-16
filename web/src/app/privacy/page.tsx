import type { Metadata } from "next";
import { CONTACT_EMAIL, GITHUB_URL } from "@/config";
import { LegalPage } from "@/components/LegalPage";
import { pageMeta } from "@/lib/meta";

const description = "What MCBridge collects, why, how long it's kept, and how to have it deleted.";

export const metadata: Metadata = pageMeta({ title: "Privacy policy", description, path: "/privacy" });

export default function PrivacyPage() {
  return (
    <LegalPage kanji="個人情報" label="Legal · Privacy" title="Privacy policy" updated="November 16, 2026">
      <p>
        MCBridge connects a Minecraft server to Discord. This policy explains what the MCBridge bot and
        plugin collect, why, how long we keep it, and how to have it removed. We collect only what the
        features need. We don&apos;t sell data, show ads, or use analytics or tracking cookies, and this
        website sets no cookies at all.
      </p>

      <h2>What we collect</h2>
      <h3>From Discord</h3>
      <ul>
        <li>The IDs of the Discord servers (guilds), channels and roles you set up with MCBridge.</li>
        <li>
          The Discord user ID and display name of people who run MCBridge commands, for features such as
          linking accounts, whitelist requests and the audit log.
        </li>
        <li>
          Messages in the channel you choose for the chat bridge. These are passed through to your
          Minecraft server and are <strong>not stored</strong>.
        </li>
      </ul>
      <h3>From your Minecraft server</h3>
      <ul>
        <li>The name you give the server, its join address if you set one, its MOTD and server icon.</li>
        <li>Performance samples: TPS, MSPT, memory use and the number of players online.</li>
        <li>
          Player names and UUIDs, with first and last seen times, playtime, number of sessions and
          deaths.
        </li>
        <li>
          Chat, join, leave, death and advancement events, which are posted to Discord and
          <strong> not stored</strong>.
        </li>
      </ul>
      <h3>Things you choose to create</h3>
      <ul>
        <li>Links between a Discord account and a Minecraft account.</li>
        <li>Whitelist requests, their status and who approved or denied them.</li>
        <li>The audit log: admin actions such as console commands and whitelist changes.</li>
      </ul>

      <h2>Why we use it</h2>
      <p>
        Only to run MCBridge: to show status cards, graphs and recaps, send alerts, relay chat, handle
        whitelist requests and account linking, and keep an audit trail for your staff.
      </p>

      <h2>How long we keep it</h2>
      <ul>
        <li>Performance samples and session history are deleted after 8 days.</li>
        <li>Link codes expire after 10 minutes and are deleted once used or expired.</li>
        <li>
          Everything else is kept while your server is linked. Run <code>/unlink</code> to remove a
          server and its data. Removing the bot from your Discord server deletes all its linked servers,
          their stats and player data, and its linked accounts.
        </li>
        <li>
          The audit log is kept so staff can review past actions. Email us to have it deleted.
        </li>
      </ul>

      <h2>Security</h2>
      <p>
        The plugin connects to MCBridge over an encrypted connection (<code>wss://</code>). Server
        tokens and link codes are stored hashed, never in plain text. The remote console is off by
        default and every use of it is recorded in the audit log.
      </p>

      <h2>Who we share it with</h2>
      <p>
        Nobody, apart from Discord itself, which receives the messages MCBridge posts. We don&apos;t sell
        or rent data.
      </p>

      <h2>Your rights</h2>
      <p>
        You can ask us for a copy of the data we hold about you, or ask us to delete it, by emailing{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Players can unlink their account at any
        time with <code>/account unlink</code>.
      </p>

      <h2>Open source</h2>
      <p>
        MCBridge is open source. You can read exactly what it does in the code on{" "}
        <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        .
      </p>

      <h2>Changes</h2>
      <p>
        If this policy changes, we&apos;ll update this page and the date at the top. Questions? Email{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>
    </LegalPage>
  );
}
