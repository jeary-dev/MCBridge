"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DEMO_URL } from "@/config";
import { BotMessage, MockWindow, StatusEmbed, type StatusData } from "../discord/Mock";

/* ── API shape (docs/PROTOCOL.md → "Live demo") ─────────────────────────── */

type Player = { name: string; uuid?: string | null };
type DemoEvent = {
  ts: number;
  type: "chat" | "discord_chat" | "join" | "leave" | "death" | "advancement";
  player: Player | null;
  text: string;
};
type Demo = {
  name: string;
  online: boolean;
  address: string | null;
  version: string | null;
  players: { online: number; max: number; list: Player[] };
  tps: number[] | null;
  mspt: number | null;
  memory: { used_mb: number; max_mb: number } | null;
  uptime_s: number | null;
  lagging: boolean;
  history: { ts: number; players: number; tps: number }[];
  events: DemoEvent[];
  updated_at: number;
};

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: Demo; stale: boolean }
  | { kind: "unavailable"; reason: string };

const POLL_MS = 10_000;
const MAX_BACKOFF_MS = 120_000;
const LAG_TPS = 15;

/** Seconds or milliseconds → milliseconds. */
const ms = (ts: number) => (ts < 1e12 ? ts * 1000 : ts);

function isDemo(x: unknown): x is Demo {
  const d = x as Demo;
  return !!d && typeof d.name === "string" && typeof d.online === "boolean" && !!d.players && Array.isArray(d.history) && Array.isArray(d.events);
}

/* ── Polling ────────────────────────────────────────────────────────────── */

function useDemo() {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [retryIn, setRetryIn] = useState<number | null>(null);
  const retryRef = useRef<() => void>(() => {});

  useEffect(() => {
    let failures = 0;
    let timer: number | undefined;
    let inflight: AbortController | null = null;
    let stopped = false;

    const schedule = (delay: number) => {
      window.clearTimeout(timer);
      if (!stopped && !document.hidden) timer = window.setTimeout(poll, delay);
    };

    async function poll() {
      window.clearTimeout(timer);
      if (stopped || document.hidden) return; // resumes on visibilitychange
      inflight?.abort();
      const ctrl = new AbortController();
      inflight = ctrl;
      const timeout = window.setTimeout(() => ctrl.abort(), 8000);
      let next = POLL_MS;
      try {
        const res = await fetch(DEMO_URL, { signal: ctrl.signal, cache: "no-store" });
        if (res.status === 404) {
          failures = 0;
          setState({ kind: "unavailable", reason: "The demo server isn't set up right now." });
          next = MAX_BACKOFF_MS;
        } else if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        } else {
          const json: unknown = await res.json();
          if (!isDemo(json)) throw new Error("bad response");
          failures = 0;
          setState({ kind: "ok", data: json, stale: false });
        }
        setRetryIn(null);
      } catch {
        if (stopped || inflight !== ctrl) return; // unmounted, hidden or superseded
        failures += 1;
        next = Math.min(MAX_BACKOFF_MS, POLL_MS * 2 ** failures);
        setRetryIn(Math.round(next / 1000));
        const gaveUp = failures >= 2;
        setState((s) =>
          s.kind === "ok"
            ? { ...s, stale: true }
            : gaveUp
              ? { kind: "unavailable", reason: "We can't reach the demo right now." }
              : s,
        );
      } finally {
        window.clearTimeout(timeout);
      }
      if (inflight === ctrl) schedule(next);
    }

    const onVisibility = () => {
      if (document.hidden) {
        window.clearTimeout(timer);
        inflight?.abort();
        inflight = null;
      } else {
        poll();
      }
    };

    retryRef.current = () => {
      failures = 0;
      poll();
    };
    schedule(0);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      inflight?.abort();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  const retry = useCallback(() => retryRef.current(), []);
  return { state, retryIn, retry };
}

/* ── Charts ─────────────────────────────────────────────────────────────── */

type Point = { t: number; v: number };

function niceMax(v: number) {
  if (v <= 4) return 4;
  const step = v <= 10 ? 2 : v <= 25 ? 5 : v <= 50 ? 10 : 25;
  return Math.ceil(v / step) * step;
}

function Chart({
  title,
  summary,
  points,
  min,
  max,
  ticks,
  unit,
  lag,
  now,
}: {
  title: string;
  summary: string;
  points: Point[];
  min: number;
  max: number;
  ticks: number[];
  unit: string;
  lag?: number;
  now: number;
}) {
  // The SVG stretches to the box; labels are HTML so they stay readable at any width.
  const W = 1000;
  const H = 300;
  const start = now - 3600_000;
  const x = (t: number) => ((t - start) / 3600_000) * W;
  const pct = (v: number) => ((Math.min(max, Math.max(min, v)) - min) / (max - min)) * 100;
  const y = (v: number) => H - (pct(v) / 100) * H;
  const pts = points.filter((p) => p.t >= start);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)} ${y(p.v).toFixed(1)}`).join(" ");
  const titleId = `chart-${title.toLowerCase().replace(/\W+/g, "-")}`;
  const label = "font-mono text-[0.75rem] text-mute";

  return (
    <figure className="border border-line bg-ink-2 p-4">
      <figcaption className="mb-3 flex items-baseline justify-between gap-3">
        <span className="font-mono text-[0.75rem] uppercase tracking-[0.16em] text-paper">{title}</span>
        <span className={label}>last hour</span>
      </figcaption>
      <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2">
        {/* y axis */}
        <div aria-hidden className="relative w-6">
          {ticks.map((t) => (
            <span key={t} className={`${label} absolute right-0 -translate-y-1/2 leading-none`} style={{ top: `${100 - pct(t)}%` }}>
              {t}
            </span>
          ))}
        </div>
        <div className="relative h-32 sm:h-36">
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            className="absolute inset-0 h-full w-full overflow-visible"
            role="img"
            aria-labelledby={titleId}
          >
            <title id={titleId}>{summary}</title>
            {ticks.map((t) => (
              <line key={t} x1={0} x2={W} y1={y(t)} y2={y(t)} stroke="rgb(237 235 230 / .08)" vectorEffect="non-scaling-stroke" />
            ))}
            {lag !== undefined && (
              <line
                x1={0}
                x2={W}
                y1={y(lag)}
                y2={y(lag)}
                stroke="#edebe6"
                strokeOpacity=".55"
                strokeDasharray="4 4"
                vectorEffect="non-scaling-stroke"
              />
            )}
            {pts.length > 1 && (
              <>
                <path d={`${line} L${x(pts[pts.length - 1].t)} ${H} L${x(pts[0].t)} ${H} Z`} fill="rgb(237 235 230 / .07)" />
                <path
                  d={line}
                  fill="none"
                  stroke="#edebe6"
                  strokeWidth="1.5"
                  strokeLinejoin="round"
                  vectorEffect="non-scaling-stroke"
                />
              </>
            )}
          </svg>
          {lag !== undefined && (
            <span
              aria-hidden
              className="absolute right-0 -translate-y-full pb-0.5 font-mono text-[0.75rem] leading-none text-paper-dim"
              style={{ top: `${100 - pct(lag)}%` }}
            >
              lag &lt; {lag}
            </span>
          )}
          {pts.length <= 1 && <p className={`${label} absolute inset-0 grid place-items-center`}>Not enough data yet</p>}
        </div>
        {/* x axis */}
        <div />
        <div aria-hidden className={`${label} mt-2 flex justify-between`}>
          <span>−60m</span>
          <span>−30m</span>
          <span>now</span>
        </div>
      </div>
      <p className="sr-only">Values in {unit}.</p>
    </figure>
  );
}

/* ── Feed ───────────────────────────────────────────────────────────────── */

function Head({ player, size = 28 }: { player: Player | null; size?: number }) {
  if (player?.uuid) {
    return (
      <Image
        src={`https://mc-heads.net/avatar/${player.uuid}/32`}
        alt=""
        width={size}
        height={size}
        unoptimized
        className="shrink-0 self-start bg-ink-3 [image-rendering:pixelated]"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <span
      aria-hidden
      className="grid shrink-0 self-start place-items-center rounded-full bg-ink-3 font-display text-[0.75rem] text-paper-dim ring-1 ring-line-strong"
      style={{ width: size, height: size }}
    >
      {(player?.name ?? "?").replace(/[^a-z0-9]/gi, "").charAt(0).toUpperCase() || "?"}
    </span>
  );
}

const clock = (ts: number) => new Date(ms(ts)).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function EventLine({ e }: { e: DemoEvent }) {
  const name = e.player?.name ?? "Someone";
  let body: React.ReactNode;
  switch (e.type) {
    case "chat":
      body = (
        <>
          <span className="font-medium text-paper">{name}</span> <span className="text-paper-dim">{e.text}</span>
        </>
      );
      break;
    case "discord_chat":
      body = (
        <>
          <span className="mr-1.5 border border-line-strong px-1 font-mono text-[0.75rem] uppercase tracking-wider text-paper-dim">
            Discord
          </span>
          <span className="font-medium text-paper">{name}</span> <span className="text-paper-dim">{e.text}</span>
        </>
      );
      break;
    case "join":
      body = <span className="text-accent">{name} joined the server</span>;
      break;
    case "leave":
      body = <span className="text-paper-dim">{name} left the server</span>;
      break;
    case "death":
      body = <span className="text-paper-dim">{e.text || `${name} died`}</span>;
      break;
    case "advancement":
      body = (
        <span className="text-paper-dim">
          {name} made the advancement <span className="text-paper">{e.text}</span>
        </span>
      );
      break;
    default:
      body = <span className="text-paper-dim">{e.text}</span>;
  }
  return (
    <li className="flex gap-3 py-2">
      <Head player={e.player} />
      <div className="min-w-0 flex-1 text-[0.88rem] leading-snug [overflow-wrap:anywhere]">
        {body}
        <span className="ml-2 font-mono text-[0.75rem] text-mute">{clock(e.ts)}</span>
      </div>
    </li>
  );
}

function Feed({ events }: { events: DemoEvent[] }) {
  const box = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  useEffect(() => {
    const el = box.current;
    if (el && pinned.current) el.scrollTop = el.scrollHeight;
  }, [events]);
  return (
    <div
      ref={box}
      tabIndex={0}
      role="region"
      aria-label="Live chat and player feed"
      onScroll={(e) => {
        const el = e.currentTarget;
        pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      }}
      className="max-h-[26rem] min-h-[12rem] overflow-y-auto px-4"
    >
      {events.length === 0 ? (
        <p className="py-10 text-center text-[0.9rem] text-mute">Nothing yet. Chat, joins and deaths show up here.</p>
      ) : (
        <ol role="log" aria-live="polite" className="divide-y divide-line">
          {events.map((e, i) => (
            <EventLine key={`${e.ts}-${e.type}-${e.player?.name ?? ""}-${i}`} e={e} />
          ))}
        </ol>
      )}
    </div>
  );
}

/* ── Page body ──────────────────────────────────────────────────────────── */

function Panel({ title, children, aside }: { title: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <section aria-label={title} className="border border-line-strong bg-ink-2">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="font-mono text-[0.75rem] uppercase tracking-[0.16em] text-paper">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

function Notice({ title, children, busy = false }: { title: string; children: React.ReactNode; busy?: boolean }) {
  return (
    <div role="status" aria-busy={busy} className="border border-line-strong bg-ink-2 p-8 text-center sm:p-12">
      {busy && <span aria-hidden className="pulse-dot mx-auto mb-5 block size-2 rounded-full bg-accent" />}
      <p className="font-display text-[1.3rem] font-medium tracking-tight">{title}</p>
      <div className="mx-auto mt-3 max-w-md text-paper-dim">{children}</div>
    </div>
  );
}

export function LiveDemo() {
  const { state, retryIn, retry } = useDemo();

  const view = useMemo(() => {
    if (state.kind !== "ok") return null;
    const d = state.data;
    const players: Point[] = d.history.map((h) => ({ t: ms(h.ts), v: h.players }));
    const tps: Point[] = d.history.map((h) => ({ t: ms(h.ts), v: h.tps }));
    const pMax = niceMax(Math.max(4, d.players.online, ...players.map((p) => p.v)));
    const status: StatusData = {
      name: d.name,
      online: d.online,
      version: d.version,
      uptimeS: d.uptime_s,
      address: d.address,
      playersOnline: d.players.online,
      playersMax: d.players.max,
      playerNames: d.players.list.map((p) => p.name),
      tps: d.tps,
      mspt: d.mspt,
      memUsedMb: d.memory?.used_mb ?? null,
      memMaxMb: d.memory?.max_mb ?? null,
      history: { players: players.map((p) => p.v), tps: tps.map((p) => p.v) },
      footer: `MCBridge · updated ${clock(d.updated_at)}`,
    };
    const tpsVals = tps.map((p) => p.v);
    const lagPoints = tpsVals.filter((v) => v < LAG_TPS).length;
    return {
      d,
      // The chart's "now" is the server's clock, so the axis lines up with the samples.
      now: ms(d.updated_at),
      status,
      players,
      tps,
      pMax,
      playersSummary: players.length
        ? `Players over the last hour: ${d.players.online} now, peak ${Math.max(...players.map((p) => p.v))}, low ${Math.min(...players.map((p) => p.v))}.`
        : "Players over the last hour: no data yet.",
      tpsSummary: tpsVals.length
        ? `TPS over the last hour: lowest ${Math.min(...tpsVals).toFixed(1)}, average ${(tpsVals.reduce((a, b) => a + b, 0) / tpsVals.length).toFixed(1)}. ${
            lagPoints ? `Below the lag line (15) in ${lagPoints} samples.` : "Never below the lag line (15)."
          }`
        : "TPS over the last hour: no data yet.",
    };
  }, [state]);

  if (state.kind === "loading") {
    return (
      <Notice title="Connecting to the demo server…" busy>
        <p>Fetching live status, players and chat.</p>
      </Notice>
    );
  }

  if (state.kind === "unavailable" || !view) {
    return (
      <Notice title="The live demo is unavailable">
        <p>{state.kind === "unavailable" ? state.reason : ""} Try again in a little while.</p>
        <button
          type="button"
          onClick={retry}
          className="mt-6 border border-line-strong px-4 py-2 text-[0.9rem] text-paper transition-colors hover:border-paper"
        >
          Try again
        </button>
      </Notice>
    );
  }

  const { d } = view;
  return (
    <div className="space-y-6">
      {(state.stale || !d.online || d.lagging) && (
        <div role="status" className="border-l-2 border-paper bg-ink-2 px-4 py-3 text-[0.92rem] text-paper-dim">
          {state.stale ? (
            <>
              Lost connection to the demo. Showing the last update{retryIn ? `, retrying in ${retryIn}s` : ""}.
            </>
          ) : !d.online ? (
            <>The demo server is offline right now. In your Discord, MCBridge would post a crash or stop alert.</>
          ) : (
            <>The demo server is lagging (TPS below 15). This is when MCBridge posts a lag alert with diagnostics.</>
          )}
        </div>
      )}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div>
          <MockWindow channel="server-status" live={d.online && !state.stale}>
            <BotMessage time={`today at ${clock(d.updated_at)}`}>
              <StatusEmbed data={view.status} />
            </BotMessage>
          </MockWindow>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)] content-start gap-6">
          <Chart
            title="Players"
            summary={view.playersSummary}
            points={view.players}
            min={0}
            max={view.pMax}
            ticks={[0, view.pMax / 2, view.pMax]}
            unit="players"
            now={view.now}
          />
          <Chart
            title="TPS"
            summary={view.tpsSummary}
            points={view.tps}
            min={0}
            max={20}
            ticks={[0, 10, 20]}
            unit="ticks per second"
            lag={LAG_TPS}
            now={view.now}
          />
        </div>
      </div>

      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
        <Panel title={`Online · ${d.players.online}/${d.players.max}`}>
          {d.players.list.length ? (
            <ul className="divide-y divide-line px-4">
              {d.players.list.map((p) => (
                <li key={p.uuid ?? p.name} className="flex items-center gap-3 py-2.5">
                  <Head player={p} size={32} />
                  <span className="min-w-0 truncate text-[0.92rem] text-paper">{p.name}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="px-4 py-8 text-center text-[0.9rem] text-mute">Nobody online right now.</p>
          )}
        </Panel>
        <Panel
          title="Chat & feed"
          aside={<span className="font-mono text-[0.75rem] text-mute">last {d.events.length}</span>}
        >
          <Feed events={d.events} />
        </Panel>
      </div>
    </div>
  );
}
