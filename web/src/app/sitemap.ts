import type { MetadataRoute } from "next";
import { SITE_URL } from "@/config";
import { ALL_DOCS } from "@/content/docs";

// Written to out/sitemap.xml at build time (static export).
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const paths = ["/", "/demo", ...ALL_DOCS.map((p) => p.href), "/privacy", "/terms"];
  return paths.map((path) => ({
    url: `${SITE_URL}${path === "/" ? "" : path}`,
    changeFrequency: path === "/demo" ? "always" : "weekly",
    priority: path === "/" ? 1 : path.startsWith("/docs") || path === "/demo" ? 0.7 : 0.3,
  }));
}
