import { defineConfig, loadEnv } from 'vite'
import { createVuePlugin } from 'vite-plugin-vue2';
import path from 'path';

export default ({ mode }) => {
    const dotEnvPath = path.resolve(process.cwd() + '/..');
    process.env = Object.assign(
        process.env,
        loadEnv(mode, dotEnvPath, 'MASCOPE_PUBLIC_')
        );
    
    return defineConfig({
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
                    target: process.env.MASCOPE_PUBLIC_API_PROTOCOL+'://'+process.env.MASCOPE_PUBLIC_API_HOST+':'+process.env.MASCOPE_PUBLIC_API_PORT,
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
        envPrefix: 'MASCOPE_PUBLIC_'
    });
}