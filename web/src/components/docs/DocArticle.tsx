import Link from "next/link";
import type { DocPage } from "@/content/doc-types";
import { DOCS_NAV, prevNext } from "@/content/docs";
import { GITHUB_EDIT_BASE } from "@/config";
import { Toc } from "./Toc";

/** One docs page: title, intro, sections, edit link, prev/next, and "On this page" on wide screens. */
export function DocArticle({ page }: { page: DocPage }) {
  const { prev, next } = prevNext(page.href);
  const group = DOCS_NAV.find((g) => g.items.some((i) => i.href === page.href));

  return (
    <div className="grid gap-12 xl:grid-cols-[minmax(0,1fr)_13rem]">
      <article className="min-w-0 py-10 lg:py-14">
        {group && <p className="font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute">{group.title}</p>}
        <h1 className="mt-3 font-display text-[clamp(2rem,4.4vw,3rem)] font-medium leading-[1.05] tracking-[-0.035em] [overflow-wrap:anywhere]">
          {page.title}
        </h1>

        <div className="doc-prose mt-6">
          {page.intro}
          {page.sections.map((s) => (
            <section key={s.id} aria-labelledby={s.id}>
              <h2 id={s.id}>
                <a href={`#${s.id}`} className="anchor">
                  {s.title}
                </a>
              </h2>
              {s.body}
            </section>
          ))}
        </div>

        <div className="mt-14 border-t border-line pt-6">
          <a
            href={`${GITHUB_EDIT_BASE}/${page.editPath}`}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[0.8rem] text-paper-dim underline decoration-line-strong underline-offset-4 transition-colors hover:text-paper hover:decoration-paper"
          >
            Edit this page on GitHub ↗
          </a>
        </div>

        <nav aria-label="Previous and next page" className="mt-8 grid gap-3 sm:grid-cols-2">
          {prev ? (
            <Link href={prev.href} className="group border border-line p-4 transition-colors hover:border-paper">
              <span className="block font-mono text-[0.75rem] uppercase tracking-[0.16em] text-mute">← Previous</span>
              <span className="mt-1 block text-paper">{prev.title}</span>
            </Link>
          ) : (
            <span />
          )}
          {next && (
            <Link href={next.href} className="group border border-line p-4 text-right transition-colors hover:border-paper">
              <span className="block font-mono text-[0.75rem] uppercase tracking-[0.16em] text-mute">Next →</span>
              <span className="mt-1 block text-paper">{next.title}</span>
            </Link>
          )}
        </nav>
      </article>

      <aside className="hidden xl:block">
        <div className="sticky top-16 max-h-[calc(100dvh-4rem)] overflow-y-auto py-14">
          <Toc items={page.sections.map((s) => ({ id: s.id, title: s.title }))} />
        </div>
      </aside>
    </div>
  );
}
