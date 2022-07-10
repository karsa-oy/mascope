import { defineConfig } from 'vite';
import { createVuePlugin } from 'vite-plugin-vue2';
import path from 'path';

export default defineConfig({
    plugins: [createVuePlugin()],
    server: {
        port: 8080
    },
    resolve: {
        alias: [
            {
                find: '$lib',
                replacement: path.resolve(__dirname, 'src/lib/')
            },
            {
                find: '$store',
                replacement: path.resolve(__dirname, 'src/store/'),
            },
        ]
    },
    build: {
        chunkSizeWarningLimit: 600,
        cssCodeSplit: false
    },
    optimizeDeps: {
        exclude: ['vue-plotly']
    }
});