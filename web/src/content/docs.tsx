/**
 * Assembles every /docs page, the sidebar and the search index from the content files.
 * Command pages are generated from ./commands.ts, which MUST MATCH docs/COMMANDS.md.
 */
import Link from "next/link";
import type { DocPage } from "./doc-types";
import { ACCESS_LABEL, COMMANDS, PERMISSIONS_NOTE, commandBySlug, type Command, type CommandOption } from "./commands";
import { FEATURE_PAGES } from "./features";
import { COMMANDS_INDEX, HELP, OVERVIEW, PLUGIN, QUICK_START } from "./guides";
import { CodeBlock, DataTable } from "@/components/docs/Prose";
import { ExampleMessages } from "@/components/discord/Mock";

/* ── Command pages ──────────────────────────────────────────────────────── */

function OptionsTable({ options, caption }: { options: CommandOption[]; caption: string }) {
  return (
    <DataTable
      caption={caption}
      head={["Option", "Required", "What it does"]}
      mono={[]}
      rows={options.map((o) => [o.name, o.required ? "Yes" : "No", o.does])}
    />
  );
}

function SummaryBox({ c }: { c: Command }) {
  const rows: [string, string][] = [
    ["Who can use it", ACCESS_LABEL[c.access]],
    ["Works in", "Text channels in a Discord server, not DMs"],
    ["Needs", c.needs.length ? c.needs.join(" · ") : "Nothing extra"],
  ];
  return (
    <dl className="not-prose my-6 grid border border-line-strong bg-ink-2 sm:grid-cols-3">
      {rows.map(([k, v], i) => (
        <div key={k} className={`p-4 ${i ? "border-t border-line sm:border-l sm:border-t-0" : ""}`}>
          <dt className="font-mono text-[0.75rem] uppercase tracking-[0.16em] text-mute">{k}</dt>
          <dd className="mt-1.5 text-[0.92rem] text-paper">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function commandPage(c: Command): DocPage {
  const sections: DocPage["sections"] = [
    { id: "usage", title: "Usage", body: <CodeBlock lines={c.usage} /> },
  ];

  if (c.subcommands) {
    sections.push({
      id: "subcommands",
      title: "Subcommands",
      body: (
        <>
          {c.subcommands.map((s) => (
            <div key={s.name} className="mt-8 first:mt-4">
              <h3>
                <code>
                  {c.name} {s.name}
                </code>
              </h3>
              <p>{s.does}</p>
              <CodeBlock lines={s.usage} />
              {s.options.length > 0 && <OptionsTable options={s.options} caption={`Options for ${c.name} ${s.name}`} />}
              {s.needs && <p className="text-[0.9rem]">Needs: {s.needs.join(", ")}.</p>}
            </div>
          ))}
        </>
      ),
    });
  } else {
    sections.push({
      id: "options",
      title: "Options",
      body: c.options.length ? (
        <OptionsTable options={c.options} caption={`Options for ${c.name}`} />
      ) : (
        <p>This command has no options.</p>
      ),
    });
  }

  sections.push(
    {
      id: "example",
      title: "Example",
      body: (
        <div className="not-prose my-6">
          <ExampleMessages messages={c.example} channel={c.access === "everyone" ? "general" : "staff"} />
          <p className="mt-3 font-mono text-[0.75rem] text-mute">Illustration. Names and numbers are made up.</p>
        </div>
      ),
    },
    {
      id: "good-to-know",
      title: "Good to know",
      body: (
        <ul>
          {c.goodToKnow.map((g) => (
            <li key={g}>{g}</li>
          ))}
          <li>{PERMISSIONS_NOTE}</li>
        </ul>
      ),
    },
    {
      id: "related",
      title: "Related commands",
      body: (
        <ul className="not-prose my-4 flex flex-wrap gap-2">
          {c.related.map((slug) => {
            const r = commandBySlug(slug);
            return r ? (
              <li key={slug}>
                <Link
                  href={`/docs/commands/${slug}`}
                  className="inline-block border border-line-strong px-3 py-1.5 font-mono text-[0.85rem] text-paper-dim transition-colors hover:border-paper hover:text-paper"
                >
                  {r.name}
                </Link>
              </li>
            ) : null;
          })}
        </ul>
      ),
    },
  );

  return {
    href: `/docs/commands/${c.slug}`,
    title: c.name,
    description: `${c.summary} How to use ${c.name}, its options, who can use it and what it needs.`,
    editPath: "docs/COMMANDS.md",
    intro: (
      <>
        <p className="text-[1.08rem]">{c.does}</p>
        <SummaryBox c={c} />
      </>
    ),
    sections,
  };
}

export const COMMAND_PAGES = COMMANDS.map(commandPage);

/* ── Navigation ─────────────────────────────────────────────────────────── */

export type NavItem = { href: string; title: string };
export type NavGroup = { title: string; items: NavItem[] };

const item = (p: DocPage): NavItem => ({ href: p.href, title: p.navTitle ?? p.title });

export const DOCS_NAV: NavGroup[] = [
  { title: "Getting started", items: [item(OVERVIEW), item(QUICK_START)] },
  { title: "Commands", items: [item(COMMANDS_INDEX), ...COMMAND_PAGES.map(item)] },
  { title: "Features", items: FEATURE_PAGES.map(item) },
  { title: "Reference", items: [item(PLUGIN), item(HELP)] },
];

/** Every page, in sidebar order (used for prev/next). */
export const ALL_DOCS: DocPage[] = [
  OVERVIEW,
  QUICK_START,
  COMMANDS_INDEX,
  ...COMMAND_PAGES,
  ...FEATURE_PAGES,
  PLUGIN,
  HELP,
];

export function docByHref(href: string) {
  return ALL_DOCS.find((p) => p.href === href);
}

export function prevNext(href: string) {
  const i = ALL_DOCS.findIndex((p) => p.href === href);
  const at = (j: number) => (j >= 0 && j < ALL_DOCS.length ? item(ALL_DOCS[j]) : null);
  return { prev: at(i - 1), next: at(i + 1) };
}

/* ── Search index (built at build time, shipped with the page) ──────────── */

export type SearchEntry = { title: string; href: string; page?: string };

export const SEARCH_INDEX: SearchEntry[] = ALL_DOCS.flatMap((p) => [
  { title: p.title, href: p.href },
  ...p.sections.map((s) => ({ title: s.title, href: `${p.href}#${s.id}`, page: p.navTitle ?? p.title })),
  ...(COMMANDS.find((c) => `/docs/commands/${c.slug}` === p.href)?.subcommands ?? []).map((s) => ({
    title: `${p.title} ${s.name}`,
    href: `${p.href}#subcommands`,
    page: p.title,
  })),
]);
