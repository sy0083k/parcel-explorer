import { mergeConfig, defineConfig } from "vitest/config";

import viteConfig from "./vite.config";

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: "jsdom",
      environmentOptions: {
        jsdom: {
          url: "http://testserver/",
        },
      },
      include: ["src/**/*.test.ts"],
      setupFiles: ["src/test/setup.ts"],
      restoreMocks: true,
      clearMocks: true,
    },
  })
);
