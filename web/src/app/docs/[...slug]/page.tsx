import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocArticle } from "@/components/docs/DocArticle";
import { ALL_DOCS, docByHref } from "@/content/docs";
import { pageMeta } from "@/lib/meta";

// Static export: only the pages listed here exist.
export const dynamicParams = false;

export function generateStaticParams() {
  return ALL_DOCS.filter((p) => p.href !== "/docs").map((p) => ({
    slug: p.href.replace(/^\/docs\//, "").split("/"),
  }));
}

async function pageFor(params: PageProps<"/docs/[...slug]">["params"]) {
  const { slug } = await params;
  return docByHref(`/docs/${slug.join("/")}`);
}

export async function generateMetadata(props: PageProps<"/docs/[...slug]">): Promise<Metadata> {
  const page = await pageFor(props.params);
  if (!page) return {};
  const isCommand = page.href.startsWith("/docs/commands/");
  return pageMeta({
    title: isCommand ? `${page.title} command` : page.title,
    description: page.description,
    path: page.href,
  });
}

export default async function DocPageRoute(props: PageProps<"/docs/[...slug]">) {
  const page = await pageFor(props.params);
  if (!page) notFound();
  return <DocArticle page={page} />;
}
