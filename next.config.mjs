/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'apibase.gatoslibres.art',
        port: '',
        pathname: '/media/**',
      },
    ],
    minimumCacheTTL: 600,
  },
  experimental: {},
  async rewrites() {
    return [
      {
        source: '/media/:path*',
        destination: 'https://apibase.gatoslibres.art/media/:path*',
      },
      {
        source: '/api/:path*',
        destination: 'https://apibase.gatoslibres.art/api/:path*',
      },
    ]
  },
};

export default nextConfig;