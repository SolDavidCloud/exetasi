<template>
  <q-page class="error-page app-container">
    <div class="error-panel app-panel">
      <p class="app-chip">{{ t('error.code') }}</p>
      <h1 class="error-title">{{ t('error.notFound') }}</h1>
      <p class="app-muted q-mt-sm">{{ t('error.notFoundDesc') }}</p>
      <div class="q-mt-lg row q-gutter-sm">
        <q-btn unelevated color="primary" :to="{ name: 'home' }" :label="t('error.goHome')" icon="home" />
        <q-btn flat color="primary" @click="goBack" :label="t('error.goBack')" icon="arrow_back" />
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';

const { t } = useI18n();
const router = useRouter();

function goBack(): void {
  router.back();
}
</script>

<style scoped lang="scss">
.error-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding-block: clamp(32px, 8vw, 96px);
}
.error-panel {
  max-width: 520px;
  width: 100%;
  text-align: center;
}
.error-title {
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 800;
  margin: 12px 0 0;
}
</style>
