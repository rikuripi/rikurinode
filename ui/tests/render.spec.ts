// The certificate screen and the secure page as a browser draws them.
// Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md
import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { CSP } from '../src/csp';

const en: Record<string, string> = JSON.parse(readFileSync(new URL('../src/i18n/en.json', import.meta.url), 'utf8'));
const t = (key: string): string => {
  const text = en[key];
  if (text === undefined) throw new Error(`no text for ${key}`);
  return text;
};

const FINGERPRINT = 'AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89';
const DEVICES = ['iphone', 'android', 'mac', 'windows', 'linux'];

async function stubSetup(page: Page, body: object | null, status = 200) {
  await page.route('**/api/setup', (route) =>
    body === null ? route.abort() : route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) }),
  );
}

function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push(e.message));
  return errors;
}

async function assertFits(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'no sideways scroll').toBeLessThanOrEqual(0);
  const small = await page.evaluate(() =>
    [...document.querySelectorAll('a[href], button')]
      .filter((el) => (el as HTMLElement).offsetParent !== null)
      .map((el) => ({ text: el.textContent?.trim() ?? '', box: el.getBoundingClientRect() }))
      .filter(({ box }) => box.height < 44 || box.width < 44)
      .map(({ text }) => text),
  );
  expect(small, 'every control at least 44 px').toEqual([]);
}

test.describe('the certificate screen', () => {
  test('offers the certificate, a guide per device, and the way on', async ({ page }) => {
    const errors = watchErrors(page);
    await page.goto('/cert.html');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('cert.title'));
    const download = page.getByRole('link', { name: t('cert.download') });
    await expect(download).toHaveAttribute('href', '/ca.crt');
    await expect(download).toHaveAttribute('download', '');
    for (const device of DEVICES) {
      await page.getByRole('button', { name: t(`device.${device}`) }).click();
      await expect(page.getByRole('button', { name: t(`device.${device}`) })).toHaveAttribute('aria-pressed', 'true');
      const steps = page.getByRole('list', { name: t('cert.steps') }).getByRole('listitem');
      await expect(steps.first()).toBeVisible();
      expect(await steps.count()).toBeGreaterThanOrEqual(2);
      await expect(steps.first()).toContainText(t(`steps.${device}.1`).replace(/<\/?b>/g, ''));
    }
    await expect(page.getByRole('link', { name: t('cert.continue') })).toHaveAttribute('href', '/setup');
    await assertFits(page);
    expect(errors).toEqual([]);
  });

  test('never asks for anything and never calls the API', async ({ page }) => {
    const calls: string[] = [];
    page.on('request', (r) => { if (new URL(r.url()).pathname.startsWith('/api/')) calls.push(r.url()); });
    await page.goto('/cert.html');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    expect(await page.locator('input, textarea, select, form').count()).toBe(0);
    expect(calls).toEqual([]);
  });
});

test.describe('the secure page', () => {
  test('says the connection is private, and how to check it against the node', async ({ page }) => {
    const errors = watchErrors(page);
    await stubSetup(page, { claimed: false, claim: 'armed', ca_fingerprint_sha256: FINGERPRINT, names: ['rikurisetup.local', '192.168.1.40'] });
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(t('secure.title'));
    await expect(page.getByText('Ctrl+Alt+F2')).toBeVisible();
    await expect(page.getByText(t('state.armed'))).toBeVisible();
    await expect(page.getByText('rikurisetup.local')).toBeVisible();
    await expect(page.getByText('192.168.1.40')).toBeVisible();
    await assertFits(page);
    expect(errors).toEqual([]);
  });

  test('never shows the fingerprint itself: only the browser can vouch for it', async ({ page }) => {
    await stubSetup(page, { claimed: false, claim: 'armed', ca_fingerprint_sha256: FINGERPRINT, names: ['rikurisetup.local'] });
    await page.goto('/');
    await expect(page.getByText(t('state.armed'))).toBeVisible();
    const text = await page.locator('body').innerText();
    expect(text).not.toContain(FINGERPRINT);
    expect(text).not.toContain(FINGERPRINT.slice(0, 11));
  });

  for (const [claim, claimed, key] of [
    ['done', true, 'state.done'],
    ['armed', false, 'state.armed'],
    ['expired', false, 'state.expired'],
    ['retired', false, 'state.retired'],
    ['unarmed', false, 'state.unarmed'],
  ] as const) {
    test(`shows the claim state "${claim}"`, async ({ page }) => {
      await stubSetup(page, { claimed, claim, ca_fingerprint_sha256: FINGERPRINT, names: ['rikurisetup.local'] });
      await page.goto('/');
      await expect(page.getByText(t(key))).toBeVisible();
    });
  }

  for (const [why, body, status] of [
    ['the API fails', { error: 'x' }, 500],
    ['the API is unreachable', null, 0],
    ['the reply is not a setup report', { claimed: 'yes' }, 200],
    ['the claim state is unknown to this page', { claimed: false, claim: 'later', ca_fingerprint_sha256: FINGERPRINT, names: [] }, 200],
  ] as const) {
    test(`says the state is unknown when ${why}, never a default`, async ({ page }) => {
      await stubSetup(page, body, status);
      await page.goto('/');
      await expect(page.getByText(t('state.unknown'))).toBeVisible();
      for (const key of ['state.done', 'state.armed', 'state.expired', 'state.retired', 'state.unarmed']) {
        await expect(page.getByText(t(key))).toHaveCount(0);
      }
    });
  }
});

// Repair 1 (verifier I2): the claim screen shows the CA's fingerprint, and
// the padlock opens the node's server certificate, which the CA signs: the
// reader must be sent to the CA in the chain, by its name, and on iPhone and
// iPad (which have no certificate viewer in Safari) to the installed profile.
test.describe('the fingerprint check', () => {
  test('sends the reader to the CA they installed, by its name, never to the server certificate', async ({ page }) => {
    await stubSetup(page, { claimed: false, claim: 'armed', ca_fingerprint_sha256: FINGERPRINT, names: ['rikurisetup.local'] });
    await page.goto('/');
    const steps = page.getByRole('list', { name: t('secure.check_steps') });
    await expect(steps).toContainText('Rikuri Node CA');
    await expect(steps).toContainText('SHA-256');
    const iphone = page.getByText(t('secure.check_iphone'));
    await expect(iphone).toBeVisible();
    expect(t('secure.check_iphone')).toContain('VPN & Device Management');
    expect(t('secure.check_iphone')).toContain('Rikuri Node CA');
  });
});

// Repair 1 (verifier I3): the preview sends the control plane's own CSP
// (ui/src/csp.ts, kept equal to src/ui.rs by scripts/quality/tests), so a
// page the node's policy would break fails here, not only on the node.
test.describe("the node's policy", () => {
  for (const path of ['/cert.html', '/']) {
    test(`${path} is drawn under the CSP the node sends, with no violation`, async ({ page }) => {
      await page.addInitScript(() => {
        const seen: string[] = [];
        (window as unknown as { __violations: string[] }).__violations = seen;
        document.addEventListener('securitypolicyviolation', (e) => seen.push(`${e.violatedDirective} ${e.blockedURI}`));
      });
      const errors = watchErrors(page);
      await stubSetup(page, { claimed: false, claim: 'armed', ca_fingerprint_sha256: FINGERPRINT, names: ['rikurisetup.local'] });
      const response = await page.goto(path);
      expect(response?.headers()['content-security-policy']).toBe(CSP);
      await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
      await expect(page.getByRole('button').or(page.getByText(t('state.armed'))).first()).toBeVisible();
      expect(await page.evaluate(() => (window as unknown as { __violations: string[] }).__violations)).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
});

test.describe('the theme', () => {
  for (const colorScheme of ['light', 'dark'] as const) {
    test(`every variable the pages use is defined (${colorScheme})`, async ({ page }) => {
      await page.emulateMedia({ colorScheme });
      for (const path of ['/cert.html', '/']) {
        await stubSetup(page, { claimed: false, claim: 'armed', ca_fingerprint_sha256: FINGERPRINT, names: [] });
        await page.goto(path);
        await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
        const missing = await page.evaluate(() => {
          const used = new Set<string>();
          for (const sheet of [...document.styleSheets]) {
            for (const rule of [...sheet.cssRules]) {
              for (const m of rule.cssText.matchAll(/var\((--[\w-]+)/g)) used.add(m[1]);
            }
          }
          const root = getComputedStyle(document.documentElement);
          return [...used].filter((v) => root.getPropertyValue(v).trim() === '');
        });
        expect(missing, `undefined variables on ${path}`).toEqual([]);
      }
    });
  }

  test('dark and light differ', async ({ page }) => {
    const bg = async (colorScheme: 'light' | 'dark') => {
      await page.emulateMedia({ colorScheme });
      await page.goto('/cert.html');
      return page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    };
    expect(await bg('dark')).not.toBe(await bg('light'));
  });
});
