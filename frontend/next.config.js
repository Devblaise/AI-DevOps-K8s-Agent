/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output keeps the production Docker image small.
  output: "standalone",
  // Hide the Next.js dev indicator badge (bottom-left logo) during development.
  devIndicators: false,
};

module.exports = nextConfig;
