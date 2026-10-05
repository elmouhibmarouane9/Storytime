import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/browser",
  use: { baseURL: "http://localhost:8889", headless: true },
  webServer: {
    command: `${process.env.NETLIFY_CLI ?? "netlify"} dev --port 8889`,
    url: "http://localhost:8889",
    reuseExistingServer: true,
    timeout: 120000,
    stdout: "ignore",
    stderr: "ignore",
  },
});
