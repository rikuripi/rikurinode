<!-- The Rikuri sun: a Bitcoin-orange ₿ rising over the horizon, with a round
     yellow glow (owner, 2026-11-11). The ₿ is drawn, not typed, so it looks
     the same with or without the web fonts. Decorative: the name beside it
     is the text. -->
<script lang="ts">
  let { size = 44 }: { size?: number } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 36 36" aria-hidden="true" focusable="false">
  <defs>
    <clipPath id="rikuri-sky"><rect x="0" y="0" width="36" height="27"></rect></clipPath>
  </defs>
  <g clip-path="url(#rikuri-sky)">
    <circle class="glow outer" cx="18" cy="20" r="17.8"></circle>
    <circle class="glow inner" cx="18" cy="20" r="14"></circle>
    <circle class="disc" cx="18" cy="20" r="9.5"></circle>
    <g class="mark" transform="rotate(14 18 20)">
      <path d="M15.6 15.6v8.8M15.6 15.6h3a2 2 0 0 1 0 4H15.6M15.6 19.6h3.5a2.4 2.4 0 0 1 0 4.8H15.6"></path>
      <path d="M16.7 14.2v1.4M18.3 14.2v1.4M16.7 24.4v1.4M18.3 24.4v1.4"></path>
    </g>
  </g>
  <path class="horizon" d="M2.5 27.5h31"></path>
  <path class="horizon ground" d="M10 32h16"></path>
</svg>

<style>
  svg { flex: none; }
  .glow { fill: var(--glow); }
  .outer { opacity: 0.45; }
  .inner { opacity: 0.85; }
  .disc { fill: var(--sun); }
  .mark { fill: none; stroke: var(--sun-mark); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }
  .horizon { stroke: var(--horizon); stroke-width: 2.5; stroke-linecap: round; }
  .ground { opacity: 0.35; }
</style>
