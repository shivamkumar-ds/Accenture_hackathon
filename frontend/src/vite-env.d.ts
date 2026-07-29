/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Build-time constant injected by vite.config.ts's `define` -- the real
// frontend package.json version, shown on Settings' About section. Not a
// runtime value; substituted with a literal string at build time.
declare const __APP_VERSION__: string;
