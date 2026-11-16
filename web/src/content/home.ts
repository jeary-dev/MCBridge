export type Feature = {
  title: string;
  body: string;
  tag: string;
};

export const FEATURES: Feature[] = [
  {
    title: "Live status card",
    body: "Real TPS, MSPT and RAM, the players online, your server icon and a graph of the last hour. One message that keeps itself up to date.",
    tag: "/status live",
  },
  {
    title: "Crash vs restart detection",
    body: "MCBridge knows the difference between a clean restart and a crash. Lag alerts ping the role you choose, and a notice lands when you're back online.",
    tag: "alerts",
  },
  {
    title: "Lag diagnostics",
    body: "The busiest chunks, with coordinates, and the most common entities. Attached to every lag alert and available any time with /lag.",
    tag: "/lag",
  },
  {
    title: "Two-way chat bridge",
    body: "Discord and Minecraft chat in one place, with each player's name and skin head. Plus a feed of joins, leaves, deaths and advancements.",
    tag: "chat",
  },
  {
    title: "Whitelist requests",
    body: "Players ask from Discord. Staff approve or deny with one button, and the player gets a DM with the result.",
    tag: "/whitelist-request",
  },
  {
    title: "Player stats",
    body: "Playtime, sessions, deaths and last seen for anyone with /player, and a leaderboard of the most active players with /top.",
    tag: "/player · /top",
  },
  {
    title: "Daily recap",
    body: "Peak players, uptime, average TPS, minutes of lag and a 24-hour graph, posted once a day to the channel you pick.",
    tag: "/recap",
  },
  {
    title: "Account linking",
    body: "Players run /account link in Discord and /discord link <code> in game. Linked members get a role automatically.",
    tag: "/account link",
  },
  {
    title: "Setup wizard",
    body: "/settings picks every channel and role with menus. No config files, no IDs to copy.",
    tag: "/settings",
  },
  {
    title: "Remote console",
    body: "Run console commands from Discord as an admin. Off by default in the plugin, and every command is recorded in the audit log.",
    tag: "/console",
  },
];

export type Cell = true | false | string;

export const COMPARE_COLUMNS = ["MCBridge", "Status bots", "Self-hosted chat plugins"] as const;

export const COMPARE_ROWS: { label: string; cells: [Cell, Cell, Cell] }[] = [
  { label: "Real TPS, MSPT and memory", cells: [true, false, "Some"] },
  { label: "Tells a crash from a restart", cells: [true, false, false] },
  { label: "Lag alerts with the busiest chunks", cells: [true, false, false] },
  { label: "Two-way chat with skin heads", cells: [true, false, true] },
  { label: "Whitelist requests with buttons", cells: [true, false, false] },
  { label: "Player stats and leaderboard", cells: [true, false, "Some"] },
  { label: "Daily recap with graphs", cells: [true, false, false] },
  { label: "Nothing to host", cells: [true, true, false] },
  { label: "No open ports", cells: [true, false, true] },
  { label: "Open source", cells: [true, "Varies", "Varies"] },
];

export const STEPS = [
  {
    kanji: "一",
    title: "Add the bot",
    body: "Invite MCBridge to your Discord server. It asks only for the permissions it uses.",
  },
  {
    kanji: "二",
    title: "Run /setup",
    body: "Type /setup and a name in Discord. You get a 6-character link code that works once and expires after 10 minutes.",
  },
  {
    kanji: "三",
    title: "Type the code",
    body: "Put the plugin in your plugins folder and restart. Then run /mcbridge link with your code in the server console. That's it.",
  },
];

export const COMMANDS = [
  "/setup",
  "/settings",
  "/status live",
  "/player",
  "/top",
  "/lag",
  "/recap",
  "/whitelist-request",
  "/account link",
  "/servers",
  "/console",
  "/audit",
];

export type Faq = { q: string; a: string };

export const FAQ: Faq[] = [
  {
    q: "Do I need to host anything?",
    a: "No. We host the bot. You only install the plugin on your Minecraft server. The plugin connects out to MCBridge over a secure WebSocket, so you don't need to open ports, set up port forwarding or have a static IP.",
  },
  {
    q: "Which servers does it work on?",
    a: "Paper or a Paper fork like Purpur, on Minecraft 1.21.x with Java 21. Spigot and Folia aren't supported. A Fabric version is on the roadmap.",
  },
  {
    q: "How is this different from a status bot?",
    a: "A status bot can only ping your server from the outside, so all it sees is online or offline and a player count. MCBridge runs inside the server, so it sees real TPS, MSPT and memory, knows a crash from a restart, and can find the chunks causing lag.",
  },
  {
    q: "How does it tell a crash from a restart?",
    a: "The plugin sends a heartbeat every few seconds and a stop message when the server shuts down cleanly. If the heartbeats stop without a stop message, that's a crash. MCBridge waits 30 seconds first, so a quick reconnect doesn't cause a false alert.",
  },
  {
    q: "Is the remote console safe?",
    a: "It's off by default. You have to turn it on in the plugin's config, only Discord members with the Administrator permission can use it, and every command is written to the audit log (/audit).",
  },
  {
    q: "Can I connect more than one server?",
    a: "Yes. Run /setup once for each Minecraft server. /servers lists everything linked to your Discord.",
  },
  {
    q: "What data do you store?",
    a: "Only what the features need: your server's name and settings, the channels and roles you pick, stats samples for the graphs (kept for 8 days), player names and playtime counters, linked accounts and the audit log. Chat messages are passed through, not stored. The privacy policy has the full list.",
  },
  {
    q: "Is it free?",
    a: "Yes. MCBridge is free to use, and the code is open source under AGPL-3.0, so you can also read it, change it or run it yourself.",
  },
];
