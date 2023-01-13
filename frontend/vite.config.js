import { defineConfig, loadEnv } from 'vite'
import { createVuePlugin } from 'vite-plugin-vue2';
import path from 'path';

export default ({ mode }) => {
    const dotEnvPath = path.resolve(process.cwd() + '/..');
    process.env = Object.assign(
        process.env,
        // loadEnv(mode, dotEnvPath, 'MASCOPE_PUBLIC_')
        loadEnv(mode, dotEnvPath, 'MASCOPE_')
        );
    
    return defineConfig({
        plugins: [createVuePlugin()],
        server: {
            port: process.env.MASCOPE_PUBLIC_PORT,
            fs: {
                strict: false,
                allow: [
                     '/data/database/'
                ]
            },
            // proxy: {
            //     '/socket.io': {
            //         target: process.env.MASCOPE_PUBLIC_PROTOCOL+'://'+
            //                 process.env.MASCOPE_PUBLIC_HOST+':'+
            //                 process.env.MASCOPE_PUBLIC_API_PORT,
            //         changeOrigin: true,
            //         ws: true,
            //     }
            // }
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
        // envPrefix: 'MASCOPE_PUBLIC_'
        envPrefix: 'MASCOPE_'
    });
}