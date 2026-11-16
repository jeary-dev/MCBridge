"use client";

import { useEffect, useState } from "react";
import { Seal } from "./Logo";

/* ── Pixel art (original, greyscale) ─────────────────────────────────────── */

const SHADES = ["transparent", "#0e0e0f", "#2a2a2c", "#4d4c4a", "#7c7a75", "#b9b6ae", "#edebe6"];

// An original 8×8 player head: dark fringe, pale face, two eyes.
const HEAD = [
  "22222222",
  "22322232",
  "23555532",
  "55555555",
  "56166165",
  "55555555",
  "55433455",
  "45555554",
];

// Server icon: a mountain under a white sun.
const ICON = [
  "22222222",
  "22222662",
  "22222662",
  "22266222",
  "22655622",
  "26544562",
  "54433445",
  "43333334",
];

function Pixels({ grid, size, label }: { grid: string[]; size: number; label?: string }) {
  return (
    <span
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
      className="grid shrink-0 overflow-hidden"
      style={{
        width: size,
        height: size,
        gridTemplateColumns: "repeat(8, 1fr)",
        imageRendering: "pixelated",
        borderRadius: 2,
      }}
    >
      {grid.join("").split("").map((c, i) => (
        <span key={i} style={{ background: SHADES[Number(c)] }} />
      ))}
    </span>
  );
}

/* ── Graph data: players and TPS across the last hour ────────────────────── */

const PLAYERS = [3, 3, 4, 4, 5, 4, 5, 6, 6, 7, 6, 6, 7, 8, 8, 7, 6, 7, 7, 6, 6, 7, 6, 6];
const TPS = [20, 20, 19.9, 20, 20, 19.8, 20, 19.9, 18.6, 17.9, 19.4, 20, 20, 19.9, 20, 20, 19.7, 20, 20, 19.9, 20, 20, 19.9, 20];

function toPath(values: number[], max: number, min: number, w: number, h: number) {
  const step = w / (values.length - 1);
  return values
    .map((v, i) => {
      const x = i * step;
      const y = h - ((v - min) / (max - min)) * h;
      return `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function ActivityGraph() {
  const W = 320;
  const H = 72;
  const players = toPath(PLAYERS, 10, 0, W, H);
  const tps = toPath(TPS, 20.5, 15, W, H);
  return (
    <figure className="mt-3 border border-line bg-ink/60 p-3">
      <figcaption className="mb-2 flex items-center justify-between font-mono text-[0.6rem] uppercase tracking-[0.16em] text-mute">
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
      <svg viewBox={`0 -4 ${W} ${H + 8}`} className="block h-auto w-full" aria-hidden>
        <defs>
          <linearGradient id="fillPlayers" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#edebe6" stopOpacity="0.18" />
            <stop offset="1" stopColor="#edebe6" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1="0" x2={W} y1={H * f} y2={H * f} stroke="rgb(237 235 230 / .06)" />
        ))}
        <path d={`${players} L${W} ${H} L0 ${H} Z`} fill="url(#fillPlayers)" />
        <path d={tps} fill="none" stroke="#7c7a75" strokeWidth="1" strokeDasharray="3 3" />
        <path
          className="graph-line"
          pathLength={1}
          d={players}
          fill="none"
          stroke="#edebe6"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      <div className="mt-1 flex justify-between font-mono text-[0.58rem] text-faint">
        <span>−60m</span>
        <span>−30m</span>
        <span>now</span>
      </div>
    </figure>
  );
}

/* ── The mock window ─────────────────────────────────────────────────────── */

const START_UPTIME = 2 * 86400 + 4 * 3600 + 12 * 60;

function fmtUptime(s: number) {
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${d}d ${h}h ${m}m`;
}

export function StatusMock() {
  const [t, setT] = useState(0);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = window.setInterval(() => setT((n) => n + 1), 2400);
    return () => window.clearInterval(id);
  }, []);

  // Deterministic wobble so the server render and first client render match.
  const wobble = (seed: number, amp: number) => Math.sin(t * 1.7 + seed) * amp;
  const tps = Math.min(20, 19.93 + wobble(1, 0.07));
  const mspt = 12.4 + wobble(2, 1.6);
  const mem = 2.14 + wobble(3, 0.12) + (t % 6) * 0.015;
  const uptime = START_UPTIME + t * 60;

  return (
    <div className="relative" aria-label="Example of the MCBridge status card in a Discord channel" role="img">
      {/* window */}
      <div className="relative overflow-hidden border border-line-strong bg-ink-2 shadow-[0_40px_120px_-30px_rgb(0_0_0/0.9)]">
        <div className="flex items-center gap-3 border-b border-line px-4 py-3">
          <span className="flex gap-1.5" aria-hidden>
            <i className="size-2 rounded-full border border-line-strong" />
            <i className="size-2 rounded-full border border-line-strong" />
            <i className="size-2 rounded-full border border-line-strong" />
          </span>
          <span className="font-mono text-[0.72rem] text-paper-dim">
            <span className="text-mute">#</span> server-status
          </span>
          <span className="ml-auto flex items-center gap-2 font-mono text-[0.6rem] uppercase tracking-[0.18em] text-mute">
            <i className="pulse-dot size-1.5 rounded-full bg-accent" /> live
          </span>
        </div>

        <div className="space-y-5 p-4 sm:p-5">
          {/* bot message */}
          <div className="flex gap-3">
            <Seal size={34} />
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2 text-[0.8rem]">
                <span className="font-medium text-paper">MCBridge</span>
                <span className="border border-line-strong px-1 font-mono text-[0.55rem] uppercase tracking-wider text-paper-dim">
                  App
                </span>
                <span className="font-mono text-[0.62rem] text-faint">today at 21:04</span>
              </div>

              {/* embed */}
              <div className="mt-2 border-l-2 border-paper bg-ink-3/70 p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="font-display text-[1rem] font-medium tracking-tight">Hinoki SMP</div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 text-[0.75rem] text-paper-dim">
                      <span className="inline-flex items-center gap-1.5 text-accent">
                        <i className="size-1.5 rounded-full bg-accent" /> Online
                      </span>
                      <span className="text-faint">·</span>
                      <span>Paper 1.21.11</span>
                      <span className="text-faint">·</span>
                      <span className="tabular-nums">up {fmtUptime(uptime)}</span>
                    </div>
                    <div className="mt-2 inline-block border border-line bg-ink px-2 py-0.5 font-mono text-[0.7rem] text-paper-dim">
                      play.hinoki.gg
                    </div>
                  </div>
                  <Pixels grid={ICON} size={44} label="Server icon" />
                </div>

                <div className="mt-4 text-[0.72rem]">
                  <div className="font-medium text-paper">Players · 6/20</div>
                  <div className="mt-0.5 truncate text-paper-dim">kiri_, Aoi, moss_block, tetsu, Ren, nori</div>
                </div>

                <dl className="mt-4 grid grid-cols-3 gap-3 text-[0.72rem]">
                  <Field label="TPS" value={tps.toFixed(1)} sub="5m 19.9 · 15m 19.9" />
                  <Field label="MSPT" value={`${mspt.toFixed(1)} ms`} sub="50 ms = 20 TPS limit" />
                  <Field label="Memory" value={`${mem.toFixed(1)} / 6.0 GB`} sub={<Bar value={mem / 6} />} />
                </dl>

                <ActivityGraph />

                <div className="mt-3 flex items-center gap-2 font-mono text-[0.6rem] text-mute">
                  <Seal size={12} /> MCBridge 0.2.0 · updated just now
                </div>
              </div>
            </div>
          </div>

          {/* player chat message */}
          <div className="flex gap-3">
            <Pixels grid={HEAD} size={34} />
            <div className="min-w-0">
              <div className="flex items-baseline gap-2 text-[0.8rem]">
                <span className="font-medium text-paper">kiri_</span>
                <span className="border border-line-strong px-1 font-mono text-[0.55rem] uppercase tracking-wider text-paper-dim">
                  In game
                </span>
                <span className="font-mono text-[0.62rem] text-faint">today at 21:05</span>
              </div>
              <p className="mt-1 text-[0.85rem] text-paper-dim">
                anyone up for the nether trip tonight? bringing extra blocks
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, sub }: { label: string; value: string; sub: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <dt className="font-medium text-paper">{label}</dt>
      <dd className="mt-0.5 font-mono text-[0.8rem] tabular-nums text-paper transition-all">{value}</dd>
      <dd className="mt-1 truncate font-mono text-[0.58rem] text-mute">{sub}</dd>
    </div>
  );
}

function Bar({ value }: { value: number }) {
  return (
    <span className="mt-1.5 block h-[3px] w-full bg-line">
      <span
        className="block h-full bg-paper transition-[width] duration-1000"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </span>
  );
}
