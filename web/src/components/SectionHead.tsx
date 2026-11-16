import type { ReactNode } from "react";
import { Reveal } from "./Reveal";

type Props = {
  index: string;
  label: string;
  kanji: string;
  title: ReactNode;
  intro?: ReactNode;
};

/** Numbered section heading: index, label, a self-drawing hairline and a kanji mark. */
export function SectionHead({ index, label, kanji, title, intro }: Props) {
  return (
    <Reveal className="relative mb-14 md:mb-20">
      <div className="mb-8 flex items-center gap-4 font-mono text-[0.7rem] uppercase tracking-[0.22em] text-mute">
        <span className="text-paper">{index}</span>
        <span>{label}</span>
        <div className="rule flex-1" style={{ ["--delay" as string]: "200ms" }} />
        <span lang="ja" className="font-jp text-base tracking-[0.3em] text-paper-dim">
          {kanji}
        </span>
      </div>
      <div className="grid gap-6 md:grid-cols-12">
        <h2 className="font-display text-[clamp(2rem,4.6vw,3.6rem)] font-medium leading-[1.02] tracking-[-0.035em] text-balance md:col-span-7">
          {title}
        </h2>
        {intro && (
          <p className="max-w-md self-end text-[1.02rem] leading-relaxed text-paper-dim md:col-span-4 md:col-start-9">
            {intro}
          </p>
        )}
      </div>
    </Reveal>
  );
}
