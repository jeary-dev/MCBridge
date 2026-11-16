import type { ReactNode } from "react";
import { Seal } from "../Logo";
import type { MockEmbed as EmbedData, MockMessage as MessageData } from "@/content/commands";

/*
 * Original, generic chat mock-ups (no third-party logos or assets). Used by the homepage hero,
 * the command examples in /docs and the live demo, so they all look the same.
 */

/* ── Pixel art (original, greyscale) ─────────────────────────────────────── */

const SHADES = ["transparent", "#0e0e0f", "#2a2a2c", "#4d4c4a", "#7c7a75", "#b9b6ae", "#edebe6"];

// An original 8×8 player head: dark fringe, pale face, two eyes.
export const HEAD = ["22222222", "22322232", "23555532", "55555555", "56166165", "55555555", "55433455", "45555554"];

// Server icon: a mountain under a white sun.
export const ICON = ["22222222", "22222662", "22222662", "22266222", "22655622", "26544562", "54433445", "43333334"];

export function Pixels({ grid, size, label }: { grid: string[]; size: number; label?: string }) {
  return (
    <span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className="grid shrink-0 overflow-hidden"
      style={{ width: size, height: size, gridTemplateColumns: "repeat(8, 1fr)", borderRadius: 2 }}
    >
      {grid
        .join("")
        .split("")
        .map((c, i) => (
          <span key={i} style={{ background: SHADES[Number(c)] }} />
        ))}
    </span>
  );
}

/* ── Window, messages, embeds ────────────────────────────────────────────── */

export function MockWindow({
  channel,
  live = false,
  children,
  className = "",
}: {
  channel: string;
  live?: boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative overflow-hidden border border-line-strong bg-ink-2 ${className}`}>
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <span className="flex gap-1.5" aria-hidden>
          <i className="size-2 rounded-full border border-line-strong" />
          <i className="size-2 rounded-full border border-line-strong" />
          <i className="size-2 rounded-full border border-line-strong" />
        </span>
        <span className="min-w-0 truncate font-mono text-[0.75rem] text-paper-dim">
          <span className="text-mute">#</span> {channel}
        </span>
        {live && (
          <span className="ml-auto flex items-center gap-2 font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute">
            <i className="pulse-dot size-1.5 rounded-full bg-accent" /> live
          </span>
        )}
      </div>
      <div className="space-y-5 p-4 sm:p-5">{children}</div>
    </div>
  );
}

function Initial({ name, size = 34 }: { name: string; size?: number }) {
  return (
    <span
      aria-hidden
      className="grid shrink-0 place-items-center rounded-full bg-ink-3 font-display text-[0.85rem] font-medium text-paper-dim ring-1 ring-line-strong"
      style={{ width: size, height: size }}
    >
      {name.replace(/[^a-z0-9]/gi, "").charAt(0).toUpperCase() || "?"}
    </span>
  );
}

export function Message({
  author,
  avatar,
  tag,
  time = "today at 21:04",
  usedBy,
  ephemeral = false,
  children,
}: {
  author: string;
  avatar?: ReactNode;
  tag?: string;
  time?: string;
  usedBy?: { user: string; command: string };
  ephemeral?: boolean;
  children: ReactNode;
}) {
  return (
    <div>
      {usedBy && (
        <div className="mb-1 ml-[2.9rem] truncate font-mono text-[0.75rem] text-mute">
          ↳ <span className="text-paper-dim">{usedBy.user}</span> used{" "}
          <span className="text-paper-dim">{usedBy.command}</span>
        </div>
      )}
      <div className="flex gap-3">
        {avatar ?? <Initial name={author} />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 text-[0.8rem]">
            <span className="font-medium text-paper">{author}</span>
            {tag && (
              <span className="border border-line-strong px-1 font-mono text-[0.75rem] uppercase tracking-wider text-paper-dim">
                {tag}
              </span>
            )}
            <span className="font-mono text-[0.75rem] text-mute">{time}</span>
          </div>
          <div className="mt-1">{children}</div>
          {ephemeral && (
            <div className="mt-1.5 font-mono text-[0.75rem] text-mute">Only you can see this message</div>
          )}
        </div>
      </div>
    </div>
  );
}

export function BotMessage(props: Omit<Parameters<typeof Message>[0], "author" | "avatar" | "tag">) {
  return <Message author="MCBridge" avatar={<Seal size={34} />} tag="App" {...props} />;
}

const TONE: Record<NonNullable<EmbedData["tone"]>, string> = {
  green: "border-accent",
  red: "border-paper",
  amber: "border-paper",
  blue: "border-paper",
  grey: "border-mute",
};

export function Embed({ embed }: { embed: EmbedData }) {
  return (
    <div className={`mt-1 border-l-2 bg-ink-3/70 p-4 ${TONE[embed.tone ?? "blue"]}`}>
      <div className="font-display text-[0.95rem] font-medium tracking-tight text-paper">{embed.title}</div>
      {embed.description && (
        <p className="mt-1.5 whitespace-pre-line text-[0.8rem] leading-relaxed text-paper-dim">{embed.description}</p>
      )}
      {embed.code && (
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words border border-line bg-ink px-3 py-2 font-mono text-[0.75rem] text-paper">
          {embed.code}
        </pre>
      )}
      {embed.fields && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3 text-[0.78rem] sm:grid-cols-3">
          {embed.fields.map((f) => (
            <div key={f.name} className={f.inline ? "min-w-0" : "col-span-full min-w-0"}>
              <dt className="font-medium text-paper">{f.name}</dt>
              <dd className="mt-0.5 whitespace-pre-line break-words text-paper-dim">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {embed.footer && <div className="mt-3 text-[0.75rem] text-mute">{embed.footer}</div>}
    </div>
  );
}

const BUTTON: Record<string, string> = {
  primary: "bg-paper text-ink",
  success: "bg-accent text-ink",
  danger: "border border-line-strong text-paper",
  secondary: "border border-line-strong text-paper-dim",
};

export function Buttons({ buttons }: { buttons: NonNullable<MessageData["buttons"]> }) {
  return (
    <div className="mt-2 flex flex-wrap gap-2" aria-hidden>
      {buttons.map((b) => (
        <span key={b.label} className={`px-3 py-1.5 text-[0.75rem] font-medium ${BUTTON[b.style ?? "secondary"]}`}>
          {b.label}
        </span>
      ))}
    </div>
  );
}

/* ── Status card (the /status embed) ─────────────────────────────────────── */

export type StatusData = {
  name: string;
  online: boolean;
  version?: string | null;
  uptimeS?: number | null;
  address?: string | null;
  playersOnline: number;
  playersMax: number;
  playerNames: string[];
  tps?: number[] | null;
  mspt?: number | null;
  memUsedMb?: number | null;
  memMaxMb?: number | null;
  history?: { players: number[]; tps: number[] };
  footer?: string;
};

export function fmtUptime(s: number) {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return d ? `${d}d ${h}h ${m}m` : `${h}h ${m}m`;
}

export function StatusEmbed({ data }: { data: StatusData }) {
  const tps = data.tps ?? null;
  const mem = data.memUsedMb != null && data.memMaxMb ? data.memUsedMb / data.memMaxMb : null;
  return (
    <div className={`mt-1 border-l-2 bg-ink-3/70 p-4 ${data.online ? "border-paper" : "border-mute"}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="truncate font-display text-[1rem] font-medium tracking-tight">{data.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[0.75rem] text-paper-dim">
            {data.online ? (
              <span className="inline-flex items-center gap-1.5 text-accent">
                <i className="size-1.5 rounded-full bg-accent" /> Online
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-paper">
                <i className="size-1.5 rounded-full border border-paper" /> Offline
              </span>
            )}
            {data.version && (
              <>
                <span className="text-mute" aria-hidden>
                  ·
                </span>
                <span>{data.version}</span>
              </>
            )}
            {data.online && data.uptimeS != null && (
              <>
                <span className="text-mute" aria-hidden>
                  ·
                </span>
                <span className="tabular-nums">up {fmtUptime(data.uptimeS)}</span>
              </>
            )}
          </div>
          {data.address && (
            <div className="mt-2 inline-block max-w-full truncate border border-line bg-ink px-2 py-0.5 font-mono text-[0.75rem] text-paper-dim">
              {data.address}
            </div>
          )}
        </div>
        <Pixels grid={ICON} size={44} />
      </div>

      <div className="mt-4 text-[0.75rem]">
        <div className="font-medium text-paper">
          Players · {data.playersOnline}/{data.playersMax}
        </div>
        <div className="mt-0.5 truncate text-paper-dim">
          {data.playerNames.length ? data.playerNames.join(", ") : "Nobody online right now"}
        </div>
      </div>

      {data.online && (
        <dl className="mt-4 grid grid-cols-3 gap-3 text-[0.75rem]">
          <Field
            label="TPS"
            value={tps ? Math.min(20, tps[0]).toFixed(1) : "-"}
            sub={tps && tps.length >= 3 ? `5m ${tps[1].toFixed(1)} · 15m ${tps[2].toFixed(1)}` : ""}
          />
          <Field label="MSPT" value={data.mspt != null ? `${data.mspt.toFixed(1)} ms` : "-"} sub="50 ms = 20 TPS limit" />
          <Field
            label="Memory"
            value={
              data.memUsedMb != null && data.memMaxMb
                ? `${(data.memUsedMb / 1024).toFixed(1)} / ${(data.memMaxMb / 1024).toFixed(1)} GB`
                : "-"
            }
            sub={mem != null ? <Bar value={mem} /> : ""}
          />
        </dl>
      )}

      {data.history && data.history.players.length > 1 && <ActivityGraph {...data.history} />}

      {data.footer && (
        <div className="mt-3 flex items-center gap-2 font-mono text-[0.75rem] text-mute">
          <Seal size={12} /> {data.footer}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, sub }: { label: string; value: string; sub: ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="font-medium text-paper">{label}</dt>
      <dd className="mt-0.5 font-mono text-[0.8rem] tabular-nums text-paper [overflow-wrap:anywhere]">{value}</dd>
      <dd className="mt-1 font-mono text-[0.75rem] text-mute">{sub}</dd>
    </div>
  );
}

function Bar({ value }: { value: number }) {
  return (
    <span className="mt-1.5 block h-[3px] w-full bg-line">
      <span
        className="block h-full bg-paper transition-[width] duration-1000"
        style={{ width: `${Math.round(Math.min(1, Math.max(0, value)) * 100)}%` }}
      />
    </span>
  );
}

function toPath(values: number[], max: number, min: number, w: number, h: number) {
  const step = w / Math.max(1, values.length - 1);
  return values
    .map((v, i) => {
      const y = h - ((Math.min(max, Math.max(min, v)) - min) / (max - min)) * h;
      return `${i ? "L" : "M"}${(i * step).toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function ActivityGraph({ players, tps }: { players: number[]; tps: number[] }) {
  const W = 320;
  const H = 72;
  const top = Math.max(4, Math.ceil(Math.max(...players) * 1.25));
  const p = toPath(players, top, 0, W, H);
  const t = tps.length > 1 ? toPath(tps, 20.5, 15, W, H) : null;
  return (
    <figure className="mt-3 border border-line bg-ink/60 p-3" aria-hidden>
      <figcaption className="mb-2 flex flex-wrap items-center justify-between gap-x-3 font-mono text-[0.75rem] uppercase tracking-[0.16em] text-mute">
        <span>Last hour</span>
        <span className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <i className="inline-block h-px w-3 bg-paper" /> Players
          </span>
          <span className="flex items-center gap-1.5">
            <i className="inline-block h-px w-3 border-t border-dashed border-mute" /> TPS
          </span>
        </span>
      </figcaption>
      <svg viewBox={`0 -4 ${W} ${H + 8}`} className="block h-auto w-full">
        <defs>
          <linearGradient id="fillPlayers" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#edebe6" stopOpacity="0.18" />
            <stop offset="1" stopColor="#edebe6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} stroke="rgb(237 235 230 / .06)" />
        ))}
        <path d={`${p} L${W} ${H} L0 ${H} Z`} fill="url(#fillPlayers)" />
        {t && <path d={t} fill="none" stroke="#8a8781" strokeWidth="1" strokeDasharray="3 3" />}
        <path className="graph-line" pathLength={1} d={p} fill="none" stroke="#edebe6" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[0.75rem] text-mute">
        <span>−60m</span>
        <span>−30m</span>
        <span>now</span>
      </div>
    </figure>
  );
}

/* ── Example renderer for command docs ───────────────────────────────────── */

export const EXAMPLE_STATUS: StatusData = {
  name: "Hinoki SMP",
  online: true,
  version: "Paper 1.21.11",
  uptimeS: 2 * 86400 + 4 * 3600 + 12 * 60,
  address: "play.hinoki.gg",
  playersOnline: 6,
  playersMax: 20,
  playerNames: ["kiri_", "Aoi", "moss_block", "tetsu", "Ren", "nori"],
  tps: [19.9, 19.9, 19.9],
  mspt: 12.4,
  memUsedMb: 2190,
  memMaxMb: 6144,
  history: {
    players: [3, 3, 4, 4, 5, 4, 5, 6, 6, 7, 6, 6, 7, 8, 8, 7, 6, 7, 7, 6, 6, 7, 6, 6],
    tps: [20, 20, 19.9, 20, 20, 19.8, 20, 19.9, 18.6, 17.9, 19.4, 20, 20, 19.9, 20, 20, 19.7, 20, 20, 19.9, 20, 20, 19.9, 20],
  },
  footer: "MCBridge · updated just now",
};

export function ExampleMessages({ messages, channel }: { messages: MessageData[]; channel: string }) {
  return (
    <MockWindow channel={channel}>
      {messages.map((m, i) => {
        const body = (
          <>
            {m.text && <p className="text-[0.85rem] text-paper-dim">{m.text}</p>}
            {m.embed && <Embed embed={m.embed} />}
            {m.statusCard && <StatusEmbed data={EXAMPLE_STATUS} />}
            {m.buttons && <Buttons buttons={m.buttons} />}
          </>
        );
        return m.from === "bot" ? (
          <BotMessage key={i} usedBy={m.usedBy} ephemeral={m.ephemeral}>
            {body}
          </BotMessage>
        ) : (
          <Message key={i} author={m.from} usedBy={m.usedBy} ephemeral={m.ephemeral}>
            {body}
          </Message>
        );
      })}
    </MockWindow>
  );
}
