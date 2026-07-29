import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

// Settings' "About" section shows the real app version rather than a
// fabricated one -- Vite doesn't expose package.json to the client by
// default, so it's injected at build time as a string constant. Read once
// here (build-time only, never re-read at runtime) rather than importing
// package.json directly, which would pull the whole file (scripts,
// dependency list, etc.) into the client bundle.
const pkg = JSON.parse(readFileSync(fileURLToPath(new URL("./package.json", import.meta.url)), "utf-8"));

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
});
