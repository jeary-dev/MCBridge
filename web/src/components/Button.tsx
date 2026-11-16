import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  href: string;
  children: ReactNode;
  variant?: "solid" | "ghost";
  className?: string;
};

export function Button({ href, children, variant = "solid", className = "" }: Props) {
  const external = href.startsWith("http");
  const base =
    "group relative inline-flex h-12 items-center justify-center gap-3 overflow-hidden px-6 text-[0.9rem] font-medium tracking-tight transition-colors duration-500";
  const styles =
    variant === "solid"
      ? "bg-accent text-ink"
      : "border border-line-strong text-paper hover:border-paper";
  const inner = (
    <>
      <span
        aria-hidden
        className={`absolute inset-0 origin-left scale-x-0 transition-transform duration-500 ease-[cubic-bezier(.16,1,.3,1)] group-hover:scale-x-100 ${
          variant === "solid" ? "bg-accent-hi" : "bg-paper/[0.06]"
        }`}
      />
      <span className="relative">{children}</span>
      <span
        aria-hidden
        className="relative inline-block transition-transform duration-500 ease-[cubic-bezier(.16,1,.3,1)] group-hover:translate-x-1"
      >
        →
      </span>
    </>
  );
  if (href.startsWith("/")) {
    return (
      <Link href={href} className={`${base} ${styles} ${className}`}>
        {inner}
      </Link>
    );
  }
  return (
    <a
      href={href}
      className={`${base} ${styles} ${className}`}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {inner}
    </a>
  );
}
