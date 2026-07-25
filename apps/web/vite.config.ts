import react from '@vitejs/plugin-react';
import { TanStackRouterVite } from '@tanstack/router-plugin/vite';
import { resolve } from 'path';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  return {
  plugins: [TanStackRouterVite(), react()],

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },

  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: env.VITE_API_PROXY_TARGET || 'http://localhost:7000',
        changeOrigin: true,
      },
    },
  },

  build: {
    target: 'es2022',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
            return 'vendor';
          }
          if (id.includes('node_modules/@tanstack/react-router')) {
            return 'router';
          }
          if (id.includes('node_modules/@tanstack/react-query')) {
            return 'query';
          }
        },
      },
    },
  },
  };
});
