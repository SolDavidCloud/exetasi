<template>
  <router-link :to="{ name: 'home' }" class="app-logo" :aria-label="t('app.title')">
    <span class="app-logo__mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="appLogoGrad" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stop-color="currentColor" stop-opacity="1" />
            <stop offset="100%" stop-color="currentColor" stop-opacity="0.65" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="28" height="28" rx="9" fill="url(#appLogoGrad)" />
        <path
          d="M10 11.5h12M10 16h8M10 20.5h12"
          stroke="white"
          stroke-width="2.4"
          stroke-linecap="round"
        />
      </svg>
    </span>
    <span class="app-logo__word">{{ t('app.title') }}</span>
  </router-link>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
</script>

<style scoped lang="scss">
.app-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--app-ink);
  font-weight: 700;
  letter-spacing: -0.01em;
  text-decoration: none;
}
.app-logo:hover {
  color: var(--app-ink);
  text-decoration: none;
}
.app-logo__mark {
  display: inline-flex;
  width: 32px;
  height: 32px;
  color: var(--q-primary);
}
.app-logo__mark svg {
  width: 100%;
  height: 100%;
}
.app-logo__word {
  font-size: 1.05rem;
}
</style>
