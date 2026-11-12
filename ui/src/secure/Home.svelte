<!-- /home (5c.3b): the signed-in owner's page. It reads the session from
     GET /api/session (signed out: to /signin), says until when it lasts, and
     signs out with DELETE /api/session and the session's CSRF token.
     5c.4a: it is the SetupHub. It shows the node's ID and every step of
     setup from GET /api/hub, each state said in words, never by colour alone.
     A reply that is not exactly the hub shows no step at all: never a guess.
     Records: docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md,
     docs/build-records/2026-11-11-5c4a-uuid-and-setup-hub.md -->
<script lang="ts">
  import type { HubReport } from '../generated/HubReport';
  import type { SessionInfo } from '../generated/SessionInfo';
  import Header from '../lib/Header.svelte';
  import { readHub, readSession, signOut } from '../lib/api';
  import { t } from '../lib/i18n';
  import { shared } from '../lib/says';

  // undefined while asking; null when the session's state is unknown.
  let session = $state<SessionInfo | null | undefined>(undefined);
  // The same for the hub: null when it could not be read.
  let hub = $state<HubReport | null | undefined>(undefined);
  let busy = $state(false);
  let said = $state('');

  readSession().then(async (outcome) => {
    if (outcome.kind === 'ok') session = outcome.value;
    else if (outcome.kind === 'refused' && outcome.status === 401) return location.replace('/signin');
    else {
      session = null;
      said = shared(outcome) ?? t('form.unknown');
      return;
    }
    const read = await readHub();
    if (read.kind === 'ok') hub = read.value;
    else if (read.kind === 'refused' && read.status === 401) location.replace('/signin');
    else hub = null;
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
      <section class="card" aria-labelledby="hub-title">
        <h2 id="hub-title">{t('hub.title')}</h2>
        {#if hub === undefined}
          <p class="hint" aria-busy="true">{t('form.working')}</p>
        {:else if hub === null}
          <p class="unread">{t('hub.unreadable')}</p>
        {:else}
          <dl>
            <dt>{t('hub.node_id')}</dt>
            <dd class="id">{hub.node_id}</dd>
          </dl>
          <ol class="steps" aria-labelledby="hub-title">
            {#each hub.steps as { step, state } (step)}
              <li data-step={step} data-state={state}>
                <span class="mark" aria-hidden="true">{state === 'done' ? '✓' : state === 'unknown' ? '?' : '○'}</span>
                <span class="what">
                  <span class="name">{t(`hub.step.${step}`)}</span>
                  <span class="state">{t(`hub.state.${state}`)}</span>
                  {#if step === 'name' && state === 'next'}<span class="hint">{t('hub.name_next')}</span>{/if}
                </span>
              </li>
            {/each}
          </ol>
        {/if}
      </section>
      <section class="card">
        <p>{until}</p>
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
  h2 { margin: 0; font-size: 21px; }
  dl { margin: 0; display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 6px 16px; }
  dt { color: var(--muted); }
  dd { margin: 0; }
  .id { font-family: ui-monospace, monospace; font-size: 15px; overflow-wrap: anywhere; }
  .unread { font-weight: 600; }
  .steps { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 12px; }
  .steps li { display: flex; gap: 12px; align-items: flex-start; }
  .mark {
    flex: none; width: 30px; height: 30px; border-radius: var(--radius-badge);
    background: var(--panel); color: var(--ink); font-weight: 600;
    display: flex; align-items: center; justify-content: center;
  }
  li[data-state='done'] .mark { background: var(--glow); color: var(--yellow-ink); }
  .what { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .name { font-weight: 600; }
  .state { font-size: 15px; color: var(--text-soft); }
</style>
