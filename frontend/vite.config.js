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
    // expose dev server to local network
    host: '0.0.0.0'
  },
  build: {
    chunkSizeWarningLimit: 600,
    cssCodeSplit: false,
    target: 'esnext'
  },
  envPrefix: 'MASCOPE_'
})
