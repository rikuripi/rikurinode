<script lang="ts">
  import Logo from './Logo.svelte';
  import { t } from './i18n';

  let { step, badge = '' }: { step: string; badge?: string } = $props();
</script>

<header>
  <Logo />
  <span class="name">{t('app.name')}</span>
  {#if badge}
    <span class="badge">
      <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
        <rect x="5" y="11" width="14" height="10" rx="2"></rect>
        <path d="M8 11V8a4 4 0 0 1 8 0v3"></path>
      </svg>
      {badge}
    </span>
  {/if}
  <span class="step">{step}</span>
</header>

<style>
  header { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
  .name { font-family: var(--font-display); font-weight: 600; font-size: 20px; }
  .badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--strong-btn); color: var(--strong-btn-ink);
    font-size: 14px; font-weight: 600; padding: 6px 12px; border-radius: var(--radius-pill);
  }
  .badge svg { fill: none; stroke: currentColor; stroke-width: 2.5; }
  .step {
    margin-left: auto; background: var(--glow); color: var(--yellow-ink);
    font-size: 13px; font-weight: 600; padding: 6px 12px; border-radius: var(--radius-pill);
  }
</style>
