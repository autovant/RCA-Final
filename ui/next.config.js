module.exports = {
  reactStrictMode: true,
  output: 'standalone',
  eslint: {
    // Disable ESLint during production builds
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable type checking during builds (types will be checked in dev)
    ignoreBuildErrors: true,
  },
};
