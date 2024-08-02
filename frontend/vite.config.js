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
    // Note: Configures the server to listen on all network interfaces. This setting is needed for accessing
    // the development server (http://192.168.1.249:5173/) not just locally, but also over a local area network.
    host: '0.0.0.0'
  },
  build: {
    chunkSizeWarningLimit: 600,
    cssCodeSplit: false,
    target: 'esnext'
  },
  envPrefix: 'MASCOPE_' // Prefix for environment variables used in the project.
})
