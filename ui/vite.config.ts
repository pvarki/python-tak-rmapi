import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { federation } from '@module-federation/vite';
import path from 'path';

export default defineConfig(({ mode }) => {
  const isProd = mode === 'production';

  return {
    plugins: [
      react(),
      federation({
        name: 'tak-integration',
        filename: 'remoteEntry.js',
        exposes: {
          './remote-ui': './src/App.tsx',
        },
        shared: {
          react: { singleton: true, requiredVersion: '18.3.1' },
          'react-dom': { singleton: true, requiredVersion: '18.3.1' },
        },
        runtime: '@module-federation/enhanced/runtime',
      }),
    ],
    build: {
      target: 'esnext',
      outDir: 'dist',
      emptyOutDir: true,
      rollupOptions: {
        preserveEntrySignatures: 'exports-only',
      },
    },
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
  };
});
