// Render tests (D15, TEST-10): the built pages at phone, tablet and desktop
// widths, served by Vite's preview of `dist/`. They run only in the pinned
// Playwright image, whose browsers are inside it (scripts/quality/ui.sh);
// nothing is downloaded at test time.
// Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;

export default defineConfig({
  testDir: 'tests',
  forbidOnly: true,
  retries: 0,
  reporter: 'list',
  use: { baseURL: `http://127.0.0.1:${PORT}` },
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}/cert.html`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
  projects: [
    { name: 'text', testMatch: 'text-keys.spec.ts' },
    { name: 'phone', testMatch: 'render.spec.ts', use: { ...devices['Pixel 7'], viewport: { width: 390, height: 844 } } },
    { name: 'phone-webkit', testMatch: 'render.spec.ts', use: { ...devices['iPhone 13'], viewport: { width: 390, height: 844 } } },
    { name: 'tablet', testMatch: 'render.spec.ts', use: { browserName: 'chromium', viewport: { width: 768, height: 1024 } } },
    { name: 'desktop', testMatch: 'render.spec.ts', use: { browserName: 'chromium', viewport: { width: 1280, height: 860 } } },
  ],
});
