// The owner's API calls (5c.3b), through the types generated from the Rust
// ones (src/generated, ts-rs). Every answer becomes one outcome, and anything
// that is not exactly the API's shape is "unknown", never a guess (EVID-02).
// Secrets travel only in a JSON body to the same origin, never in a URL.
// Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md
import type { ClaimRequest } from '../generated/ClaimRequest';
import type { ErrorReply } from '../generated/ErrorReply';
import type { HubReport } from '../generated/HubReport';
import type { HubStep } from '../generated/HubStep';
import type { SetupStep } from '../generated/SetupStep';
import type { StepState } from '../generated/StepState';
import type { SessionInfo } from '../generated/SessionInfo';
import type { SessionOpened } from '../generated/SessionOpened';
import type { SignInRequest } from '../generated/SignInRequest';

export type Outcome<T> =
  | { kind: 'ok'; value: T }
  | { kind: 'refused'; status: number; error: string }
  | { kind: 'wait'; seconds: number }
  | { kind: 'offline' }
  | { kind: 'unknown' };

const CSRF_HEADER = 'x-csrf-token';

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

export function parseErrorReply(value: unknown): ErrorReply | null {
  const v = record(value);
  if (!v || typeof v['error'] !== 'string') return null;
  const wait = v['retry_after_seconds'];
  if (wait !== undefined && !(Number.isInteger(wait) && (wait as number) >= 0)) return null;
  return wait === undefined ? { error: v['error'] } : { error: v['error'], retry_after_seconds: wait as number };
}

export function parseSession(value: unknown): SessionInfo | SessionOpened | null {
  const v = record(value);
  if (!v) return null;
  const { csrf_token, issued_unix, expires_unix } = v;
  if (typeof csrf_token !== 'string' || csrf_token === '') return null;
  if (!Number.isInteger(issued_unix) || !Number.isInteger(expires_unix)) return null;
  return { csrf_token, issued_unix: issued_unix as number, expires_unix: expires_unix as number };
}

// 5c.4a: the hub's closed sets, as the Rust enums write them (hub.rs).
const STEPS: readonly SetupStep[] = ['connection', 'owner', 'name', 'bitcoin', 'lightning', 'backup'];
const STATES: readonly StepState[] = ['done', 'next', 'later', 'unknown'];

/** A hub exactly as the node writes it, or null: a step or state this page
 *  does not know, a step twice, or no node ID makes the whole reply unreadable. */
export function parseHub(value: unknown): HubReport | null {
  const v = record(value);
  if (!v || typeof v['node_id'] !== 'string' || v['node_id'] === '' || !Array.isArray(v['steps'])) return null;
  const steps: HubStep[] = [];
  for (const item of v['steps']) {
    const s = record(item);
    const step = s?.['step'];
    const state = s?.['state'];
    if (!(STEPS as readonly unknown[]).includes(step) || !(STATES as readonly unknown[]).includes(state)) return null;
    if (steps.some((seen) => seen.step === step)) return null; // a step twice is not the node's list
    steps.push({ step: step as SetupStep, state: state as StepState });
  }
  return { node_id: v['node_id'], steps };
}

async function body(reply: Response): Promise<unknown> {
  try {
    return await reply.json();
  } catch {
    return undefined;
  }
}

/** One call: `ok` only for the status this call expects and a body `parse` accepts. */
async function call<T>(
  method: string,
  path: string,
  expect: number,
  parse: (value: unknown) => T | null,
  init: { json?: unknown; headers?: Record<string, string> } = {},
): Promise<Outcome<T>> {
  let reply: Response;
  try {
    reply = await fetch(path, {
      method,
      cache: 'no-store',
      credentials: 'same-origin',
      headers: {
        accept: 'application/json',
        ...(init.json === undefined ? {} : { 'content-type': 'application/json' }),
        ...init.headers,
      },
      body: init.json === undefined ? undefined : JSON.stringify(init.json),
    });
  } catch {
    return { kind: 'offline' };
  }
  if (reply.status === expect) {
    const value = parse(expect === 204 ? null : await body(reply));
    return value === null ? { kind: 'unknown' } : { kind: 'ok', value };
  }
  const refusal = parseErrorReply(await body(reply));
  if (reply.status === 429) {
    const seconds = refusal?.retry_after_seconds ?? Number(reply.headers.get('retry-after'));
    return Number.isInteger(seconds) && seconds > 0 ? { kind: 'wait', seconds } : { kind: 'unknown' };
  }
  if (refusal && reply.status >= 400 && reply.status < 500) {
    return { kind: 'refused', status: reply.status, error: refusal.error };
  }
  return { kind: 'unknown' };
}

export function claim(request: ClaimRequest): Promise<Outcome<SessionOpened>> {
  return call('POST', '/api/claim', 201, parseSession, { json: request });
}

export function signIn(request: SignInRequest): Promise<Outcome<SessionOpened>> {
  return call('POST', '/api/session', 201, parseSession, { json: request });
}

/** The session behind this browser's cookie: ok, refused 401 (signed out), or another outcome. */
export function readSession(): Promise<Outcome<SessionInfo>> {
  return call('GET', '/api/session', 200, parseSession);
}

/** What setup still needs: ok, refused 401 (signed out), or another outcome. */
export function readHub(): Promise<Outcome<HubReport>> {
  return call('GET', '/api/hub', 200, parseHub);
}

export function signOut(csrf: string): Promise<Outcome<true>> {
  return call('DELETE', '/api/session', 204, () => true, { headers: { [CSRF_HEADER]: csrf } });
}
