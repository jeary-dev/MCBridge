"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { GITHUB_URL, INVITE_URL } from "@/config";
import { Logo } from "./Logo";

const NAV = [
  { href: "/#features", label: "Features" },
  { href: "/#compare", label: "Compare" },
  { href: "/#setup", label: "Setup" },
  { href: "/#faq", label: "FAQ" },
];

export function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 border-b transition-[background-color,border-color] duration-500 ${
        scrolled || open ? "border-line bg-ink/80 backdrop-blur-xl" : "border-transparent"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between px-4 sm:px-6 lg:px-10">
        <Link href="/" aria-label="MCBridge home" onClick={() => setOpen(false)}>
          <Logo />
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-9 md:flex">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} className="nav-link">
              {n.label}
            </a>
          ))}
          <a href={GITHUB_URL} target="_blank" rel="noopener noreferrer" className="nav-link">
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <a
            href={INVITE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden h-9 items-center bg-paper px-4 text-[0.8rem] font-medium text-ink transition-colors duration-300 hover:bg-white sm:inline-flex"
          >
            Add to Discord
          </a>
          <button
            type="button"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-nav"
            onClick={() => setOpen((o) => !o)}
            className="relative grid size-10 place-items-center md:hidden"
          >
            <span
              className={`absolute h-px w-5 bg-paper transition-transform duration-500 ${open ? "rotate-45" : "-translate-y-[4px]"}`}
            />
            <span
              className={`absolute h-px w-5 bg-paper transition-transform duration-500 ${open ? "-rotate-45" : "translate-y-[4px]"}`}
            />
          </button>
        </div>
      </div>

      <div
        id="mobile-nav"
        className={`grid transition-[grid-template-rows] duration-500 ease-[cubic-bezier(.16,1,.3,1)] md:hidden ${
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <nav aria-label="Mobile" className="min-h-0 overflow-hidden" inert={!open}>
          <ul className="flex flex-col px-4 pb-6 pt-2">
            {[...NAV, { href: GITHUB_URL, label: "GitHub" }].map((n) => (
              <li key={n.href} className="border-t border-line">
                <a
                  href={n.href}
                  onClick={() => setOpen(false)}
                  className="flex items-center justify-between py-4 font-display text-xl tracking-tight"
                  {...(n.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                >
                  {n.label}
                  <span className="text-mute">→</span>
                </a>
              </li>
            ))}
            <li className="pt-4">
              <a
                href={INVITE_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex h-12 items-center justify-center bg-paper font-medium text-ink"
              >
                Add to Discord
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
  );
}
