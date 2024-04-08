import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

import path from 'path'

export default ({ mode }) => {
  const envDir = path.resolve(process.cwd() + '/..')
  const env = loadEnv(mode, envDir, 'MASCOPE_PUBLIC_')

  return defineConfig({
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: { port: env.MASCOPE_PUBLIC_PORT },
    build: {
      chunkSizeWarningLimit: 600,
      cssCodeSplit: false,
      target: 'esnext'
    },
    envPrefix: 'MASCOPE_PUBLIC_',
    envDir
  })
}
