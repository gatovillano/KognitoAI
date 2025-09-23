/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['apibase.gatoslibres.art'],
  },
  experimental: {},
  async rewrites() {
    return [
      {
        source: '/media/:path*',
        destination: 'https://apibase.gatoslibres.art/media/:path*',
      },
    ]
  },
};

export default nextConfig;