import type { Metadata } from "next";
import { DocArticle } from "@/components/docs/DocArticle";
import { OVERVIEW } from "@/content/guides";
import { pageMeta } from "@/lib/meta";

export const metadata: Metadata = pageMeta({
  title: "Docs",
  description: OVERVIEW.description,
  path: OVERVIEW.href,
});

export default function DocsHome() {
  return <DocArticle page={OVERVIEW} />;
}
