import type { ReactNode } from "react";
import { CopyButton } from "./CopyButton";

/** A code block with a copy button. `lines` are joined with newlines. */
export function CodeBlock({ lines, label }: { lines: string[] | string; label?: string }) {
  const text = Array.isArray(lines) ? lines.join("\n") : lines;
  return (
    <div className="group/code relative my-5 border border-line-strong bg-ink-2">
      {label && (
        <div className="border-b border-line px-4 py-2 font-mono text-[0.75rem] uppercase tracking-[0.16em] text-mute">
          {label}
        </div>
      )}
      <pre className="overflow-x-auto px-4 py-3.5 pr-20 font-mono text-[0.85rem] leading-relaxed text-paper">
        <code>{text}</code>
      </pre>
      <CopyButton text={text} />
    </div>
  );
}

/** A table that scrolls sideways inside itself on small screens, never the page. */
export function DataTable({
  caption,
  head,
  rows,
  mono = [0],
}: {
  caption: string;
  head: string[];
  rows: ReactNode[][];
  /** Column indexes rendered in the mono font. */
  mono?: number[];
}) {
  return (
    <div className="my-6 overflow-x-auto border border-line" role="region" aria-label={caption} tabIndex={0}>
      <table className="w-full min-w-[520px] border-collapse text-left text-[0.9rem]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line-strong bg-ink-2">
            {head.map((h) => (
              <th key={h} scope="col" className="px-4 py-3 font-mono text-[0.75rem] font-normal uppercase tracking-[0.16em] text-mute">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-line last:border-0 align-top">
              {r.map((c, j) =>
                j === 0 ? (
                  <th key={j} scope="row" className="px-4 py-3 font-mono text-[0.82rem] font-normal text-paper">
                    {c}
                  </th>
                ) : (
                  <td key={j} className={`px-4 py-3 ${mono.includes(j) ? "font-mono text-[0.82rem] text-paper" : "text-paper-dim"}`}>
                    {c}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Callout({ title, children, tone = "note" }: { title: string; children: ReactNode; tone?: "note" | "warn" }) {
  return (
    <aside
      className={`my-6 border-l-2 bg-ink-2 px-5 py-4 ${tone === "warn" ? "border-paper" : "border-accent"}`}
      aria-label={title}
    >
      <p className="font-mono text-[0.75rem] uppercase tracking-[0.18em] text-paper">{title}</p>
      <div className="mt-2 text-[0.95rem] leading-relaxed text-paper-dim [&_code]:text-paper">{children}</div>
    </aside>
  );
}

/** Numbered steps with a hairline rail. */
export function Steps({ children }: { children: ReactNode }) {
  return <ol className="doc-steps my-6">{children}</ol>;
}

export function Step({ title, children }: { title: string; children: ReactNode }) {
  return (
    <li>
      <h3 className="font-display text-[1.1rem] font-medium tracking-tight text-paper">{title}</h3>
      <div className="mt-2">{children}</div>
    </li>
  );
}
