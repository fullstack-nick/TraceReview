import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/app/' : '/',
  server: {
    host: '127.0.0.1', port: 5173, strictPort: true,
    proxy: { '/api': { target: process.env.TRACEREVIEW_API_URL || 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: { chunkSizeWarningLimit: 1500 },
}))
