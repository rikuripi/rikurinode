<!-- /claim (5c.3b): the code from the node's screen and a new password,
     typed twice. It submits only when the node's rule holds (12 characters,
     counted as the node counts them) and both match, and only by fetch, in
     a JSON body, to POST /api/claim. Every answer is said; a refusal of the
     password clears it, a wrong code clears the code.
     Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md -->
<script lang="ts">
  import type { SetupReport } from '../generated/SetupReport';
  import Header from '../lib/Header.svelte';
  import { claim } from '../lib/api';
  import { t } from '../lib/i18n';
  import { shared, waitText } from '../lib/says';
  import { readSetup } from '../lib/setup';
  import { Wait } from '../lib/wait.svelte';

  const MIN_CHARS = 12; // password.rs MIN_CHARS

  // undefined while asking; null when the node's state is unknown, and the
  // form is offered: the node itself refuses a claim it will not take.
  let report = $state<SetupReport | null | undefined>(undefined);
  readSetup().then((r) => (report = r));

  let code = $state('');
  let password = $state('');
  let confirm = $state('');
  let show = $state(false);
  let busy = $state(false);
  let said = $state('');
  let already = $state(false);
  const wait = new Wait();
  $effect(() => () => wait.stop());

  // Characters as the node counts them (Rust's chars(): Unicode scalar values).
  const met = $derived([...password].length >= MIN_CHARS);
  const mismatch = $derived(confirm !== '' && confirm !== password);
  const ready = $derived(code.trim() !== '' && met && password === confirm && !busy && !wait.active);

  const message = $derived(wait.active ? waitText(wait.seconds) : said);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!ready) return;
    busy = true;
    said = t('form.working');
    already = false;
    const outcome = await claim({ code, password });
    busy = false;
    if (outcome.kind === 'ok') {
      password = '';
      confirm = '';
      location.assign('/home');
      return;
    }
    if (outcome.kind === 'wait') {
      said = '';
      wait.start(outcome.seconds);
      return;
    }
    if (outcome.kind === 'refused') {
      if (outcome.status === 401) {
        code = '';
        said = t('claim.wrong_code');
      } else if (outcome.status === 409) {
        already = true;
        said = t('claim.already');
      } else if (outcome.status === 422) {
        password = '';
        confirm = '';
        said = `${t('claim.policy')} ${outcome.error}`;
      } else {
        said = t('form.unknown');
      }
      return;
    }
    said = shared(outcome) ?? t('form.unknown');
  }
</script>

<div class="page">
  <Header step={t('claim.step')} badge={t('secure.badge')} />
  <main>
    <h1>{t('claim.title')}</h1>
    {#if report === undefined}
      <p class="lead" aria-busy="true">{t('form.working')}</p>
    {:else if report?.claimed}
      <p class="alert">{t('claim.already')}</p>
      <a class="action strong" href="/signin">{t('secure.signin_link')}</a>
    {:else}
      <p class="lead">{t('claim.lead')}</p>
      <form class="card" method="post" onsubmit={submit} novalidate>
        <div class="field">
          <label for="code">{t('claim.code')}</label>
          <input id="code" bind:value={code} autocomplete="one-time-code" autocapitalize="characters"
                 spellcheck="false" aria-describedby="code-hint" />
          <p class="hint" id="code-hint">{t('claim.code_hint')}</p>
        </div>
        <div class="field">
          <label for="password">{t('claim.password')}</label>
          <input id="password" type={show ? 'text' : 'password'} bind:value={password}
                 autocomplete="new-password" aria-describedby="rule" />
          <p class="hint rule" id="rule" data-met={String(met)}>{t('claim.rule')}</p>
        </div>
        <div class="field">
          <label for="confirm">{t('claim.confirm')}</label>
          <input id="confirm" type={show ? 'text' : 'password'} bind:value={confirm}
                 autocomplete="new-password" />
          {#if mismatch}<p class="hint warn">{t('claim.mismatch')}</p>{/if}
        </div>
        <button type="button" class="quietaction" aria-pressed={show} onclick={() => (show = !show)}>
          {show ? t('password.hide') : t('password.show')}
        </button>
        <p class="hint">{t('claim.tip')}</p>
        <p class="keep">{t('claim.keep')}</p>
        {#if message}<p class="alert" role="alert">{message}</p>{/if}
        {#if already}<a class="action strong" href="/signin">{t('secure.signin_link')}</a>{/if}
        <button type="submit" class="action primary" disabled={!ready}>{t('claim.submit')}</button>
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
  .rule::before { content: '○ '; }
  .rule[data-met='true'] { color: var(--ink); }
  .rule[data-met='true']::before { content: '✓ '; }
  .warn { color: var(--link); }
  .keep { margin: 0; padding: 12px 14px; border-radius: var(--radius-chip); background: var(--panel); font-size: 15px; }
  .quietaction { align-self: flex-start; }
</style>
