/**
 * Minecraft server ── MCBridge ── Discord, drawn as a bridge.
 * Packets travel the arc both ways: events out, commands back.
 */
export function BridgeDiagram() {
  const arc = "M 40 120 Q 300 10 560 120";
  // Cropped to the drawing (top labels at y≈22, last water line at y=150) so there is no dead space below.
  const viewBox = "0 20 600 136";
  return (
    <div className="relative">
      <svg viewBox={viewBox} className="block h-auto w-full" role="img" aria-labelledby="bridge-title">
        <title id="bridge-title">
          The plugin inside your Minecraft server connects out to MCBridge, which talks to Discord.
        </title>
        {/* water lines */}
        {[134, 142, 150].map((y, i) => (
          <line
            key={y}
            x1={60 + i * 30}
            x2={540 - i * 30}
            y1={y}
            y2={y}
            stroke="rgb(237 235 230 / .08)"
            strokeDasharray={i === 0 ? "none" : "2 6"}
          />
        ))}
        {/* deck + arc */}
        <line x1="40" x2="560" y1="120" y2="120" stroke="rgb(237 235 230 / .25)" />
        <path d={arc} fill="none" stroke="rgb(237 235 230 / .5)" strokeWidth="1" />
        {/* hangers */}
        {Array.from({ length: 11 }, (_, i) => {
          const x = 90 + i * 42;
          const tt = (x - 40) / 520;
          const y = (1 - tt) ** 2 * 120 + 2 * (1 - tt) * tt * 10 + tt ** 2 * 120;
          return <line key={x} x1={x} x2={x} y1={y} y2={120} stroke="rgb(237 235 230 / .14)" />;
        })}
        {/* towers */}
        <Node x={40} label="Minecraft" sub="Paper plugin" />
        <Node x={300} label="MCBridge" sub="hosted" top={65} filled />
        <Node x={560} label="Discord" sub="your discord" />
      </svg>

      {/* packets ride the same arc via offset-path */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <svg viewBox={viewBox} className="h-full w-full overflow-visible">
          <foreignObject width="600" height="170">
            <div className="relative h-full w-full">
              <span
                className="packet absolute left-0 top-0 block size-[7px] -translate-x-1/2 -translate-y-1/2 bg-paper"
                style={{ offsetPath: `path("${arc}")` }}
              />
              <span
                className="packet reverse absolute left-0 top-0 block size-[7px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-paper"
                style={{ offsetPath: `path("${arc}")` }}
              />
            </div>
          </foreignObject>
        </svg>
      </div>

      <div className="mt-5 flex flex-wrap justify-between gap-4 font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute">
        <span className="flex items-center gap-2">
          <i className="inline-block size-[7px] bg-paper" /> events, heartbeats →
        </span>
        <span className="flex items-center gap-2">
          ← commands <i className="inline-block size-[7px] rounded-full border border-paper" />
        </span>
        <span>wss:// · outbound only · no open ports</span>
      </div>
    </div>
  );
}

function Node({
  x,
  label,
  sub,
  top = 120,
  filled = false,
}: {
  x: number;
  label: string;
  sub: string;
  top?: number;
  filled?: boolean;
}) {
  return (
    <g>
      <rect
        x={x - 5}
        y={top - 5}
        width="10"
        height="10"
        fill={filled ? "#edebe6" : "#0b0b0c"}
        stroke="#edebe6"
      />
      <text
        x={x}
        y={top === 120 ? 66 : top - 18}
        textAnchor={x < 100 ? "start" : x > 500 ? "end" : "middle"}
        fill="#edebe6"
        style={{ font: "500 13px var(--font-grotesk)" }}
      >
        {label}
      </text>
      <text
        x={x}
        y={top === 120 ? 50 : top - 32}
        textAnchor={x < 100 ? "start" : x > 500 ? "end" : "middle"}
        fill="#7c7a75"
        style={{ font: "10px var(--font-jetbrains)", letterSpacing: "0.12em", textTransform: "uppercase" }}
      >
        {sub}
      </text>
    </g>
  );
}
