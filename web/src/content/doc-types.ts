import type { ReactNode } from "react";

export type DocSection = {
  /** Anchor id, unique within the page. */
  id: string;
  title: string;
  body: ReactNode;
};

export type DocPage = {
  /** Full path, e.g. "/docs/features/chat-bridge". */
  href: string;
  title: string;
  /** Shorter label for the sidebar, if different. */
  navTitle?: string;
  description: string;
  /** Repo path the "Edit this page on GitHub" link points to. */
  editPath: string;
  /** Shown above the first section (summary boxes, lead paragraph). */
  intro?: ReactNode;
  sections: DocSection[];
};
