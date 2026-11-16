import { DocsSidebar } from "@/components/docs/DocsSidebar";
import { DOCS_NAV, SEARCH_INDEX } from "@/content/docs";

export default function DocsLayout({ children }: LayoutProps<"/docs">) {
  return (
    <div className="mx-auto max-w-[1400px] px-4 pt-16 sm:px-6 lg:grid lg:grid-cols-[16rem_minmax(0,1fr)] lg:gap-10 lg:px-10">
      <DocsSidebar nav={DOCS_NAV} index={SEARCH_INDEX} />
      <div className="min-w-0">{children}</div>
    </div>
  );
}
