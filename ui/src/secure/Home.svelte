<!-- /home (5c.3b): the signed-in owner's page. It reads the session from
     GET /api/session (signed out: to /signin), says until when it lasts, and
     signs out with DELETE /api/session and the session's CSRF token.
     Record: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md -->
<script lang="ts">
  import type { SessionInfo } from '../generated/SessionInfo';
  import Header from '../lib/Header.svelte';
  import { readSession, signOut } from '../lib/api';
  import { t } from '../lib/i18n';
  import { shared } from '../lib/says';

  // undefined while asking; null when the session's state is unknown.
  let session = $state<SessionInfo | null | undefined>(undefined);
  let busy = $state(false);
  let said = $state('');

  readSession().then((outcome) => {
    if (outcome.kind === 'ok') session = outcome.value;
    else if (outcome.kind === 'refused' && outcome.status === 401) location.replace('/signin');
    else {
      session = null;
      said = shared(outcome) ?? t('form.unknown');
    }
  });

  const until = $derived(
    session ? t('home.until').replace('{date}', new Date(session.expires_unix * 1000).toLocaleString()) : '',
  );

  async function out() {
    if (!session || busy) return;
    busy = true;
    said = t('form.working');
    const outcome = await signOut(session.csrf_token);
    busy = false;
    if (outcome.kind === 'ok' || (outcome.kind === 'refused' && outcome.status === 401)) {
      session = undefined;
      location.assign('/signin');
      return;
    }
    said = shared(outcome) ?? t('form.unknown');
  }
</script>

<div class="page">
  <Header step={t('home.step')} badge={t('secure.badge')} />
  <main>
    <h1>{t('home.title')}</h1>
    {#if session === undefined}
      <p class="lead" aria-busy="true">{t('form.working')}</p>
    {:else if session}
      <section class="card">
        <p>{until}</p>
        <p class="hint">{t('home.next')}</p>
        <button type="button" class="action strong" disabled={busy} onclick={out}>{t('home.signout')}</button>
      </section>
    {/if}
    {#if said}<p class="alert" role="alert">{said}</p>{/if}
  </main>
</div>

<style>
  .page { max-width: 640px; margin: 0 auto; padding: 24px 16px 40px; display: flex; flex-direction: column; gap: 24px; }
  main { display: flex; flex-direction: column; gap: 18px; }
  h1 { margin: 0; font-size: clamp(30px, 5vw, 42px); line-height: 1.1; }
  .lead { margin: 0; color: var(--text-soft); }
  .card { background: var(--surface); border-radius: var(--radius-card); padding: 24px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 16px; }
  .card p { margin: 0; }
</style>
