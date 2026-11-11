// Every text key in every shipped language (D15). English only for now
// (owner, 2026-11-11: "English, ready for more"); a new language is a new
// file in src/i18n/ with exactly English's keys.
// Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
import { expect, test } from '@playwright/test';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const SRC = new URL('../src/', import.meta.url).pathname;
const I18N = join(SRC, 'i18n');

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return name === 'i18n' || name === 'generated' ? [] : sources(path);
    return /\.(svelte|ts)$/.test(name) ? [path] : [];
  });
}

const languages = readdirSync(I18N).filter((f) => f.endsWith('.json'));
const keysOf = (file: string) => Object.keys(JSON.parse(readFileSync(join(I18N, file), 'utf8'))).sort();

test('English is shipped', () => {
  expect(languages).toContain('en.json');
});

test('every language has exactly English\'s keys, none empty', () => {
  const en = keysOf('en.json');
  for (const file of languages) {
    expect(keysOf(file), file).toEqual(en);
    const texts: Record<string, string> = JSON.parse(readFileSync(join(I18N, file), 'utf8'));
    expect(Object.entries(texts).filter(([, v]) => typeof v !== 'string' || v.trim() === '').map(([k]) => k), file).toEqual([]);
  }
});

test('every key the code uses exists, and every key is used', () => {
  const en = new Set(keysOf('en.json'));
  const used = new Set<string>();
  const dynamic = new Set<string>();
  for (const file of sources(SRC)) {
    const text = readFileSync(file, 'utf8');
    for (const m of text.matchAll(/\bt\(\s*'([\w.]+)'\s*\)/g)) used.add(m[1]);
    // A key built at run time names its prefix: t(`steps.${device}.1`)
    for (const m of text.matchAll(/\bt\(\s*`([\w.]+)\$\{/g)) dynamic.add(m[1]);
  }
  expect([...used].filter((k) => !en.has(k)), 'keys used but missing').toEqual([]);
  const unused = [...en].filter((k) => !used.has(k) && ![...dynamic].some((p) => k.startsWith(p)));
  expect(unused, 'keys never used').toEqual([]);
});
