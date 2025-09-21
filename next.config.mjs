/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    domains: ['apibase.gatoslibres.art'],
  },
  // Eliminado allowedDevOrigins de experimental ya que no es una opción válida en Next.js 15.4.1
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
