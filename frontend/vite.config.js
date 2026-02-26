import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/agentplatform',
  server: {
    port: 8014,
    host: true,
    allowedHosts: ['test4.txcaix.com', 'txcai.txcaix.com'],
    proxy: {
      '/agentplatform/api': {
        target: 'http://localhost:8013',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/agentplatform\/api/, ''),
      }
    },
    cors: { origin: '*' }
  },
  preview: {
    port: 8014,
    host: true
  }
})
