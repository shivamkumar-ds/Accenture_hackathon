// Phase 1.5 finding #10 — no ESLint config existed despite the codebase
// already scattering `// eslint-disable-next-line react-hooks/exhaustive-deps`
// comments (TenderDetail.tsx, Missions.tsx, Dashboard.tsx, Capabilities.tsx,
// Evaluation.tsx). Those were no-ops until now — nothing linted the project,
// so nothing was actually being suppressed. This is that lint.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // Unused vars/params are already caught by tsconfig's
      // noUnusedLocals/noUnusedParameters (Phase 1.5 finding #14) --
      // avoid a duplicate, differently-configured check here.
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
  // Prettier last -- turns off any ESLint formatting rules that would
  // conflict with Prettier's own formatting, per eslint-config-prettier's
  // own documented usage.
  prettierConfig
);
