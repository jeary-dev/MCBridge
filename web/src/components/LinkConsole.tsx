"use client";

import { useEffect, useRef, useState } from "react";

const COMMAND = "mcbridge link K7PQ2X";
const OUTPUT = [
  "MCBridge: linking...",
  'MCBridge: linked as "Hinoki SMP" - connecting to Discord!',
  "[MCBridge] Connected to the mcbridge bot as srv_7Q2xK9",
];

/** A server console that types the link command once it scrolls into view. */
export function LinkConsole() {
  const ref = useRef<HTMLDivElement>(null);
  const [typed, setTyped] = useState(0);
  const [lines, setLines] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const instant = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const timers: number[] = [];
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return;
        io.disconnect();
        if (instant) {
          timers.push(
            window.setTimeout(() => {
              setTyped(COMMAND.length);
              setLines(OUTPUT.length);
            }, 0),
          );
          return;
        }
        for (let i = 1; i <= COMMAND.length; i++) {
          timers.push(window.setTimeout(() => setTyped(i), 500 + i * 55 + Math.random() * 40));
        }
        const done = 500 + COMMAND.length * 60 + 450;
        OUTPUT.forEach((_, i) => timers.push(window.setTimeout(() => setLines(i + 1), done + i * 650)));
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      timers.forEach(clearTimeout);
    };
  }, []);

  const typing = typed < COMMAND.length;

  return (
    <div
      ref={ref}
      className="border border-line-strong bg-ink-2 font-mono text-[0.78rem] leading-relaxed"
      aria-label={`Server console: ${COMMAND}`}
    >
      <div className="flex items-center justify-between border-b border-line px-4 py-2.5 text-[0.75rem] uppercase tracking-[0.18em] text-mute">
        <span>server console</span>
        <span>paper 1.21</span>
      </div>
      <div className="min-h-[9.5rem] p-4" aria-hidden>
        <div className="text-faint">[21:02:11 INFO]: Done (4.218s)! For help, type &quot;help&quot;</div>
        <div className="mt-1 text-paper">
          <span className="text-mute">&gt; </span>
          {COMMAND.slice(0, typed)}
          {(typing || lines === OUTPUT.length) && <span className="blink ml-px inline-block h-[1.05em] w-[0.55em] translate-y-[2px] bg-paper" />}
        </div>
        {OUTPUT.slice(0, lines).map((l, i) => (
          <div
            key={l}
            className={`fade-in ${i === OUTPUT.length - 1 ? "text-paper" : "text-paper-dim"}`}
          >
            {l}
          </div>
        ))}
      </div>
    </div>
  );
}
