/** @type {import('next').NextConfig} */
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const apiServerUrl = process.env.NEXT_PUBLIC_API_URL || 'https://apibase.cuerpolibre.cl';
let apiHostname = 'apibase.cuerpolibre.cl';
try {
  const parsedUrl = new URL(apiServerUrl);
  apiHostname = parsedUrl.hostname;
} catch (e) {
  // Fallback if parsing fails
}

const nextConfig = {
  allowedDevOrigins: ['kognito.cuerpolibre.cl', 'webapp3.cuerpolibre.cl', 'kognitoai.cloud'],
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: apiServerUrl.startsWith('https') ? 'https' : 'http',
        hostname: apiHostname,
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
        source: '/',
        destination: '/presentacion',
        permanent: false,
      },
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
        destination: `${apiServerUrl}/media/:path*`,
      },
      {
        source: '/tmp/pollinations_images/:path*',
        destination: `${apiServerUrl}/tmp/pollinations_images/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${apiServerUrl}/api/:path*`,
      },
      {
        source: '/onlyoffice/:path*',
        destination: 'http://host.docker.internal:8081/:path*',
      },
    ]
  },
  outputFileTracingRoot: __dirname,
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        ...config.watchOptions,
        ignored: [
          '**/node_modules/**',
          '**/.next/**',
          '**/.venv/**',
          '**/venv_host/**',
          '**/.git/**',
          '**/media/**',
          '**/thumbnails/**',
          '**/storage/**',
          '**/tmp/**',
          '**/data-gym-cache/**',
          '**/logs/**',
          '**/alembic/**'
        ]
      };
    }
    return config;
  },
};

export default nextConfig;