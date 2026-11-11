<!-- The certificate screen, served in the clear at http://<node>/. It explains,
     hands over /ca.crt with a guide per device, and sends the reader on to
     /setup, which the plain listener redirects to HTTPS. It asks for nothing
     and calls no API: anyone on the network could alter a page sent in the
     clear, so no decision rests on it.
     Record: docs/build-records/2026-11-11-5c3a-ui-pipeline.md -->
<script lang="ts">
  import Header from '../lib/Header.svelte';
  import { t } from '../lib/i18n';

  const DEVICES = ['iphone', 'android', 'mac', 'windows', 'linux'] as const;
  type Device = (typeof DEVICES)[number];

  function guess(): Device {
    const ua = navigator.userAgent;
    if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'iphone';
    if (/Android/.test(ua)) return 'android';
    if (/Macintosh/.test(ua)) return 'mac';
    if (/Windows/.test(ua)) return 'windows';
    if (/Linux|X11/.test(ua)) return 'linux';
    return 'iphone';
  }

  let device: Device = $state(guess());
  const steps = $derived([1, 2, 3].map((n) => t(`steps.${device}.${n}`)));
</script>

<main>
  <Header step={t('cert.step')} />
  <h1>{t('cert.title')}</h1>
  <p class="lead">{t('cert.lead')}</p>

  <section aria-labelledby="which">
    <h2 id="which">{t('cert.which')}</h2>
    <div class="devices">
      {#each DEVICES as d (d)}
        <button type="button" aria-pressed={device === d} class:chosen={device === d} onclick={() => (device = d)}>
          {t(`device.${d}`)}
        </button>
      {/each}
    </div>
  </section>

  <section class="card">
    <ol aria-label={t('cert.steps')}>
      {#each steps as text, i (i)}
        <li><span class="n" aria-hidden="true">{i + 1}</span><span>{text}</span></li>
      {/each}
    </ol>
    <a class="primary" href="/ca.crt" download>{t('cert.download')}</a>
  </section>

  <section class="panel" aria-labelledby="installed">
    <h2 id="installed">{t('cert.installed')}</h2>
    <p>{t('cert.installed_text')}</p>
    <a class="strong" href="/setup">{t('cert.continue')} →</a>
  </section>

  <p class="quiet">{t('cert.stop')}</p>
</main>

<style>
  main { max-width: 560px; margin: 0 auto; padding: 24px 16px 40px; display: flex; flex-direction: column; gap: 20px; }
  h1 { margin: 8px 0 0; font-size: 32px; line-height: 1.12; }
  h2 { margin: 0; font-size: 19px; }
  .lead { margin: 0; color: var(--text-soft); }
  section { display: flex; flex-direction: column; gap: 12px; }
  .devices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
  .devices button {
    min-height: 48px; border: 0; border-radius: var(--radius-chip);
    background: var(--surface); color: var(--ink); font: inherit; font-weight: 600;
    box-shadow: inset 0 0 0 1.5px var(--line); cursor: pointer;
  }
  .devices button.chosen { background: var(--accent); color: var(--accent-ink); box-shadow: none; }
  .card { background: var(--surface); border-radius: var(--radius-card); padding: 20px; box-shadow: var(--shadow); gap: 16px; }
  ol { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 14px; font-size: 16px; }
  li { display: flex; gap: 12px; }
  .n {
    flex: none; width: 28px; height: 28px; border-radius: var(--radius-badge);
    background: var(--glow); color: var(--yellow-ink); font-family: var(--font-display); font-weight: 600;
    display: flex; align-items: center; justify-content: center;
  }
  a.primary, a.strong {
    min-height: 52px; border-radius: var(--radius-pill); text-decoration: none; font-weight: 600;
    display: flex; align-items: center; justify-content: center; text-align: center; padding: 0 20px;
  }
  a.primary { background: var(--accent); color: var(--accent-ink); font-family: var(--font-display); font-size: 18px; }
  a.strong { background: var(--strong-btn); color: var(--strong-btn-ink); }
  .panel { background: var(--panel); border-radius: var(--radius-card); padding: 20px; }
  .panel p { margin: 0; color: var(--text-soft); }
  .quiet { margin: 0; font-size: 14px; color: var(--muted); }
  @media (min-width: 640px) { .devices { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
</style>
