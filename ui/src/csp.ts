// The control plane's Content-Security-Policy for the setup pages, as
// control-plane/crates/rikuri-control/src/ui.rs sends it. The render tests'
// preview sends it too (vite.config.ts), so a page the node's policy would
// break fails there; scripts/quality/tests/test_workflows.py keeps the two equal.
// Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
export const CSP =
  "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'";
