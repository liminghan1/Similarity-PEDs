import type { NextConfig } from "next";

// GitHub Pages serves this repo at https://<user>.github.io/<repo>/, not the domain root, so
// every asset/link needs that prefix -- but only for the GH Pages build. Local dev/build (the
// FastAPI dashboard on localhost:3000) must keep basePath empty, so this is opt-in via an env
// var the deploy workflow sets, not always-on.
const isGithubPagesBuild = process.env.GITHUB_PAGES === "true";
const repoName = "Similarity-PEDs";

const nextConfig: NextConfig = {
  // Every page here is a Server Component that fetches real data at build time (from the
  // FastAPI backend, which the deploy workflow runs against a freshly-ingested database) --
  // there is no request-time server, so a static export is both possible and the right fit.
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath: isGithubPagesBuild ? `/${repoName}` : "",
  assetPrefix: isGithubPagesBuild ? `/${repoName}/` : "",
};

export default nextConfig;
