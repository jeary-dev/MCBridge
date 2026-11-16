"use client";

import { useEffect, useState } from "react";
import { BotMessage, EXAMPLE_STATUS, HEAD, Message, MockWindow, Pixels, StatusEmbed } from "./discord/Mock";

/** The homepage hero: an example status card whose numbers wobble gently. */
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

  return (
    <div className="relative" aria-label="Example of the MCBridge status card in a Discord channel" role="img">
      <MockWindow channel="server-status" live className="shadow-[0_40px_120px_-30px_rgb(0_0_0/0.9)]">
        <BotMessage>
          <StatusEmbed
            data={{
              ...EXAMPLE_STATUS,
              tps: [tps, 19.9, 19.9],
              mspt: 12.4 + wobble(2, 1.6),
              memUsedMb: (2.14 + wobble(3, 0.12) + (t % 6) * 0.015) * 1024,
              uptimeS: (EXAMPLE_STATUS.uptimeS ?? 0) + t * 60,
              footer: "MCBridge 0.2.0 · updated just now",
            }}
          />
        </BotMessage>

        <Message author="kiri_" avatar={<Pixels grid={HEAD} size={34} />} tag="In game" time="today at 21:05">
          <p className="text-[0.85rem] text-paper-dim">anyone up for the nether trip tonight? bringing extra blocks</p>
        </Message>
      </MockWindow>
    </div>
  );
}
