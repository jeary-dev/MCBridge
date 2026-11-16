import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Fully static site for Cloudflare Pages: `npm run build` writes ./out
  output: "export",
  trailingSlash: false,
  images: { unoptimized: true },
  turbopack: {
    root: process.cwd(),
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
