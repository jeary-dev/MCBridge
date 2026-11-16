/**
 * Every outbound link on the site comes from here. Never hard-code these elsewhere.
 */
export const DISCORD_CLIENT_ID =
  process.env.NEXT_PUBLIC_DISCORD_CLIENT_ID || "YOUR_CLIENT_ID";

export const INVITE_URL = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&permissions=805424192&scope=bot+applications.commands`;

export const DOWNLOAD_URL = "https://github.com/jeary-dev/MCBridge/releases/latest";

export const GITHUB_URL = "https://github.com/jeary-dev/MCBridge";

export const SUPPORT_URL = "https://discord.gg/HA8scCCJXB";

export const CONTACT_EMAIL = "contact@mcbridge.dev";

export const SITE_URL = "https://mcbridge.dev";
