// GET /api/setup, read through the type generated from the Rust one
// (src/generated, ts-rs). Anything that is not exactly a setup report is
// `null`: the page then says the state is unknown (EVID-02), never a default.
import type { SetupClaim } from '../generated/SetupClaim';
import type { SetupReport } from '../generated/SetupReport';

export const CLAIMS: readonly SetupClaim[] = ['done', 'armed', 'expired', 'retired', 'unarmed'];

export function parseSetup(value: unknown): SetupReport | null {
  if (typeof value !== 'object' || value === null) return null;
  const v = value as Record<string, unknown>;
  const claim = v['claim'];
  const names = v['names'];
  if (typeof v['claimed'] !== 'boolean') return null;
  if (typeof claim !== 'string' || !(CLAIMS as readonly string[]).includes(claim)) return null;
  if (typeof v['ca_fingerprint_sha256'] !== 'string') return null;
  if (!Array.isArray(names) || !names.every((n) => typeof n === 'string')) return null;
  return {
    claimed: v['claimed'],
    claim: claim as SetupClaim,
    ca_fingerprint_sha256: v['ca_fingerprint_sha256'],
    names: names as string[],
  };
}

export async function readSetup(): Promise<SetupReport | null> {
  try {
    const reply = await fetch('/api/setup', { headers: { accept: 'application/json' }, cache: 'no-store' });
    if (!reply.ok) return null;
    return parseSetup(await reply.json());
  } catch {
    return null;
  }
}
