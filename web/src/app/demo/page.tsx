import type { Metadata } from "next";
import { Button } from "@/components/Button";
import { LiveDemo } from "@/components/demo/LiveDemo";
import { INVITE_URL, SUPPORT_INVITE } from "@/config";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = pageMeta({
  title: "Live demo",
  description:
    "A real Minecraft server running MCBridge, live: status, players, TPS over the last hour, and chat bridged with our Discord.",
  path: "/demo",
});

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-[1240px] px-4 pb-28 pt-28 sm:px-6 md:pt-36 lg:px-10">
      <div className="mb-12 grid gap-8 lg:grid-cols-12 lg:items-end">
        <div className="lg:col-span-7">
          <p className="mb-6 flex items-center gap-3 font-mono text-[0.75rem] uppercase tracking-[0.22em] text-mute">
            <span aria-hidden className="inline-block h-px w-8 bg-mute" />
            Live demo
          </p>
          <h1 className="font-display text-[clamp(2.4rem,5.4vw,4rem)] font-medium leading-[1] tracking-[-0.045em]">
            A real server,
            <span className="text-paper-dim"> live right now.</span>
          </h1>
        </div>
        <div className="lg:col-span-5">
          <p className="text-[1.02rem] leading-relaxed text-paper-dim">
            This is our demo Minecraft server, as MCBridge sees it. It refreshes every 10 seconds. Say something in our
            Discord and watch it show up in the feed.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button href={SUPPORT_INVITE}>Talk to it in our Discord</Button>
            <Button href={INVITE_URL} variant="ghost">
              Add to your Discord
            </Button>
          </div>
        </div>
      </div>

      <LiveDemo />
    </div>
  );
}
