import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/agents': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
      '/sessions': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
      '/teams': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
      '/config': {
        target: 'http://localhost:7777',
        changeOrigin: true,
      },
    }
  }
})
