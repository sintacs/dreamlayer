import { defineConfig } from "vite";

export default defineConfig(({ mode }) => ({
  base: "./",
  build: {
    // Overlay images carry meaning in their exact alpha; never inline or
    // recompress them through the bundler.
    assetsInlineLimit: 0,
    target: "es2022",
    rollupOptions: {
      // The single-file artifact build cannot lazy-load a second chunk, so
      // fold the motion module in; its runtime reduced-motion gate still holds.
      output: { inlineDynamicImports: mode === "artifact" },
    },
  },
}));
