
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/predict': 'http://127.0.0.1:8000',
      '/investigation': 'http://127.0.0.1:8000',
      '/rag': 'http://127.0.0.1:8000',
      '/compliance': 'http://127.0.0.1:8000',
    },
  },
})
