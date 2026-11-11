<!-- /signin (5c.3b): the owner's password, as a current password, sent only
     by fetch in a JSON body to POST /api/session. A wrong one is said and
     cleared; an unclaimed node leads to the claim instead.
     Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md -->
<script lang="ts">
  import type { SetupReport } from '../generated/SetupReport';
  import Header from '../lib/Header.svelte';
  import { signIn } from '../lib/api';
  import { t } from '../lib/i18n';
  import { shared, waitText } from '../lib/says';
  import { readSetup } from '../lib/setup';
  import { Wait } from '../lib/wait.svelte';

  let report: SetupReport | null | undefined = $state(undefined);
  readSetup().then((r) => (report = r));

  let password = $state('');
  let show = $state(false);
  let busy = $state(false);
  let said = $state('');
  const wait = new Wait();

  const ready = $derived(password !== '' && !busy && !wait.active);
  const message = $derived(wait.active ? waitText(wait.seconds) : said);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!ready) return;
    busy = true;
    said = t('form.working');
    const outcome = await signIn({ password });
    busy = false;
    if (outcome.kind === 'ok') {
      password = '';
      location.assign('/home');
      return;
    }
    if (outcome.kind === 'wait') {
      said = '';
      wait.start(outcome.seconds);
      return;
    }
    if (outcome.kind === 'refused' && outcome.status === 401) {
      password = '';
      said = t('signin.wrong');
      return;
    }
    said = shared(outcome) ?? t('form.unknown');
  }
</script>

<div class="page">
  <Header step={t('signin.step')} badge={t('secure.badge')} />
  <main>
    <h1>{t('signin.title')}</h1>
    {#if report === undefined}
      <p class="lead" aria-busy="true">{t('form.working')}</p>
    {:else if report !== null && !report.claimed}
      <p class="alert">{t('signin.unclaimed')}</p>
      <a class="action primary" href="/claim">{t('secure.claim_link')}</a>
    {:else}
      <form class="card" onsubmit={submit} novalidate>
        <div class="field">
          <label for="password">{t('signin.password')}</label>
          <input id="password" name="password" type={show ? 'text' : 'password'} bind:value={password}
                 autocomplete="current-password" />
        </div>
        <button type="button" class="quietaction" aria-pressed={show} onclick={() => (show = !show)}>
          {show ? t('password.hide') : t('password.show')}
        </button>
        {#if message}<p class="alert" role="alert">{message}</p>{/if}
        <button type="submit" class="action primary" disabled={!ready}>{t('signin.submit')}</button>
      </form>
    {/if}
  </main>
</div>

<style>
  .page { max-width: 640px; margin: 0 auto; padding: 24px 16px 40px; display: flex; flex-direction: column; gap: 24px; }
  main { display: flex; flex-direction: column; gap: 18px; }
  h1 { margin: 0; font-size: clamp(30px, 5vw, 42px); line-height: 1.1; }
  .lead { margin: 0; color: var(--text-soft); }
  .card { background: var(--surface); border-radius: var(--radius-card); padding: 24px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 18px; }
  .quietaction { align-self: flex-start; }
</style>
