import type { NextConfig } from 'next';
const config: NextConfig = {
  output: 'standalone',
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  async rewrites() {
    // Browser calls stay same-origin during npm run dev/start as well as Compose.
    return [{source:'/api/:path*',destination:`${process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000'}/api/:path*`}];
  }
};
export default config;
