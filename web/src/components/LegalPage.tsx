import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

type Props = {
  kanji: string;
  label: string;
  title: string;
  updated: string;
  children: ReactNode;
};

export function LegalPage({ kanji, label, title, updated, children }: Props) {
  return (
    <div className="mx-auto max-w-[1240px] px-4 pb-32 pt-36 sm:px-6 md:pt-44 lg:px-10">
      <div className="grid gap-12 lg:grid-cols-12">
        <aside className="lg:col-span-3">
          <div className="lg:sticky lg:top-28">
            <p className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-mute">{label}</p>
            <span lang="ja" aria-hidden className="mt-6 hidden font-jp text-6xl leading-none text-faint lg:block">
              {kanji}
            </span>
          </div>
        </aside>
        <article className="lg:col-span-8 lg:col-start-5">
          <h1 className="fade-in font-display text-[clamp(2.4rem,5vw,4rem)] font-medium leading-none tracking-[-0.04em]">
            {title}
          </h1>
          <p className="fade-in mt-5 font-mono text-[0.72rem] uppercase tracking-[0.18em] text-mute" style={{ ["--delay" as string]: "150ms" }}>
            Last updated {updated}
          </p>
          <Reveal className="prose-legal mt-10" delay={250}>
            {children}
          </Reveal>
        </article>
      </div>
    </div>
  );
}
