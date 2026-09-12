import path from "path";

import { federation } from "@module-federation/vite";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { dependencies } from "./package.json";

export default defineConfig(() => {
  return {
    server: {
      fs: {
        allow: [".", "../shared"],
      },
      proxy: {
        "/ui/tak": {
          target: "http://localhost:4174",
          rewrite: (path) => path.replace(/^\/ui\/tak/, ""),
        },
      },
    },
    build: {
      target: "chrome89",
      emptyOutDir: true,
      rollupOptions: {
        preserveEntrySignatures: "exports-only",
      },
    },
    plugins: [
      federation({
        filename: "remoteEntry.js",
        name: "tak-integration",
        exposes: {
          "./remote-ui": "./src/App.tsx",
        },
        remotes: {},
        shared: {
          react: {
            requiredVersion: dependencies.react,
            singleton: true,
          },
          i18next: {
            requiredVersion: dependencies.i18next,
            singleton: true,
          },
          "react-i18next": {
            requiredVersion: dependencies["react-i18next"],
            singleton: true,
          },
          "@tanstack/react-router": {
            requiredVersion: dependencies["@tanstack/react-router"],
            singleton: true,
          },
        },
        runtime: "@module-federation/enhanced/runtime",
      }),
      react(),
      tailwindcss(),
    ],
    resolve: {
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    define: {
      __USE_GLOBAL_CSS__: JSON.stringify(
        process.env.VITE_USE_GLOBAL_CSS === "true",
      ),
    },
  };
});
