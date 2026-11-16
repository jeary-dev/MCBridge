import type { Metadata } from "next";
import Link from "next/link";
import { CONTACT_EMAIL, GITHUB_URL } from "@/config";
import { LegalPage } from "@/components/LegalPage";
import { pageMeta } from "@/lib/meta";

const description = "The terms for using the MCBridge Discord bot and Minecraft plugin.";

export const metadata: Metadata = pageMeta({ title: "Terms of service", description, path: "/terms" });

export default function TermsPage() {
  return (
    <LegalPage kanji="規約" label="Legal · Terms" title="Terms of service" updated="November 16, 2026">
      <p>
        These terms cover your use of the MCBridge Discord bot, the hosted service behind it, and the
        MCBridge plugin. By adding the bot to a Discord server or linking a Minecraft server to it, you
        agree to them.
      </p>

      <h2>The service</h2>
      <p>
        MCBridge is provided free of charge, as is, without any warranty. We work to keep it running, but
        we can&apos;t promise it will always be available, error-free or that alerts will always arrive.
        Don&apos;t rely on MCBridge as your only way to monitor a server.
      </p>

      <h2>Your responsibilities</h2>
      <ul>
        <li>Only link servers and Discord communities you run or have permission to manage.</li>
        <li>Follow Discord&apos;s Terms of Service and Community Guidelines, and the Minecraft EULA.</li>
        <li>
          You are responsible for what you do with MCBridge, including commands run through the remote
          console and who you give access to it.
        </li>
        <li>Keep your server&apos;s token secret. If you think it has leaked, unlink and link again.</li>
      </ul>

      <h2>Acceptable use</h2>
      <p>Don&apos;t use MCBridge to:</p>
      <ul>
        <li>break the law, or harass, spam or harm others;</li>
        <li>try to access servers, data or accounts that aren&apos;t yours;</li>
        <li>overload, attack or interfere with the service or its infrastructure.</li>
      </ul>
      <p>We may stop serving a Discord or Minecraft server that breaks these terms.</p>

      <h2>Open source</h2>
      <p>
        The MCBridge code is licensed under the{" "}
        <a href={`${GITHUB_URL}/blob/main/LICENSE`} target="_blank" rel="noopener noreferrer">
          GNU Affero General Public License v3.0
        </a>
        . The license, not these terms, governs what you can do with the code itself. These terms cover
        the hosted service we run.
      </p>

      <h2>Your data</h2>
      <p>
        How we handle data is described in the <Link href="/privacy">privacy policy</Link>. You can stop
        using MCBridge at any time by running <code>/unlink</code> or removing the bot from your Discord
        server.
      </p>

      <h2>Liability</h2>
      <p>
        To the extent the law allows, we aren&apos;t liable for any loss or damage from using MCBridge,
        including downtime, missed alerts, lost data or commands run on your server.
      </p>

      <h2>Not affiliated</h2>
      <p>
        MCBridge is not an official Minecraft product and is not approved by or associated with Mojang or
        Microsoft. It is not affiliated with Discord.
      </p>

      <h2>Changes</h2>
      <p>
        We may update these terms. When we do, we&apos;ll change the date at the top of this page.
        Continuing to use MCBridge after that means you accept the new terms. Questions? Email{" "}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.
      </p>
    </LegalPage>
  );
}
