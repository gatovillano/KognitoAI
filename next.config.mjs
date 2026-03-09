/** @type {import('next').NextConfig} */
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

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
  transpilePackages: ['react-dnd', 'react-dnd-html5-backend'],
  async redirects() {
    return [
      {
        source: '/.well-known/caldav',
        destination: '/api/caldav/',
        permanent: true,
      },
      {
        source: '/.well-known/carddav',
        destination: '/api/caldav/',
        permanent: true,
      },
    ];
  },
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
      {
        source: '/onlyoffice/:path*',
        destination: 'http://onlyoffice:80/:path*',
      },
    ]
  },
  outputFileTracingRoot: __dirname,
};

export default nextConfig;