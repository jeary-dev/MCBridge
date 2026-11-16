/** The bridge mark (same drawing as src/app/icon.svg). Decorative: always paired with a text label. */
export function Seal({ size = 28 }: { size?: number }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 32 32"
      width={size}
      height={size}
      className="block shrink-0"
    >
      <rect width="32" height="32" rx="4" fill="#edebe6" />
      <path
        d="M5 22h22M7 22c3-8 15-8 18 0M11 22v-4.5M16 22v-6M21 22v-4.5"
        fill="none"
        stroke="#0b0b0c"
        strokeWidth="2.4"
        strokeLinecap="square"
      />
    </svg>
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
