<!-- The secure page, served only over TLS (/ and /setup). It confirms the
     connection and says how to check it: the node's CA (Rikuri Node CA) as
     the browser's own certificate viewer, or the phone's settings, show it,
     against the node's claim screen, which shows the CA's fingerprint. It never shows the fingerprint
     itself: a page in the middle could show the node's real, public one.
     The node's state comes from GET /api/setup; anything else is "unknown".
     Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md; the way on,
     docs/build-records/2026-11-11-5c3b-claim-and-sign-in.md -->
<script lang="ts">
  import type { SetupReport } from '../generated/SetupReport';
  import Header from '../lib/Header.svelte';
  import { readSession } from '../lib/api';
  import { t } from '../lib/i18n';
  import { readSetup } from '../lib/setup';

  let report = $state<SetupReport | null | undefined>(undefined);
  // 5c.3b: the way on. Unclaimed: the claim. Claimed: the node when this
  // browser is signed in, else sign-in. Unknown: no way on is guessed.
  let way = $state<'claim' | 'signin' | 'home' | undefined>(undefined);
  readSetup().then(async (r) => {
    report = r;
    if (r === null) return;
    if (!r.claimed) way = 'claim';
    else {
      const session = await readSession();
      if (session.kind === 'ok') way = 'home';
      else if (session.kind === 'refused' && session.status === 401) way = 'signin';
    }
  });
</script>

<div class="page">
  <Header step={t('secure.step')} badge={t('secure.badge')} />
  <div class="columns">
    <main>
      <h1>{t('secure.title')}</h1>
      <p class="lead">{t('secure.lead')}</p>
      <section class="card" aria-labelledby="check">
        <h2 id="check">{t('secure.check')}</h2>
        <ol aria-label={t('secure.check_steps')}>
          <li><span class="n" aria-hidden="true">1</span><span>{t('secure.check1_before')} <kbd>Ctrl+Alt+F2</kbd>{t('secure.check1_after')}</span></li>
          <li><span class="n" aria-hidden="true">2</span><span>{t('secure.check2')}</span></li>
          <li><span class="n" aria-hidden="true">3</span><span>{t('secure.check3')}</span></li>
        </ol>
        <ul class="phones">
          <li>{t('secure.check_iphone')}</li>
          <li>{t('secure.check_android')}</li>
        </ul>
        <p class="why">{t('secure.why')}</p>
      </section>
    </main>
    <aside class="panel" aria-labelledby="node">
      <h2 id="node">{t('secure.node')}</h2>
      {#if report === undefined}
        <p class="state" aria-busy="true">…</p>
      {:else if report === null}
        <p class="state">{t('state.unknown')}</p>
      {:else}
        <dl>
          <dt>{t('secure.setup')}</dt>
          <dd>{t(`state.${report.claim}`)}</dd>
          <dt>{t('secure.names')}</dt>
          <dd>
            {#each report.names as name (name)}
              <span class="name">{name}</span>
            {/each}
          </dd>
        </dl>
      {/if}
      {#if way === 'claim'}
        <p class="next">{t('secure.next')}</p>
        <a class="action primary" href="/claim">{t('secure.claim_link')}</a>
      {:else if way === 'home'}
        <a class="action strong" href="/home">{t('secure.home_link')}</a>
      {:else if way === 'signin'}
        <a class="action strong" href="/signin">{t('secure.signin_link')}</a>
      {/if}
    </aside>
  </div>
</div>

<style>
  .page { max-width: 1120px; margin: 0 auto; padding: 24px 16px 40px; display: flex; flex-direction: column; gap: 28px; }
  .columns { display: flex; flex-wrap: wrap; gap: 28px; align-items: flex-start; }
  main { flex: 999 1 520px; min-width: 0; display: flex; flex-direction: column; gap: 18px; }
  aside { flex: 1 1 300px; min-width: 0; }
  h1 { margin: 0; font-size: clamp(32px, 5vw, 46px); line-height: 1.08; }
  h2 { margin: 0; font-size: 21px; }
  .lead { margin: 0; color: var(--text-soft); max-width: 600px; }
  .card { background: var(--surface); border-radius: var(--radius-card); padding: 24px; box-shadow: var(--shadow); display: flex; flex-direction: column; gap: 16px; }
  ol { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 14px; }
  ol li { display: flex; gap: 12px; }
  .phones { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; font-size: 15px; color: var(--text-soft); }
  .n {
    flex: none; width: 30px; height: 30px; border-radius: var(--radius-badge);
    background: var(--glow); color: var(--yellow-ink); font-family: var(--font-display); font-weight: 600;
    display: flex; align-items: center; justify-content: center;
  }
  .why { margin: 0; font-size: 15px; color: var(--muted); background: var(--bg); border-radius: var(--radius-chip); padding: 14px 16px; }
  .panel { background: var(--panel); border-radius: var(--radius-card); padding: 24px; display: flex; flex-direction: column; gap: 14px; }
  dl { margin: 0; display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 10px 16px; }
  dt { color: var(--muted); }
  dd { margin: 0; font-weight: 600; display: flex; flex-direction: column; gap: 4px; overflow-wrap: anywhere; }
  .state { margin: 0; font-weight: 600; }
  .next { margin: 0; font-size: 15px; color: var(--text-soft); }
</style>
