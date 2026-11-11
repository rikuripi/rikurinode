// The owner's pages (5c.3b): claim the node, sign in, see it is yours, sign
// out. The API is stubbed with its real shapes (src/generated, from the Rust
// types); the preview sends the node's CSP, as render.spec.ts checks.
// Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md
import { expect, test, type Page, type Request } from '@playwright/test';
import { readFileSync } from 'node:fs';
import type { ErrorReply } from '../src/generated/ErrorReply';
import type { HubReport } from '../src/generated/HubReport';
import type { SessionInfo } from '../src/generated/SessionInfo';
import type { SessionOpened } from '../src/generated/SessionOpened';
import type { SetupReport } from '../src/generated/SetupReport';

const en: Record<string, string> = JSON.parse(readFileSync(new URL('../src/i18n/en.json', import.meta.url), 'utf8'));
const t = (key: string): string => {
  const text = en[key];
  if (text === undefined) throw new Error(`no text for ${key}`);
  return text;
};

const CODE = 'K7QM-4XD9-TR';
const PASSWORD = 'correct horse battery staple';
const CSRF = 'csrf-token-for-the-test';
const FP = 'AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89';
const UNCLAIMED: SetupReport = { claimed: false, claim: 'armed', ca_fingerprint_sha256: FP, names: ['rikurisetup.local'] };
const CLAIMED: SetupReport = { claimed: true, claim: 'done', ca_fingerprint_sha256: FP, names: ['rikurisetup.local'] };
const OPENED: SessionOpened = { csrf_token: CSRF, issued_unix: 1_800_000_000, expires_unix: 1_802_592_000 };
const INFO: SessionInfo = OPENED;
const NODE_ID = '12345678-9abc-4ef0-8fed-cba987654321';
// 5c.4a: the hub of a node just claimed, not yet named.
const HUB: HubReport = {
  node_id: NODE_ID,
  steps: [
    { step: 'connection', state: 'done' },
    { step: 'owner', state: 'done' },
    { step: 'name', state: 'next' },
    { step: 'bitcoin', state: 'later' },
    { step: 'lightning', state: 'later' },
    { step: 'backup', state: 'later' },
  ],
};

type Answer = { status: number; body?: unknown; headers?: Record<string, string> } | 'offline';

/** Stubs the API: each key is "METHOD /path"; every request is kept.
 *  5c.4a: /home reads the hub, so it answers HUB unless a test says otherwise. */
async function api(page: Page, answers: Record<string, Answer | Answer[]>): Promise<Request[]> {
  const seen: Request[] = [];
  const all: Record<string, Answer | Answer[]> = { 'GET /api/hub': { status: 200, body: HUB }, ...answers };
  const queues = new Map(Object.entries(all).map(([k, v]) => [k, Array.isArray(v) ? [...v] : [v]]));
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    seen.push(req);
    const key = `${req.method()} ${new URL(req.url()).pathname}`;
    const queue = queues.get(key);
    const answer = queue && (queue.length > 1 ? queue.shift() : queue[0]);
    if (!answer) return route.fulfill({ status: 599, body: `no stub for ${key}` });
    if (answer === 'offline') return route.abort();
    return route.fulfill({
      status: answer.status,
      headers: answer.headers,
      contentType: 'application/json',
      body: answer.body === undefined ? '' : JSON.stringify(answer.body),
    });
  });
  return seen;
}

const refused = (error: string, extra: Partial<ErrorReply> = {}): ErrorReply => ({ error, ...extra });

function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  return errors;
}

async function fillClaim(page: Page, code = CODE, password = PASSWORD, confirm = password) {
  await page.getByLabel(t('claim.code')).fill(code);
  await page.getByLabel(t('claim.password'), { exact: true }).fill(password);
  await page.getByLabel(t('claim.confirm')).fill(confirm);
}

test.describe('the secure page leads on by the node\'s state', () => {
  test('an unclaimed node: to the claim', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/');
    await expect(page.getByRole('link', { name: t('secure.claim_link') })).toHaveAttribute('href', '/claim');
  });

  test('a claimed node, signed out: to sign-in', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED }, 'GET /api/session': { status: 401, body: refused('not signed in') } });
    await page.goto('/');
    await expect(page.getByRole('link', { name: t('secure.signin_link') })).toHaveAttribute('href', '/signin');
    await expect(page.getByRole('link', { name: t('secure.claim_link') })).toHaveCount(0);
  });

  test('a claimed node, signed in: to the node', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED }, 'GET /api/session': { status: 200, body: INFO } });
    await page.goto('/');
    await expect(page.getByRole('link', { name: t('secure.home_link') })).toHaveAttribute('href', '/home');
  });
});

test.describe('the claim', () => {
  test('asks for the code and a password typed twice, with the rule, the tip and the warning', async ({ page }) => {
    const errors = watchErrors(page);
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/claim');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('claim.title'));
    await expect(page.getByLabel(t('claim.code'))).toHaveAttribute('autocomplete', 'one-time-code');
    for (const label of [t('claim.password'), t('claim.confirm')]) {
      const field = page.getByLabel(label, { exact: true });
      await expect(field).toHaveAttribute('type', 'password');
      await expect(field).toHaveAttribute('autocomplete', 'new-password');
    }
    await expect(page.getByText(t('claim.tip'))).toBeVisible();
    await expect(page.getByText(t('claim.keep'))).toBeVisible();
    expect(t('claim.keep').toLowerCase()).toContain('password manager');
    await expect(page.getByRole('button', { name: t('claim.submit') })).toBeDisabled();
    expect(await page.locator('form[action]').count()).toBe(0);
    expect(errors).toEqual([]);
  });

  test('submits only when the rule holds and both passwords match', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/claim');
    const submit = page.getByRole('button', { name: t('claim.submit') });
    await fillClaim(page, CODE, 'too short', 'too short');
    await expect(page.getByText(t('claim.rule'))).toHaveAttribute('data-met', 'false');
    await expect(submit).toBeDisabled();
    await fillClaim(page, CODE, PASSWORD, PASSWORD + 'x');
    await expect(page.getByText(t('claim.rule'))).toHaveAttribute('data-met', 'true');
    await expect(page.getByText(t('claim.mismatch'))).toBeVisible();
    await expect(submit).toBeDisabled();
    await fillClaim(page, '', PASSWORD, PASSWORD);
    await expect(submit).toBeDisabled();
    await fillClaim(page);
    await expect(page.getByText(t('claim.mismatch'))).toHaveCount(0);
    await expect(submit).toBeEnabled();
  });

  test('the rule counts characters, as the node does, not bytes', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/claim');
    await fillClaim(page, CODE, 'ééééééééééé', 'ééééééééééé'); // 11 characters, 22 bytes
    await expect(page.getByText(t('claim.rule'))).toHaveAttribute('data-met', 'false');
    await fillClaim(page, CODE, 'éééééééééééé', 'éééééééééééé'); // 12
    await expect(page.getByText(t('claim.rule'))).toHaveAttribute('data-met', 'true');
  });

  test('the show toggle reveals the passwords and hides them again', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/claim');
    const field = page.getByLabel(t('claim.password'), { exact: true });
    await page.getByRole('button', { name: t('password.show') }).click();
    await expect(field).toHaveAttribute('type', 'text');
    await page.getByRole('button', { name: t('password.hide') }).click();
    await expect(field).toHaveAttribute('type', 'password');
  });

  test('a claim sends the code and password once, in the body only, and opens the node', async ({ page }) => {
    const seen = await api(page, {
      'GET /api/setup': { status: 200, body: UNCLAIMED },
      'POST /api/claim': { status: 201, body: OPENED },
      'GET /api/session': { status: 200, body: INFO },
    });
    await page.goto('/claim');
    await fillClaim(page);
    await page.getByRole('button', { name: t('claim.submit') }).click();
    await expect(page).toHaveURL(/\/home$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('home.title'));
    const posts = seen.filter((r) => r.method() === 'POST');
    expect(posts.map((r) => new URL(r.url()).pathname)).toEqual(['/api/claim']);
    expect(posts[0]!.headers()['content-type']).toContain('application/json');
    expect(JSON.parse(posts[0]!.postData() ?? '')).toEqual({ code: CODE, password: PASSWORD });
    for (const r of seen) {
      expect(r.url()).not.toContain(encodeURIComponent(PASSWORD));
      expect(r.url()).not.toContain(CODE);
      if (r !== posts[0]) expect(r.postData() ?? '').not.toContain(PASSWORD);
    }
    expect(page.url()).not.toContain(CODE);
  });

  for (const [why, answer, key, cleared] of [
    ['a wrong code', { status: 401, body: refused('claim refused') }, 'claim.wrong_code', 'code'],
    ['an already claimed node', { status: 409, body: refused('already claimed') }, 'claim.already', 'none'],
    ['the password rule', { status: 422, body: refused('a password needs at least 12 characters (11 given)') }, 'claim.policy', 'passwords'],
    ['a server failure', { status: 500, body: refused('internal error') }, 'form.unknown', 'none'],
    ['no answer', 'offline', 'form.offline', 'none'],
    ['an answer that is not the API\'s', { status: 502, body: '<html>' }, 'form.unknown', 'none'],
    // Repair 1 (verifier I2): the framework's own refusals, in plain text, not the API's shape.
    ['a body too large', { status: 413, body: 'length limit exceeded' }, 'form.unknown', 'none'],
    ['a body the node cannot read', { status: 400, body: 'Failed to parse the request body as JSON' }, 'form.unknown', 'none'],
  ] as const) {
    test(`a refused claim: ${why}`, async ({ page }) => {
      await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED }, 'POST /api/claim': answer as Answer });
      await page.goto('/claim');
      await fillClaim(page);
      await page.getByRole('button', { name: t('claim.submit') }).click();
      await expect(page.getByRole('alert')).toContainText(t(key));
      await expect(page).toHaveURL(/\/claim$/);
      const code = page.getByLabel(t('claim.code'));
      const password = page.getByLabel(t('claim.password'), { exact: true });
      await expect(code).toHaveValue(cleared === 'code' ? '' : CODE);
      await expect(password).toHaveValue(cleared === 'passwords' ? '' : PASSWORD);
      if (key === 'claim.already') {
        await expect(page.getByRole('link', { name: t('secure.signin_link') })).toHaveAttribute('href', '/signin');
      }
    });
  }

  test('the node\'s own words for the password rule are shown', async ({ page }) => {
    const words = 'a password needs at least 12 characters (11 given)';
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED }, 'POST /api/claim': { status: 422, body: refused(words) } });
    await page.goto('/claim');
    await fillClaim(page);
    await page.getByRole('button', { name: t('claim.submit') }).click();
    await expect(page.getByRole('alert')).toContainText(words);
  });

  test('too many tries: the form waits the seconds the node says, counting down', async ({ page }) => {
    await page.clock.install();
    await api(page, {
      'GET /api/setup': { status: 200, body: UNCLAIMED },
      'POST /api/claim': { status: 429, body: refused('too many tries', { retry_after_seconds: 3 }), headers: { 'retry-after': '3' } },
    });
    await page.goto('/claim');
    await fillClaim(page);
    const submit = page.getByRole('button', { name: t('claim.submit') });
    await submit.click();
    const alert = page.getByRole('alert');
    await expect(alert).toContainText(t('form.wait').replace('{seconds}', '3'));
    await expect(submit).toBeDisabled();
    await page.clock.runFor(1000);
    await expect(alert).toContainText(t('form.wait').replace('{seconds}', '2'));
    await page.clock.runFor(2000);
    await expect(submit).toBeEnabled();
  });

  test('a node already claimed says so on arrival and leads to sign-in', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED } });
    await page.goto('/claim');
    await expect(page.getByText(t('claim.already'))).toBeVisible();
    await expect(page.getByRole('link', { name: t('secure.signin_link') })).toHaveAttribute('href', '/signin');
    await expect(page.getByLabel(t('claim.code'))).toHaveCount(0);
  });
});

test.describe('sign-in', () => {
  test('asks for the password, as a current password', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED } });
    await page.goto('/signin');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('signin.title'));
    const field = page.getByLabel(t('signin.password'), { exact: true });
    await expect(field).toHaveAttribute('type', 'password');
    await expect(field).toHaveAttribute('autocomplete', 'current-password');
  });

  test('a right password opens the node; the password is sent once, in the body', async ({ page }) => {
    const seen = await api(page, {
      'GET /api/setup': { status: 200, body: CLAIMED },
      'POST /api/session': { status: 201, body: OPENED },
      'GET /api/session': { status: 200, body: INFO },
    });
    await page.goto('/signin');
    await page.getByLabel(t('signin.password'), { exact: true }).fill(PASSWORD);
    await page.getByRole('button', { name: t('signin.submit') }).click();
    await expect(page).toHaveURL(/\/home$/);
    const posts = seen.filter((r) => r.method() === 'POST');
    expect(posts.length).toBe(1);
    expect(JSON.parse(posts[0]!.postData() ?? '')).toEqual({ password: PASSWORD });
    for (const r of seen) expect(r.url()).not.toContain(encodeURIComponent(PASSWORD));
  });

  test('a wrong password is said plainly, and the field is cleared', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED }, 'POST /api/session': { status: 401, body: refused('sign-in refused') } });
    await page.goto('/signin');
    await page.getByLabel(t('signin.password'), { exact: true }).fill(PASSWORD);
    await page.getByRole('button', { name: t('signin.submit') }).click();
    await expect(page.getByRole('alert')).toContainText(t('signin.wrong'));
    await expect(page.getByLabel(t('signin.password'), { exact: true })).toHaveValue('');
  });

  test('too many tries: the form waits', async ({ page }) => {
    await page.clock.install();
    await api(page, {
      'GET /api/setup': { status: 200, body: CLAIMED },
      'POST /api/session': { status: 429, body: refused('too many tries', { retry_after_seconds: 2 }), headers: { 'retry-after': '2' } },
    });
    await page.goto('/signin');
    await page.getByLabel(t('signin.password'), { exact: true }).fill(PASSWORD);
    const submit = page.getByRole('button', { name: t('signin.submit') });
    await submit.click();
    await expect(page.getByRole('alert')).toContainText(t('form.wait').replace('{seconds}', '2'));
    await expect(submit).toBeDisabled();
    await page.clock.runFor(2000);
    await expect(submit).toBeEnabled();
  });

  // Repair 1 (verifier I2): every other answer is said, and the password is kept to try again.
  for (const [why, answer, key] of [
    ['a server failure', { status: 500, body: refused('internal error') }, 'form.unknown'],
    ['no answer', 'offline', 'form.offline'],
    ['an answer that is not the API\'s', { status: 502, body: '<html>' }, 'form.unknown'],
    ['a body too large', { status: 413, body: 'length limit exceeded' }, 'form.unknown'],
    ['a body the node cannot read', { status: 400, body: 'Failed to parse the request body as JSON' }, 'form.unknown'],
  ] as const) {
    test(`a refused sign-in: ${why}`, async ({ page }) => {
      await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED }, 'POST /api/session': answer as Answer });
      await page.goto('/signin');
      await page.getByLabel(t('signin.password'), { exact: true }).fill(PASSWORD);
      await page.getByRole('button', { name: t('signin.submit') }).click();
      await expect(page.getByRole('alert')).toContainText(t(key));
      await expect(page.getByRole('alert')).not.toContainText(t('signin.wrong'));
      await expect(page).toHaveURL(/\/signin$/);
      await expect(page.getByLabel(t('signin.password'), { exact: true })).toHaveValue(PASSWORD);
    });
  }

  test('an unclaimed node leads to the claim instead', async ({ page }) => {
    await api(page, { 'GET /api/setup': { status: 200, body: UNCLAIMED } });
    await page.goto('/signin');
    await expect(page.getByText(t('signin.unclaimed'))).toBeVisible();
    await expect(page.getByRole('link', { name: t('secure.claim_link') })).toHaveAttribute('href', '/claim');
  });
});

test.describe('the node, signed in', () => {
  test('says it is yours, until when, and signs out with the CSRF token', async ({ page }) => {
    const errors = watchErrors(page);
    const seen = await api(page, {
      'GET /api/session': [{ status: 200, body: INFO }, { status: 401, body: refused('not signed in') }],
      'DELETE /api/session': { status: 204 },
      'GET /api/setup': { status: 200, body: CLAIMED },
    });
    await page.goto('/home');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('home.title'));
    await expect(page.getByText(t('home.until').split('{date}')[0]!.trim())).toBeVisible();
    await page.getByRole('button', { name: t('home.signout') }).click();
    await expect(page).toHaveURL(/\/signin$/);
    const out = seen.find((r) => r.method() === 'DELETE');
    expect(out, 'a sign-out request').toBeTruthy();
    expect(out!.headers()['x-csrf-token']).toBe(CSRF);
    expect(errors).toEqual([]);
  });

  test('signed out already: to sign-in', async ({ page }) => {
    await api(page, { 'GET /api/session': { status: 401, body: refused('not signed in') }, 'GET /api/setup': { status: 200, body: CLAIMED } });
    await page.goto('/home');
    await expect(page).toHaveURL(/\/signin$/);
  });

  test('a sign-out that fails is said, and the page stays', async ({ page }) => {
    await api(page, {
      'GET /api/session': { status: 200, body: INFO },
      'DELETE /api/session': { status: 500, body: refused('internal error') },
    });
    await page.goto('/home');
    await page.getByRole('button', { name: t('home.signout') }).click();
    await expect(page.getByRole('alert')).toContainText(t('form.unknown'));
    await expect(page).toHaveURL(/\/home$/);
  });

  // Repair 1 (verifier I2, N4).
  test('a sign-out with no answer is said, and the page stays', async ({ page }) => {
    await api(page, { 'GET /api/session': { status: 200, body: INFO }, 'DELETE /api/session': 'offline' });
    await page.goto('/home');
    await page.getByRole('button', { name: t('home.signout') }).click();
    await expect(page.getByRole('alert')).toContainText(t('form.offline'));
    await expect(page).toHaveURL(/\/home$/);
  });

  test('a sign-out of a session that has already ended: to sign-in', async ({ page }) => {
    await api(page, {
      'GET /api/session': { status: 200, body: INFO },
      'DELETE /api/session': { status: 401, body: refused('not signed in') },
      'GET /api/setup': { status: 200, body: CLAIMED },
    });
    await page.goto('/home');
    await page.getByRole('button', { name: t('home.signout') }).click();
    await expect(page).toHaveURL(/\/signin$/);
  });
});

// Repair 1 (verifier N4): a session the page cannot read leads nowhere, rather than to a guess.
test('the secure page guesses no way on when the session cannot be read', async ({ page }) => {
  await api(page, { 'GET /api/setup': { status: 200, body: CLAIMED }, 'GET /api/session': 'offline' });
  await page.goto('/');
  await expect(page.getByText(t('state.done'))).toBeVisible();
  for (const key of ['secure.claim_link', 'secure.signin_link', 'secure.home_link']) {
    await expect(page.getByRole('link', { name: t(key) })).toHaveCount(0);
  }
});

// Repair 1 (verifier N2): the owner's pages, like the setup pages in
// render.spec.ts, fit the screen with every control at least 44 px, and are
// drawn under the node's CSP with no violation and no error.
for (const [path, answers, ready] of [
  ['/claim', { 'GET /api/setup': { status: 200, body: UNCLAIMED } }, 'claim.submit'],
  ['/signin', { 'GET /api/setup': { status: 200, body: CLAIMED } }, 'signin.submit'],
  ['/home', { 'GET /api/session': { status: 200, body: INFO } }, 'home.signout'],
] as const) {
  test(`${path} fits, with every control at least 44 px, under the node's CSP`, async ({ page }) => {
    await page.addInitScript(() => {
      const seen: string[] = [];
      (window as unknown as { __violations: string[] }).__violations = seen;
      document.addEventListener('securitypolicyviolation', (e) => seen.push(`${e.violatedDirective} ${e.blockedURI}`));
    });
    const errors = watchErrors(page);
    await api(page, answers as Record<string, Answer>);
    await page.goto(path);
    await expect(page.getByRole('button', { name: t(ready) })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, 'no sideways scroll').toBeLessThanOrEqual(0);
    const small = await page.evaluate(() =>
      [...document.querySelectorAll('a[href], button, input')]
        .filter((el) => (el as HTMLElement).offsetParent !== null)
        .map((el) => ({ text: el.textContent?.trim() || el.id, box: el.getBoundingClientRect() }))
        .filter(({ box }) => box.height < 44 || box.width < 44)
        .map(({ text }) => text),
    );
    expect(small, 'every control at least 44 px').toEqual([]);
    expect(await page.evaluate(() => (window as unknown as { __violations: string[] }).__violations)).toEqual([]);
    expect(errors).toEqual([]);
  });
}

// 5c.4a: /home is the SetupHub. Each step is said in words, its state too
// (never by colour alone), and only the node's own answer marks one done.
// Record: docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md
test.describe('the SetupHub', () => {
  const STEPS = ['connection', 'owner', 'name', 'bitcoin', 'lightning', 'backup'] as const;

  test('lists every step in order, with its state in words, and the node\'s ID', async ({ page }) => {
    const errors = watchErrors(page);
    await api(page, { 'GET /api/session': { status: 200, body: INFO } });
    await page.goto('/home');
    await expect(page.getByRole('heading', { name: t('hub.title') })).toBeVisible();
    const items = page.getByRole('list', { name: t('hub.title') }).getByRole('listitem');
    await expect(items).toHaveCount(STEPS.length);
    for (const [i, step] of STEPS.entries()) {
      const item = items.nth(i);
      const want = HUB.steps[i]!.state;
      await expect(item).toHaveAttribute('data-step', step);
      await expect(item).toHaveAttribute('data-state', want);
      await expect(item).toContainText(t(`hub.step.${step}`));
      await expect(item).toContainText(t(`hub.state.${want}`));
    }
    await expect(items.nth(2)).toContainText(t('hub.name_next'));
    await expect(page.getByText(t('hub.node_id'))).toBeVisible();
    await expect(page.getByText(NODE_ID)).toBeVisible();
    expect(errors).toEqual([]);
  });

  test('a step the node could not read says so, and is never shown as done', async ({ page }) => {
    const hub: HubReport = { ...HUB, steps: HUB.steps.map((s) => (s.step === 'name' ? { ...s, state: 'unknown' } : s)) };
    await api(page, { 'GET /api/session': { status: 200, body: INFO }, 'GET /api/hub': { status: 200, body: hub } });
    await page.goto('/home');
    const name = page.locator('li[data-step="name"]');
    await expect(name).toHaveAttribute('data-state', 'unknown');
    await expect(name).toContainText(t('hub.state.unknown'));
    await expect(name).not.toContainText(t('hub.state.done'));
  });

  test('a named node: the name is done', async ({ page }) => {
    const hub: HubReport = { ...HUB, steps: HUB.steps.map((s) => (s.step === 'name' ? { ...s, state: 'done' } : s)) };
    await api(page, { 'GET /api/session': { status: 200, body: INFO }, 'GET /api/hub': { status: 200, body: hub } });
    await page.goto('/home');
    const name = page.locator('li[data-step="name"]');
    await expect(name).toHaveAttribute('data-state', 'done');
    await expect(name).toContainText(t('hub.state.done'));
    await expect(name).not.toContainText(t('hub.name_next'));
  });

  test('signed out when the hub is read: to sign-in', async ({ page }) => {
    await api(page, {
      'GET /api/session': { status: 200, body: INFO },
      'GET /api/hub': { status: 401, body: refused('sign-in required') },
      'GET /api/setup': { status: 200, body: CLAIMED },
    });
    await page.goto('/home');
    await expect(page).toHaveURL(/\/signin$/);
  });

  for (const [why, answer] of [
    ['the node fails', { status: 500, body: refused('internal error') }],
    ['no answer', 'offline'],
    ['an answer that is not the hub', { status: 200, body: { node_id: NODE_ID, steps: [{ step: 'name', state: 'finished' }] } }],
    ['a step the page does not know', { status: 200, body: { node_id: NODE_ID, steps: [{ step: 'tor', state: 'done' }] } }],
    ['no node ID', { status: 200, body: { node_id: '', steps: HUB.steps } }],
    ['a step listed twice', { status: 200, body: { node_id: NODE_ID, steps: [...HUB.steps, HUB.steps[0]] } }],
  ] as const) {
    test(`the hub unread when ${why}: said, never a guess, and sign-out stays`, async ({ page }) => {
      await api(page, { 'GET /api/session': { status: 200, body: INFO }, 'GET /api/hub': answer as Answer });
      await page.goto('/home');
      await expect(page.getByText(t('hub.unreadable'))).toBeVisible();
      await expect(page.locator('li[data-step]')).toHaveCount(0);
      await expect(page.getByText(t('hub.state.done'), { exact: true })).toHaveCount(0);
      await expect(page.getByRole('button', { name: t('home.signout') })).toBeVisible();
    });
  }
});
