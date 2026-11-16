/**
 * Every outbound link on the site comes from here. Never hard-code these elsewhere.
 */
export const DISCORD_CLIENT_ID =
  process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID || "YOUR_CLIENT_ID";

/** Bot permissions, see docs/COMMANDS.md → Requirements. 805424208 includes Manage Channels (stat channel). */
export const INVITE_PERMISSIONS = "805424208";

export const INVITE_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&permissions=${INVITE_PERMISSIONS}&scope=bot+applications.commands`;

export const DOWNLOAD_URL = "https://github.com/jeary-dev/MCBridge/releases/latest";

export const GITHUB_URL = "https://github.com/jeary-dev/MCBridge";

/** Base for "Edit this page on GitHub" links on /docs. */
export const GITHUB_EDIT_BASE = `${GITHUB_URL}/edit/main`;

/** Invite to the MCBridge Discord, where the live demo server's chat bridge runs. */
export const SUPPORT_INVITE = "https://discord.gg/HA8scCCJXB";
/** Kept for existing imports. */
export const SUPPORT_URL = SUPPORT_INVITE;

/** Public JSON for the live demo (docs/PROTOCOL.md → "Live demo"). Override for local testing. */
export const DEMO_URL = process.env.NEXT_PUBLIC_DEMO_URL || "https://bot.mcbridge.dev/v1/demo";

export const CONTACT_EMAIL = "contact@mcbridge.dev";

export const SITE_URL = "https://mcbridge.dev";
