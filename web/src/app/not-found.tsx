import type { Metadata } from "next";
import Link from "next/link";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = {
  ...pageMeta({ title: "Page not found", description: "This page doesn't exist.", path: "/404" }),
  robots: { index: false },
};

export default function NotFound() {
  return (
    <section className="relative isolate flex min-h-[80dvh] items-center overflow-hidden">
      <span
        lang="ja"
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 select-none font-jp text-[clamp(14rem,40vw,30rem)] font-extrabold leading-none text-transparent [-webkit-text-stroke:1px_rgb(237_235_230/0.08)]"
      >
        無
      </span>
      <div className="mx-auto w-full max-w-[1240px] px-4 pt-24 sm:px-6 lg:px-10">
        <p className="fade-in font-mono text-[0.7rem] uppercase tracking-[0.22em] text-mute">Error 404</p>
        <h1 className="mt-6 font-display text-[clamp(2.6rem,7vw,5.5rem)] font-medium leading-none tracking-[-0.045em]">
          <span className="line-mask">
            <span>Nothing here.</span>
          </span>
          <span className="line-mask">
            <span className="text-paper-dim" style={{ ["--delay" as string]: "150ms" }}>
              The bridge ends.
            </span>
          </span>
        </h1>
        <p className="fade-in mt-8 max-w-md text-paper-dim" style={{ ["--delay" as string]: "400ms" }}>
          The page you&apos;re looking for doesn&apos;t exist or has moved.
        </p>
        <Link
          href="/"
          className="fade-in group mt-10 inline-flex h-12 items-center gap-3 border border-line-strong px-6 text-[0.9rem] transition-colors hover:border-paper"
          style={{ ["--delay" as string]: "550ms" }}
        >
          <span className="transition-transform duration-500 group-hover:-translate-x-1">←</span>
          Back to MCBridge
        </Link>
      </div>
    </section>
  );
}
