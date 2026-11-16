"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import type { NavGroup, SearchEntry } from "@/content/docs";

function normalise(path: string | null) {
  if (!path) return "/docs";
  return path.replace(/\.html$/, "").replace(/\/$/, "") || "/";
}

/* ── Search ─────────────────────────────────────────────────────────────── */

function search(index: SearchEntry[], q: string) {
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  return index
    .map((e) => {
      const hay = `${e.title} ${e.page ?? ""}`.toLowerCase();
      if (!words.every((w) => hay.includes(w))) return null;
      const t = e.title.toLowerCase();
      // Page titles and prefix matches first.
      const score = (e.page ? 1 : 0) + (t.startsWith(words[0]) || t.startsWith(`/${words[0]}`) ? 0 : 2);
      return { e, score };
    })
    .filter((x): x is { e: SearchEntry; score: number } => x !== null)
    .sort((a, b) => a.score - b.score)
    .slice(0, 12)
    .map((x) => x.e);
}

function SearchBox({ index, onNavigate }: { index: SearchEntry[]; onNavigate?: () => void }) {
  const [q, setQ] = useState("");
  const inputId = useId();
  const listId = useId();
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const results = useMemo(() => search(index, q), [index, q]);

  // "/" focuses the search box (unless you're typing somewhere already).
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      const el = document.activeElement;
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      if (el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || (el as HTMLElement).isContentEditable)) return;
      if (!input.current || input.current.offsetParent === null) return;
      e.preventDefault();
      input.current.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const move = (e: KeyboardEvent, from: number) => {
    const links = list.current?.querySelectorAll<HTMLAnchorElement>("a");
    if (!links?.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      links[Math.min(links.length - 1, from + 1)]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (from <= 0) input.current?.focus();
      else links[from - 1]?.focus();
    } else if (e.key === "Escape") {
      setQ("");
      input.current?.focus();
    }
  };

  return (
    <div role="search">
      <label htmlFor={inputId} className="sr-only">
        Search the docs
      </label>
      <div className="relative">
        <input
          ref={input}
          id={inputId}
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape" && q) {
              e.preventDefault();
              setQ("");
            } else move(e, -1);
          }}
          placeholder="Search docs"
          autoComplete="off"
          aria-controls={listId}
          className="h-10 w-full border border-line-strong bg-ink-2 px-3 pr-9 text-[0.9rem] text-paper placeholder:text-mute focus:border-paper focus:outline-none"
        />
        {!q && (
          <kbd
            aria-hidden
            className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 border border-line-strong px-1.5 font-mono text-[0.75rem] text-mute"
          >
            /
          </kbd>
        )}
      </div>
      <div aria-live="polite" className="sr-only">
        {q ? `${results.length} result${results.length === 1 ? "" : "s"}` : ""}
      </div>
      {q && (
        <ul ref={list} id={listId} className="mt-2 border border-line bg-ink-2">
          {results.length === 0 && <li className="px-3 py-3 text-[0.9rem] text-mute">No results for “{q}”</li>}
          {results.map((r, i) => (
            <li key={r.href + r.title}>
              <Link
                href={r.href}
                onClick={() => {
                  setQ("");
                  onNavigate?.();
                }}
                onKeyDown={(e) => move(e, i)}
                className="block border-b border-line px-3 py-2.5 last:border-0 hover:bg-ink-3 focus-visible:bg-ink-3"
              >
                <span className="block text-[0.9rem] text-paper">{r.title}</span>
                {r.page && <span className="block font-mono text-[0.75rem] text-mute">{r.page}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* ── Nav tree ───────────────────────────────────────────────────────────── */

function NavTree({ nav, path, onNavigate }: { nav: NavGroup[]; path: string; onNavigate?: () => void }) {
  // Only groups you toggle are stored; the rest open by default when they hold the current page.
  const [toggled, setToggled] = useState<Record<string, boolean>>({});
  const uid = useId();
  const defaultOpen = (g: NavGroup) =>
    g.items.some((i) => i.href === path) || g.title === "Getting started" || g.title === "Reference";

  return (
    <nav aria-label="Docs" className="mt-6">
      {nav.map((g) => {
        const id = `${uid}-${g.title.toLowerCase().replace(/\W+/g, "-")}`;
        const isOpen = toggled[g.title] ?? defaultOpen(g);
        return (
          <div key={g.title} className="mb-5">
            <button
              type="button"
              aria-expanded={isOpen}
              aria-controls={id}
              onClick={() => setToggled((t) => ({ ...t, [g.title]: !isOpen }))}
              className="flex w-full items-center justify-between py-1.5 font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute transition-colors hover:text-paper"
            >
              {g.title}
              <span aria-hidden className={`transition-transform duration-300 ${isOpen ? "rotate-90" : ""}`}>
                ›
              </span>
            </button>
            <ul id={id} hidden={!isOpen} className="mt-1.5 border-l border-line">
              {g.items.map((i) => {
                const active = i.href === path;
                return (
                  <li key={i.href}>
                    <Link
                      href={i.href}
                      onClick={onNavigate}
                      aria-current={active ? "page" : undefined}
                      className={`-ml-px block border-l py-1.5 pl-4 text-[0.9rem] transition-colors ${
                        active
                          ? "border-accent text-paper"
                          : "border-transparent text-paper-dim hover:border-line-strong hover:text-paper"
                      }`}
                    >
                      {i.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

/* ── Sidebar (desktop) + drawer (mobile) ────────────────────────────────── */

export function DocsSidebar({ nav, index }: { nav: NavGroup[]; index: SearchEntry[] }) {
  const path = normalise(usePathname());
  const dialog = useRef<HTMLDialogElement>(null);
  const current = nav.flatMap((g) => g.items).find((i) => i.href === path);

  const close = () => dialog.current?.close();

  return (
    <>
      {/* Mobile / tablet bar */}
      <div className="sticky top-16 z-30 -mx-4 border-b border-line bg-ink/90 px-4 backdrop-blur-xl sm:-mx-6 sm:px-6 lg:hidden">
        <button
          type="button"
          onClick={() => dialog.current?.showModal()}
          aria-haspopup="dialog"
          className="flex h-12 w-full items-center gap-3 text-left text-[0.9rem]"
        >
          <span aria-hidden className="grid gap-[3px]">
            <i className="block h-px w-4 bg-paper" />
            <i className="block h-px w-4 bg-paper" />
            <i className="block h-px w-4 bg-paper" />
          </span>
          <span className="text-paper">Docs menu</span>
          {current && <span className="min-w-0 truncate text-mute">· {current.title}</span>}
        </button>
      </div>

      <dialog
        ref={dialog}
        aria-label="Docs navigation"
        className="docs-drawer m-0 h-dvh max-h-dvh w-[min(20rem,88vw)] max-w-none overflow-y-auto border-r border-line-strong bg-ink p-5 text-paper backdrop:bg-black/60 lg:hidden"
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
      >
        <div className="mb-5 flex items-center justify-between">
          <span className="font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute">Docs</span>
          <button
            type="button"
            onClick={close}
            className="border border-line-strong px-2.5 py-1 text-[0.85rem] text-paper-dim hover:border-paper hover:text-paper"
          >
            Close
          </button>
        </div>
        <SearchBox index={index} onNavigate={close} />
        <NavTree nav={nav} path={path} onNavigate={close} />
      </dialog>

      {/* Desktop sidebar */}
      <aside className="hidden lg:block">
        <div className="sticky top-16 max-h-[calc(100dvh-4rem)] overflow-y-auto py-10 pr-6">
          <SearchBox index={index} />
          <NavTree nav={nav} path={path} />
        </div>
      </aside>
    </>
  );
}
