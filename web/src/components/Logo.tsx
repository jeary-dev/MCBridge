/** Hanko-style square seal with 橋 ("bridge"). */
export function Seal({ size = 28 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="inline-grid shrink-0 place-items-center bg-paper font-jp font-extrabold leading-none text-ink"
      style={{ width: size, height: size, fontSize: size * 0.68, borderRadius: 3 }}
    >
      橋
    </span>
  );
}

export function Logo() {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Seal />
      <span className="font-display text-[1.05rem] font-medium tracking-tight">MCBridge</span>
    </span>
  );
}
