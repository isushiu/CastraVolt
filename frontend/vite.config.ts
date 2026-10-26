import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({mode}) => {
  const target = loadEnv(mode,'.','CASTRAVOLT_API_').CASTRAVOLT_API_TARGET || 'http://127.0.0.1:8000';
  return {
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy: {
    '/api': { target, changeOrigin: true },
    '/health': { target, changeOrigin: true },
  } },
  };
});
