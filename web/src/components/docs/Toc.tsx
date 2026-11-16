"use client";

import { useEffect, useState } from "react";

/** "On this page": the page's h2s, highlighting the one you're reading. */
export function Toc({ items }: { items: { id: string; title: string }[] }) {
  const [active, setActive] = useState(items[0]?.id);

  useEffect(() => {
    const els = items.map((i) => document.getElementById(i.id)).filter((e): e is HTMLElement => e !== null);
    if (!els.length) return;
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-72px 0px -65% 0px" },
    );
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, [items]);

  if (items.length < 2) return null;
  return (
    <nav aria-label="On this page">
      <p className="mb-3 font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute">On this page</p>
      <ul className="border-l border-line">
        {items.map((i) => (
          <li key={i.id}>
            <a
              href={`#${i.id}`}
              aria-current={active === i.id ? "location" : undefined}
              className={`-ml-px block border-l py-1 pl-4 text-[0.85rem] transition-colors ${
                active === i.id ? "border-paper text-paper" : "border-transparent text-paper-dim hover:text-paper"
              }`}
            >
              {i.title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
