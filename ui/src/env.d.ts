/// <reference types="svelte" />
// Vite's client types declare the side-effect imports of the pages' CSS
// (src/*/main.ts), which TypeScript 6 refuses without a declaration
// (repair 2: docs/build-records/2026-11-11-5c3a-ui-pipeline.md).
/// <reference types="vite/client" />
