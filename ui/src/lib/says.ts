// What a form says for the outcomes every call shares (5c.3b).
import type { Outcome } from './api';
import { t } from './i18n';

export function waitText(seconds: number): string {
  return t('form.wait').replace('{seconds}', String(seconds));
}

/** The shared outcomes' words; `null` for those a page words itself. */
export function shared(outcome: Outcome<unknown>): string | null {
  switch (outcome.kind) {
    case 'offline':
      return t('form.offline');
    case 'unknown':
      return t('form.unknown');
    default:
      return null;
  }
}
