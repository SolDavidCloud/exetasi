<template>
  <q-page class="app-container q-py-xl">
    <section class="app-hero">
      <div class="hero-grid">
        <div class="hero-copy">
          <p class="app-chip">{{ t('home.eyebrow') }}</p>
          <h1 class="hero-title">{{ t('app.title') }}</h1>
          <p class="hero-lead app-muted">{{ t('home.lead') }}</p>
          <div class="hero-actions">
            <q-btn
              v-if="!auth.isAuthenticated"
              unelevated
              color="primary"
              size="lg"
              :label="t('home.ctaGetStarted')"
              :to="{ name: 'login' }"
              icon-right="arrow_forward"
            />
            <q-btn
              v-else
              unelevated
              color="primary"
              size="lg"
              :label="t('home.ctaYourOrgs')"
              :to="{ name: 'orgs' }"
              icon-right="arrow_forward"
            />
            <q-btn
              flat
              color="primary"
              size="lg"
              :label="t('home.ctaLearnMore')"
              href="https://github.com"
              target="_blank"
              rel="noopener"
              icon-right="open_in_new"
            />
          </div>
        </div>
        <div class="hero-visual" aria-hidden="true">
          <div class="hero-card hero-card--one">
            <q-icon name="quiz" size="28px" />
            <div>
              <p class="hero-card__title">{{ t('home.visual.quizTitle') }}</p>
              <p class="hero-card__sub app-muted">{{ t('home.visual.quizSub') }}</p>
            </div>
          </div>
          <div class="hero-card hero-card--two">
            <q-icon name="insights" size="28px" />
            <div>
              <p class="hero-card__title">{{ t('home.visual.analyticsTitle') }}</p>
              <p class="hero-card__sub app-muted">{{ t('home.visual.analyticsSub') }}</p>
            </div>
          </div>
          <div class="hero-card hero-card--three">
            <q-icon name="groups" size="28px" />
            <div>
              <p class="hero-card__title">{{ t('home.visual.teamTitle') }}</p>
              <p class="hero-card__sub app-muted">{{ t('home.visual.teamSub') }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="q-mt-xl">
      <h2 class="section-title">{{ t('home.featuresTitle') }}</h2>
      <div class="app-grid">
        <article v-for="f in features" :key="f.titleKey" class="app-panel feature">
          <div class="feature__icon">
            <q-icon :name="f.icon" size="24px" />
          </div>
          <p class="feature__title">{{ t(f.titleKey) }}</p>
          <p class="feature__desc app-muted">{{ t(f.descKey) }}</p>
        </article>
      </div>
    </section>

    <section v-if="isDev" class="q-mt-xl app-panel">
      <div class="row items-center justify-between q-gutter-md">
        <div>
          <p class="text-weight-medium q-mb-xs">{{ t('home.devApiTitle') }}</p>
          <p class="text-caption app-muted q-ma-none">{{ t('home.devApiSub') }}</p>
        </div>
        <div class="row items-center q-gutter-sm">
          <q-btn
            outline
            color="primary"
            :loading="loading"
            :label="t('home.pingBackend')"
            @click="pingBackend"
          />
          <q-chip
            v-if="statusText"
            :color="errored ? 'negative' : 'positive'"
            text-color="white"
            size="md"
          >
            {{ statusText }}
          </q-chip>
        </div>
      </div>
    </section>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getApiClient } from 'src/api/client';
import { useAuthStore } from 'src/stores/auth-store';

const { t } = useI18n();
const auth = useAuthStore();

const isDev = import.meta.env.DEV;

const loading = ref(false);
const status = ref<string | null>(null);
const errored = ref(false);

const statusText = computed(() => {
  if (errored.value) {
    return t('home.backendError');
  }
  if (status.value) {
    return t('home.backendOk', { status: status.value });
  }
  return '';
});

const features = [
  { icon: 'edit_note', titleKey: 'home.features.authoring.title', descKey: 'home.features.authoring.desc' },
  { icon: 'shuffle', titleKey: 'home.features.randomize.title', descKey: 'home.features.randomize.desc' },
  { icon: 'verified', titleKey: 'home.features.grading.title', descKey: 'home.features.grading.desc' },
  { icon: 'bar_chart', titleKey: 'home.features.analytics.title', descKey: 'home.features.analytics.desc' },
  { icon: 'public', titleKey: 'home.features.openSource.title', descKey: 'home.features.openSource.desc' },
  { icon: 'devices', titleKey: 'home.features.responsive.title', descKey: 'home.features.responsive.desc' },
] as const;

async function pingBackend(): Promise<void> {
  loading.value = true;
  errored.value = false;
  status.value = null;
  try {
    const { data, error } = await getApiClient().GET('/api/v1/health');
    if (error) {
      errored.value = true;
      return;
    }
    status.value = data?.status ?? t('home.unknown');
  } catch {
    errored.value = true;
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped lang="scss">
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 40px;
  align-items: center;
}
@media (min-width: 900px) {
  .hero-grid {
    grid-template-columns: 1.2fr 1fr;
  }
}
.hero-title {
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.05;
  margin: 16px 0 12px;
}
.hero-lead {
  font-size: 1.1rem;
  max-width: 50ch;
  margin: 0 0 24px;
}
.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hero-visual {
  position: relative;
  min-height: 280px;
}
.hero-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: var(--app-surface);
  border-radius: var(--app-radius-md);
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-md);
  position: absolute;
  color: var(--q-primary);
}
.hero-card__title {
  font-weight: 700;
  color: var(--app-ink);
  margin: 0 0 2px;
}
.hero-card__sub {
  margin: 0;
  font-size: 0.85rem;
}
.hero-card--one {
  top: 0;
  left: 0;
}
.hero-card--two {
  top: 48%;
  right: 0;
  transform: translateY(-50%);
}
.hero-card--three {
  bottom: 0;
  left: 10%;
}
.section-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0 0 16px;
}
.feature {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.feature__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--app-brand-soft);
  color: var(--q-primary);
}
.feature__title {
  font-weight: 700;
  margin: 0;
}
.feature__desc {
  margin: 0;
  font-size: 0.95rem;
}
</style>
