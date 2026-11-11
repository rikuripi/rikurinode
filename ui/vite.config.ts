// The setup pages' build: two pages, every script and style a file of its
// own (the control plane's CSP allows no inline code and no outside origin),
// nothing inlined as a data: URL, no source maps shipped.
// Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vite';
import { CSP } from './src/csp';

export default defineConfig({
  plugins: [svelte()],
  // The render tests load the build through `vite preview`: with the node's own policy.
  preview: { headers: { 'Content-Security-Policy': CSP } },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    assetsInlineLimit: 0,
    modulePreload: { polyfill: false },
    sourcemap: false,
    rolldownOptions: {
      // index.html: the secure page, served only over TLS;
      // cert.html: the certificate screen, served in the clear at /.
      input: { index: 'index.html', cert: 'cert.html' },
    },
  },
});
