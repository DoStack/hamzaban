import { defineConfig } from "vite";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  build: {
    outDir: "static/build",
    emptyOutDir: false,
    rollupOptions: {
      input: "frontend/app.jsx",
      output: {
        entryFileNames: "app.js",
      },
    },
  },
});
