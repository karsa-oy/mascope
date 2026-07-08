import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // This alias configuration helps in resolving paths relative to the src directory.
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    // expose dev server to local network if option is set
    host: process.env.MASCOPE_DEVHOST ? '0.0.0.0' : 'localhost',
    // listen port; overridden per-instance so several checkouts can run
    // their own dev server on one machine (see `mascope dev run --instance`)
    port: Number(process.env.MASCOPE_FRONTEND_PORT) || 5173
  },
  build: {
    chunkSizeWarningLimit: 600,
    cssCodeSplit: false,
    target: 'esnext'
  },
  envPrefix: 'MASCOPE_'
})
