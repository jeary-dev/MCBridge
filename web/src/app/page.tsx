import type { Metadata } from "next";
import { DOWNLOAD_URL, INVITE_URL, SUPPORT_INVITE } from "@/config";
import { pageMeta } from "@/lib/meta";
import { Button } from "@/components/Button";
import { Reveal } from "@/components/Reveal";
import { SectionHead } from "@/components/SectionHead";
import { StatusMock } from "@/components/StatusMock";
import { BridgeDiagram } from "@/components/BridgeDiagram";
import { LinkConsole } from "@/components/LinkConsole";
import { COMMANDS, COMPARE_COLUMNS, COMPARE_ROWS, FAQ, FEATURES, STEPS, type Cell } from "@/content/home";

export const metadata: Metadata = pageMeta({
  title: "MCBridge · Your Minecraft server, live in Discord",
  description:
    "Connect your Minecraft server to Discord. Live stats, alerts, chat and more, from a Paper plugin and a bot we host. Nothing to host, no port forwarding.",
  path: "/",
  absoluteTitle: true,
});

const LIVE_POINTS = [
  { title: "The real status card", body: "TPS, MSPT, memory and players, straight from the server, refreshed every 10 seconds." },
  { title: "The last hour", body: "Players and TPS over the last hour, with the line where a lag alert would fire." },
  { title: "Chat both ways", body: "In-game chat, joins and deaths as they happen. Say hi in our Discord and it shows up in-game." },
];

export default function Home() {
  return (
    <>
      <Hero />
      <Marquee />

      {/* 01 · Why */}
      <section className="mx-auto max-w-[1240px] px-4 py-28 sm:px-6 md:py-40 lg:px-10">
        <SectionHead
          index="01"
          label="How it works"
          kanji="仕組み"
          title={
            <>
              Status bots ping your server.
              <span className="text-mute"> MCBridge runs inside it.</span>
            </>
          }
          intro="So it knows what's really going on. The plugin connects out to MCBridge, and MCBridge talks to Discord. Nothing to host, no port forwarding."
        />
        <Reveal delay={150}>
          <BridgeDiagram />
        </Reveal>
      </section>

      {/* 02 · Features */}
      <section id="features" className="mx-auto max-w-[1240px] px-4 pb-28 sm:px-6 md:pb-40 lg:px-10">
        <SectionHead
          index="02"
          label="Features"
          kanji="機能"
          title="Everything your community asks about, answered in Discord."
          intro="Stats, alerts, chat, whitelist, recaps and more. Set up with menus, not config files."
        />
        <ul className="grid gap-px border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f, i) => (
            <Reveal
              as="li"
              key={f.title}
              delay={(i % 4) * 80}
              className="group relative flex min-h-[15rem] flex-col bg-ink p-7 transition-colors duration-700 hover:bg-ink-3"
            >
              <span className="font-mono text-[0.75rem] tracking-[0.2em] text-mute transition-colors duration-500 group-hover:text-paper">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-8 font-display text-[1.3rem] font-medium leading-tight tracking-[-0.02em]">
                {f.title}
              </h3>
              <p className="mt-3 text-[0.92rem] leading-relaxed text-paper-dim">{f.body}</p>
              <span className="mt-auto pt-8 font-mono text-[0.75rem] text-mute">{f.tag}</span>
              <span
                aria-hidden
                className="absolute inset-x-0 top-0 h-px origin-left scale-x-0 bg-paper transition-transform duration-700 ease-[cubic-bezier(.16,1,.3,1)] group-hover:scale-x-100"
              />
            </Reveal>
          ))}
          {/* 10 cards in 4 columns leave 2 empty cells; fill them with ink so the hairline grid stays clean */}
          {FEATURES.length % 4 !== 0 && (
            <li
              aria-hidden
              className="hidden bg-ink lg:block"
              style={{ gridColumn: `span ${4 - (FEATURES.length % 4)}` }}
            />
          )}
        </ul>
      </section>

      {/* 03 · Compare */}
      <section id="compare" className="mx-auto max-w-[1240px] px-4 pb-28 sm:px-6 md:pb-40 lg:px-10">
        <SectionHead
          index="03"
          label="Compare"
          kanji="比較"
          title="Not another status bot."
          intro="Pinging from the outside tells you online or offline. Running inside the server tells you why."
        />
        <p className="mb-4 font-mono text-[0.75rem] uppercase tracking-[0.2em] text-mute sm:hidden" aria-hidden>
          Scroll to compare →
        </p>
        <Reveal className="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0">
          <table className="w-full min-w-[640px] border-collapse text-left text-[0.92rem]">
            <caption className="sr-only">MCBridge compared with status bots and self-hosted chat plugins</caption>
            <thead>
              <tr className="border-b border-line-strong">
                <th scope="col" className="w-[40%] py-5 pr-4 font-mono text-[0.75rem] font-normal uppercase tracking-[0.2em] text-mute">
                  Feature
                </th>
                {COMPARE_COLUMNS.map((c, i) => (
                  <th
                    key={c}
                    scope="col"
                    className={`px-4 py-5 text-center font-display text-[0.95rem] font-medium tracking-tight ${
                      i === 0 ? "bg-paper text-ink" : "text-paper-dim"
                    }`}
                  >
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPARE_ROWS.map((r) => (
                <tr key={r.label} className="group border-b border-line transition-colors hover:bg-paper/[0.025]">
                  <th scope="row" className="py-4 pr-4 font-normal text-paper-dim group-hover:text-paper">
                    {r.label}
                  </th>
                  {r.cells.map((c, i) => (
                    <td key={i} className={`px-4 py-4 text-center ${i === 0 ? "bg-paper/[0.04]" : ""}`}>
                      <Mark value={c} strong={i === 0} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </Reveal>
      </section>

      {/* 04 · Live demo */}
      <section id="live" className="mx-auto max-w-[1240px] px-4 pb-28 sm:px-6 md:pb-40 lg:px-10">
        <SectionHead
          index="04"
          label="Live demo"
          kanji="実況"
          title="See it live."
          intro="Our demo server runs MCBridge right now. Watch its status, players and TPS, and chat with it from our Discord."
        />
        <Reveal className="grid gap-px border border-line bg-line md:grid-cols-3">
          {LIVE_POINTS.map((p, i) => (
            <div key={p.title} className="bg-ink p-7">
              <span className="font-mono text-[0.75rem] tracking-[0.2em] text-mute">{String(i + 1).padStart(2, "0")}</span>
              <h3 className="mt-6 font-display text-[1.2rem] font-medium tracking-[-0.02em]">{p.title}</h3>
              <p className="mt-2 text-[0.92rem] leading-relaxed text-paper-dim">{p.body}</p>
            </div>
          ))}
        </Reveal>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Button href="/demo">See it live</Button>
          <Button href={SUPPORT_INVITE} variant="ghost">
            Talk to it in our Discord
          </Button>
        </div>
      </section>

      {/* 05 · Setup */}
      <section id="setup" className="mx-auto max-w-[1240px] px-4 pb-28 sm:px-6 md:pb-40 lg:px-10">
        <SectionHead
          index="05"
          label="Setup"
          kanji="手順"
          title="Three steps. About two minutes."
          intro="Add the bot, run /setup, type the code into your server console. Then you get live stats, alerts, chat and more."
        />
        <div className="grid gap-12 lg:grid-cols-12">
          <ol className="lg:col-span-6">
            {STEPS.map((s, i) => (
              <Reveal as="li" key={s.title} delay={i * 120} className="group grid grid-cols-[4.5rem_1fr] gap-6 border-t border-line py-9 last:border-b">
                <span
                  lang="ja"
                  aria-hidden
                  className="font-jp text-[3.2rem] leading-none text-mute transition-colors duration-700 group-hover:text-paper"
                >
                  {s.kanji}
                </span>
                <div>
                  <span className="font-mono text-[0.75rem] uppercase tracking-[0.2em] text-mute">Step {i + 1}</span>
                  <h3 className="mt-2 font-display text-[1.45rem] font-medium tracking-[-0.02em]">{s.title}</h3>
                  <p className="mt-2 max-w-md leading-relaxed text-paper-dim">{s.body}</p>
                </div>
              </Reveal>
            ))}
          </ol>
          <div className="lg:col-span-5 lg:col-start-8">
            <Reveal delay={200} className="lg:sticky lg:top-28">
              <LinkConsole />
              <div className="mt-6 flex flex-col gap-3 sm:flex-row">
                <Button href={INVITE_URL}>Add to Discord</Button>
                <Button href={DOWNLOAD_URL} variant="ghost">
                  Download the plugin
                </Button>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* 06 · FAQ */}
      <section id="faq" className="mx-auto max-w-[1240px] px-4 pb-28 sm:px-6 md:pb-40 lg:px-10">
        <SectionHead index="06" label="FAQ" kanji="質問" title="Questions, answered." />
        <Reveal className="border-t border-line-strong lg:ml-[calc(100%/12*4)]">
          {FAQ.map((f) => (
            <details key={f.q} className="group border-b border-line">
              <summary className="flex cursor-pointer items-center justify-between gap-6 py-6 font-display text-[1.12rem] tracking-[-0.01em] transition-colors hover:text-white">
                {f.q}
                <span
                  aria-hidden
                  className="faq-icon relative block size-3 shrink-0 before:absolute before:left-0 before:top-1/2 before:h-px before:w-3 before:bg-paper after:absolute after:left-0 after:top-1/2 after:h-px after:w-3 after:rotate-90 after:bg-paper"
                />
              </summary>
              <p className="max-w-2xl pb-7 leading-relaxed text-paper-dim">{f.a}</p>
            </details>
          ))}
        </Reveal>
      </section>

      <FinalCta />
    </>
  );
}

/* ── Hero ────────────────────────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="relative isolate overflow-hidden pt-32 md:pt-40">
      {/* soft light behind the card */}
      <div
        aria-hidden
        className="absolute right-[-10%] top-[8%] -z-10 size-[46rem] rounded-full opacity-60 blur-3xl"
        style={{ background: "radial-gradient(circle, rgb(237 235 230 / .07), transparent 62%)" }}
      />
      <Enso />
      {/* vertical text along the edge */}
      <p
        lang="ja"
        aria-hidden
        className="absolute right-4 top-36 hidden font-jp text-[0.8rem] tracking-[0.6em] text-faint [writing-mode:vertical-rl] xl:block"
      >
        サーバーとディスコードを結ぶ橋
      </p>

      <div className="mx-auto grid max-w-[1240px] items-center gap-16 px-4 pb-24 sm:px-6 md:pb-32 lg:grid-cols-12 lg:px-10">
        <div className="lg:col-span-6">
          <p className="mb-8 flex items-center gap-3 font-mono text-[0.75rem] uppercase tracking-[0.22em] text-mute">
            <span aria-hidden className="inline-block h-px w-8 bg-mute" />
            Minecraft × Discord
          </p>
          {/* One heading, read once. Line breaks are visual only; the spaces keep the accessible name intact. */}
          <h1 className="font-display text-[clamp(2.5rem,5.6vw,4.4rem)] font-medium leading-[1] tracking-[-0.045em]">
            <span className="block">Your Minecraft </span>
            <span className="block">server, live </span>
            <span className="block text-paper-dim">in Discord.</span>
          </h1>
          <p className="mt-8 max-w-[34rem] text-[1.1rem] leading-relaxed text-paper-dim">
            A Paper plugin and a bot that actually talk to each other. Add the bot, run /setup, type the
            code into your server console. Then get live stats, alerts, chat and more. Nothing to host,
            no port forwarding.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button href={INVITE_URL}>Add to Discord</Button>
            <Button href={DOWNLOAD_URL} variant="ghost">
              Download the plugin
            </Button>
          </div>
          <p className="mt-8 font-mono text-[0.75rem] tracking-wide text-mute">
            Paper 1.21 · Java 21 · Open source (AGPL-3.0)
          </p>
        </div>

        <div className="lg:col-span-6 lg:pl-6">
          <StatusMock />
        </div>
      </div>
    </section>
  );
}

function Enso() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 400 400"
      className="enso pointer-events-none absolute right-[-6rem] top-12 -z-10 hidden w-[44rem] opacity-[0.07] md:block"
    >
      <defs>
        <filter id="brush">
          <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="7" />
          <feDisplacementMap in="SourceGraphic" scale="9" />
        </filter>
      </defs>
      <g filter="url(#brush)" fill="none" stroke="#edebe6" strokeLinecap="round">
        <path pathLength={1} strokeWidth="22" d="M 232 58 C 330 74 372 180 334 260 C 294 344 176 368 104 312 C 40 262 38 160 92 104 C 124 72 160 60 196 58" />
        <path pathLength={1} strokeWidth="6" d="M 196 58 C 210 57 222 60 236 64" />
      </g>
    </svg>
  );
}

/* ── Command marquee ─────────────────────────────────────────────────────── */

function Marquee() {
  const items = [...COMMANDS, ...COMMANDS];
  return (
    <div className="marquee overflow-hidden border-y border-line py-5" aria-hidden>
      <div className="marquee-track flex w-max gap-12 font-mono text-[0.85rem] text-mute">
        {items.map((c, i) => (
          <span key={i} className="flex items-center gap-12 whitespace-nowrap">
            <span className="transition-colors hover:text-paper">{c}</span>
            <span className="text-faint">◇</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Compare marks ───────────────────────────────────────────────────────── */

function Mark({ value, strong }: { value: Cell; strong?: boolean }) {
  if (value === true)
    return (
      <span
        role="img"
        aria-label="Yes"
        className={`text-[1.05rem] leading-none ${strong ? "text-paper" : "text-paper-dim"}`}
      >
        ✓
      </span>
    );
  if (value === false)
    return (
      <span role="img" aria-label="No" className="text-mute">
        —
      </span>
    );
  return <span className="font-mono text-[0.75rem] uppercase tracking-wider text-paper-dim">{value}</span>;
}

/* ── Final call to action ────────────────────────────────────────────────── */

function FinalCta() {
  return (
    <section className="relative isolate overflow-hidden border-t border-line">
      <span
        lang="ja"
        aria-hidden
        className="pointer-events-none absolute -bottom-[0.18em] right-[-0.04em] -z-10 select-none font-jp text-[clamp(16rem,42vw,34rem)] font-extrabold leading-none text-transparent [-webkit-text-stroke:1px_rgb(237_235_230/0.09)]"
      >
        橋
      </span>
      <div className="mx-auto max-w-[1240px] px-4 py-28 sm:px-6 md:py-44 lg:px-10">
        <Reveal>
          <p className="mb-8 flex items-center gap-3 font-mono text-[0.75rem] uppercase tracking-[0.22em] text-mute">
            <span aria-hidden className="inline-block h-px w-8 bg-mute" />
            Get started
          </p>
          <h2 className="max-w-4xl font-display text-[clamp(2.4rem,6vw,5rem)] font-medium leading-[1] tracking-[-0.045em]">
            Build the bridge.
            <br />
            <span className="text-paper-dim">Your players are already in Discord.</span>
          </h2>
          <p className="mt-8 max-w-lg text-[1.05rem] leading-relaxed text-paper-dim">
            Add the bot, drop the plugin in, link them with one code. Free and open source.
          </p>
          <div className="mt-10 flex flex-col gap-3 sm:flex-row">
            <Button href={INVITE_URL}>Add to Discord</Button>
            <Button href={DOWNLOAD_URL} variant="ghost">
              Download the plugin
            </Button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
