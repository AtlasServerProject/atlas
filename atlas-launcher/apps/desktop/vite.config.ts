import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({ command }) => ({
  plugins: [
    react(),
    {
      name: 'atlas-dev-csp',
      transformIndexHtml(html) {
        return command === 'serve'
          ? html.replace("script-src 'self';", "script-src 'self' 'unsafe-inline';")
          : html;
      },
    },
  ],
  base: './',
  build: { outDir: 'dist/renderer' },
  server: { host: '127.0.0.1', port: 5179, strictPort: true },
}));
