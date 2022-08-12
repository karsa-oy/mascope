import { defineConfig } from 'vite'
import { createVuePlugin } from 'vite-plugin-vue2';
import path from 'path';

export default defineConfig({
    plugins: [createVuePlugin()],
    server: {
        port: 8080,
        fs: {
            strict: false,
            allow: [
                '/data/database/'
            ]
        },
        proxy: {
            '/socket.io': {
                target: 'ws://127.0.0.1:8090',
                changeOrigin: true,
                ws: true,
            }
        }
    },
    resolve: {
        alias: [
            {
                find: '$lib',
                replacement: path.resolve(__dirname, 'src/lib/')
            },
            {
                find: '$api',
                replacement: path.resolve(__dirname, 'src/api.js')
            },
        ]
    },
    build: {
        chunkSizeWarningLimit: 600,
        cssCodeSplit: false,
        target: "esnext"
    },
    envPrefix: 'MASCOPE_PUBLIC_',
});