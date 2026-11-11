// The pages' text, by key. English only for now (owner, 2026-11-11); a key
// missing from a language is a build-time test failure (tests/text-keys.spec.ts),
// and at run time shows the key itself, never an empty string.
import en from '../i18n/en.json';

const texts: Record<string, string> = en;

export function t(key: string): string {
  return texts[key] ?? key;
}
