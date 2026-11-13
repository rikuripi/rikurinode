<!-- /name (5c.4b-2): naming the node, during setup only. It reads the
     session (signed out: to /signin) and the hub; a node already named says
     so, with the way back, and asks nothing more. Otherwise it fills in the
     first free rikuriNN from GET /api/node/name/suggestion, lets the owner
     change it, checks the name's rules, and renames with PUT /api/node/name
     and the session's CSRF token. The session's cookie is the old name's, so
     on success the page opens the new name's sign-in. A reply it cannot read
     is a failure, never success.
     Record: docs/build-records/2026-11-13-5c4b2-naming-page.md -->
<script lang="ts">
  import type { SessionInfo } from '../generated/SessionInfo';
  import Header from '../lib/Header.svelte';
  import { nodeName, readHub, readSession, readSuggestion, renameNode } from '../lib/api';
  import { t } from '../lib/i18n';
  import { shared } from '../lib/says';

  // How long the page shows the new name before it opens it.
  const OPEN_AFTER_MS = 1500;
  const TAKEN = 'that name is already in use on this network';
  const ALREADY = 'the node already has a name';

  let session = $state<SessionInfo | null>(null);
  let phase = $state<'loading' | 'named' | 'form' | 'done' | 'unread'>('loading');
  let name = $state('');
  let hint = $state('');
  let busy = $state(false);
  let said = $state('');
  let opens = $state('');
  let host = $state('');

  readSession().then(async (outcome) => {
    if (outcome.kind === 'refused' && outcome.status === 401) return location.replace('/signin');
    if (outcome.kind !== 'ok') {
      phase = 'unread';
      said = shared(outcome) ?? t('form.unknown');
      return;
    }
    session = outcome.value;
    const hub = await readHub();
    if (hub.kind === 'refused' && hub.status === 401) return location.replace('/signin');
    if (hub.kind !== 'ok') {
      phase = 'unread';
      said = t('hub.unreadable');
      return;
    }
    if (hub.value.steps.find((s) => s.step === 'name')?.state !== 'next') {
      phase = 'named';
      return;
    }
    phase = 'form';
    const suggested = await readSuggestion();
    if (suggested.kind === 'refused' && suggested.status === 401) return location.replace('/signin');
    if (suggested.kind !== 'ok') hint = t('name.check_failed');
    else if (suggested.value.name === null) hint = t('name.none_free');
    else if (name === '') name = suggested.value.name;
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!session || busy || phase !== 'form') return;
    const wanted = nodeName(name);
    if (wanted === null) {
      said = t('name.rule');
      return;
    }
    busy = true;
    said = t('form.working');
    const outcome = await renameNode(session.csrf_token, wanted);
    busy = false;
    if (outcome.kind === 'ok') {
      host = outcome.value.host;
      opens = `https://${host}/signin`;
      said = '';
      phase = 'done';
      setTimeout(() => location.assign(opens), OPEN_AFTER_MS);
      return;
    }
    if (outcome.kind === 'refused') {
      if (outcome.status === 401) return location.replace('/signin');
      if (outcome.status === 409 && outcome.error === TAKEN) said = t('name.taken');
      else if (outcome.status === 409 && outcome.error === ALREADY) phase = 'named';
      else if (outcome.status === 400) said = t('name.rule');
      else said = t('name.failed');
      return;
    }
    said = outcome.kind === 'offline' ? t('form.offline') : t('name.failed');
  }
</script>

<div class="page">
  <Header step={t('name.step')} badge={t('secure.badge')} />
  <main>
    <h1>{t('name.title')}</h1>
    {#if phase === 'loading'}
      <p class="lead" aria-busy="true">{t('form.working')}</p>
    {:else if phase === 'named'}
      <p class="alert" role="status">{t('name.already')}</p>
      <a class="action primary" href="/home">{t('name.back')}</a>
    {:else if phase === 'done'}
      <section class="card" aria-live="polite">
        <p>{t('name.done').replace('{host}', host)}</p>
        <a class="action primary" href={opens}>{t('name.continue')}</a>
      </section>
    {:else if phase === 'form'}
      <p class="lead">{t('name.lead')}</p>
      <form class="card" method="post" onsubmit={submit} novalidate>
        <div class="field">
          <label for="name">{t('name.field')}</label>
          <div class="named">
            <input id="name" type="text" bind:value={name} autocomplete="off" autocapitalize="none"
                   spellcheck="false" />
            <span class="suffix" aria-hidden="true">.local</span>
          </div>
        </div>
        {#if hint}<p class="hint">{hint}</p>{/if}
        {#if said}<p class="alert" role="alert">{said}</p>{/if}
        <button type="submit" class="action primary" disabled={busy}>{t('name.submit')}</button>
      </form>
    {/if}
    {#if phase === 'unread' && said}<p class="alert" role="alert">{said}</p>{/if}
  </main>
</div>

<style>
  .page { max-width: 640px; margin: 0 auto; padding: 24px 16px 40px; display: flex; flex-direction: column; gap: 24px; }
  main { display: flex; flex-direction: column; gap: 18px; }
  h1 { margin: 0; font-size: clamp(30px, 5vw, 42px); line-height: 1.1; }
  .lead { margin: 0; color: var(--text-soft); }
  .card { background: var(--surface); border-radius: var(--radius-card); padding: 24px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 18px; }
  .card p { margin: 0; }
  .named { display: flex; align-items: center; gap: 8px; min-width: 0; }
  .named input { flex: 1; min-width: 0; }
  .suffix { flex: none; color: var(--muted); font-family: ui-monospace, monospace; }
</style>
