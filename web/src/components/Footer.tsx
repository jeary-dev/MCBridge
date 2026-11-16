import Link from "next/link";
import { CONTACT_EMAIL, DOWNLOAD_URL, GITHUB_URL, INVITE_URL } from "@/config";
import { Logo } from "./Logo";

type FooterLink = { href: string; label: string };

const COLUMNS: { title: string; links: FooterLink[] }[] = [
  {
    title: "Product",
    links: [
      { href: INVITE_URL, label: "Add to Discord" },
      { href: DOWNLOAD_URL, label: "Download the plugin" },
      { href: "/#features", label: "Features" },
      { href: "/#faq", label: "FAQ" },
    ],
  },
  {
    title: "Project",
    links: [
      { href: GITHUB_URL, label: "GitHub" },
      { href: `${GITHUB_URL}/blob/main/LICENSE`, label: "AGPL-3.0 license" },
      { href: `mailto:${CONTACT_EMAIL}`, label: CONTACT_EMAIL },
    ],
  },
  {
    title: "Legal",
    links: [
      { href: "/privacy", label: "Privacy policy" },
      { href: "/terms", label: "Terms of service" },
    ],
  },
];

export function Footer() {
  return (
    <footer className="relative border-t border-line">
      <div className="mx-auto grid max-w-[1240px] gap-12 px-4 py-16 sm:px-6 md:grid-cols-12 lg:px-10">
        <div className="md:col-span-4">
          <Logo />
          <p className="mt-5 max-w-xs text-sm leading-relaxed text-mute">
            Your Minecraft server, live in Discord. A Paper plugin and a hosted bot that actually talk
            to each other.
          </p>
        </div>

        {COLUMNS.map((col) => (
          <div key={col.title} className={col.title === "Project" ? "md:col-span-3" : "md:col-span-2"}>
            <h3 className="mb-5 font-mono text-[0.75rem] uppercase tracking-[0.22em] text-mute">
              {col.title}
            </h3>
            <ul className="space-y-3 text-sm">
              {col.links.map((l) => (
                <li key={l.label}>
                  <FooterAnchor {...l} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="mx-auto flex max-w-[1240px] flex-col gap-3 border-t border-line px-4 py-6 font-mono text-[0.75rem] uppercase tracking-[0.18em] text-mute sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-10">
        <span>© {new Date().getFullYear()} MCBridge · mcbridge.dev</span>
        <span>Not affiliated with Mojang, Microsoft or Discord</span>
      </div>
    </footer>
  );
}

function FooterAnchor({ href, label }: FooterLink) {
  const cls = "whitespace-nowrap text-paper-dim transition-colors duration-300 hover:text-paper";
  if (href.startsWith("/")) {
    return (
      <Link href={href} className={cls}>
        {label}
      </Link>
    );
  }
  const external = href.startsWith("http");
  return (
    <a
      href={href}
      className={cls}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {label}
    </a>
  );
}
