import { ImageResponse } from "next/og";

// Rendered once at build time and written to out/og.png (the Open Graph image).
export const dynamic = "force-static";
const size = { width: 1200, height: 630 };

const PLAYERS = [3, 3, 4, 4, 5, 4, 5, 6, 6, 7, 6, 6, 7, 8, 8, 7, 6, 7, 7, 6, 6, 7, 6, 6];

export function GET() {
  const W = 460;
  const H = 110;
  const step = W / (PLAYERS.length - 1);
  const line = PLAYERS.map((v, i) => `${i ? "L" : "M"}${(i * step).toFixed(1)} ${(H - (v / 10) * H).toFixed(1)}`).join(" ");

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          background: "#0b0b0c",
          color: "#edebe6",
          padding: 80,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ position: "absolute", left: 80, top: 80, display: "flex", alignItems: "center", gap: 16, fontSize: 30 }}>
          <div style={{ width: 22, height: 22, background: "#edebe6" }} />
          MCBridge
        </div>
        <div
          style={{
            position: "absolute",
            left: 80,
            bottom: 140,
            display: "flex",
            flexDirection: "column",
            fontSize: 72,
            letterSpacing: -3,
            lineHeight: 1.02,
          }}
        >
          <span>Your Minecraft server,</span>
          <span style={{ color: "#b9b6ae" }}>live in Discord.</span>
        </div>
        <div style={{ position: "absolute", left: 80, bottom: 80, display: "flex", fontSize: 24, color: "#7c7a75" }}>
          Paper 1.21 · Java 21 · Open source · mcbridge.dev
        </div>
        <div
          style={{
            position: "absolute",
            right: 80,
            top: 56,
            width: 500,
            display: "flex",
            flexDirection: "column",
            border: "1px solid rgba(237,235,230,.18)",
            borderLeft: "4px solid #edebe6",
            padding: 20,
            background: "#18181b",
            opacity: 0.9,
          }}
        >
          <div style={{ display: "flex", fontSize: 26 }}>Hinoki SMP</div>
          <div style={{ display: "flex", fontSize: 18, color: "#b9b6ae", marginTop: 6 }}>Online · TPS 20.0 · 6/20 players</div>
          <svg width={W} height={H + 10} viewBox={`0 -5 ${W} ${H + 10}`} style={{ marginTop: 18 }}>
            <path d={`${line} L${W} ${H} L0 ${H} Z`} fill="rgba(237,235,230,.1)" />
            <path d={line} fill="none" stroke="#edebe6" strokeWidth={2.5} />
          </svg>
        </div>
      </div>
    ),
    size,
  );
}
