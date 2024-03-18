import { defineConfig, loadEnv } from "vite";
import vue from '@vitejs/plugin-vue';
import path from "path";

export default ({ mode }) => {
  const dotEnvPath = path.resolve(process.cwd() + "/..");
  process.env = Object.assign(
    process.env,
    loadEnv(mode, dotEnvPath, "MASCOPE_PUBLIC_")
  );

  return defineConfig({
    plugins: [vue()],
    server: {
      port: process.env.MASCOPE_PUBLIC_PORT,
    },
    resolve: {
      alias: {
        $lib: path.resolve(__dirname, "src/lib/"),
        $api: path.resolve(__dirname, "src/api.js")
      }
    },
    build: {
      chunkSizeWarningLimit: 600,
      cssCodeSplit: false,
      target: "esnext",
    },
    envPrefix: "MASCOPE_PUBLIC_",
  });
};
