/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the FastAPI backend serves the built UI from the same origin
  // (one Railway deploy for API + UI). NEXT_PUBLIC_API_URL is auto-inlined by
  // Next; left empty at build time the client calls /api/... same-origin.
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
};

module.exports = nextConfig;
