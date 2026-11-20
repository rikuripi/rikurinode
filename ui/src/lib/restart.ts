// Why the node last restarted (D22): one sentence from the node's record of
// this boot (restart.rs), its times in this browser's own time zone and
// locale, as the node has none. It says only what the record shows: no claim
// about funds or data until a check can prove one (owner, 2026-11-19).
// Record: docs/build-records/2026-11-19-boot-cause-sentence.md
import type { LastRestart } from '../generated/LastRestart';
import type { RestartCause } from '../generated/RestartCause';
import { t } from './i18n';

// restart.rs's closed set, as the Rust enum writes it.
export const CAUSES: readonly RestartCause[] = [
  'kernel-crash', 'watchdog', 'rolled-back', 'update-applied', 'clean', 'power-cut', 'unknown', 'first-boot',
];

const time = (value: unknown): value is number => Number.isSafeInteger(value) && (value as number) >= 0;

/** A restart exactly as the node writes it, or undefined: anything else.
 *  The same rules as restart.rs: a clean shutdown and a power cut always
 *  have a last-alive time, a first boot never has one. */
export function parseRestart(value: unknown): LastRestart | undefined {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return undefined;
  const v = value as Record<string, unknown>;
  const { cause, at_unix, last_alive_unix } = v;
  if (Object.keys(v).length !== 3 || !(CAUSES as readonly unknown[]).includes(cause)) return undefined;
  if (!time(at_unix)) return undefined;
  let alive: number | null;
  if (last_alive_unix === null) alive = null;
  else if (time(last_alive_unix)) alive = last_alive_unix;
  else return undefined;
  if ((cause === 'clean' || cause === 'power-cut') && alive === null) return undefined;
  if (cause === 'first-boot' && alive !== null) return undefined;
  return { cause: cause as RestartCause, at_unix, last_alive_unix: alive };
}

/** A Unix time as this browser says a date and time. */
export function when(unix: number): string {
  return new Date(unix * 1000).toLocaleString();
}

/** The sentence for the owner; null is the node saying it could not read it. */
export function sentence(restart: LastRestart | null): string {
  if (restart === null) return t('restart.unread');
  const alive = restart.last_alive_unix;
  return t(`restart.${restart.cause}${alive === null ? '' : '.alive'}`)
    .replace('{at}', when(restart.at_unix))
    .replace('{alive}', alive === null ? '' : when(alive));
}
