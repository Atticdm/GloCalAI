/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  eslint: {
    dirs: ["app", "components", "lib"],
  },
};

module.exports = nextConfig;
