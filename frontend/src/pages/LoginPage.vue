<template>
  <q-page class="login-page">
    <div class="login-card app-panel">
      <div class="q-mb-lg text-center">
        <AppLogo class="q-mb-md" />
        <h1 class="login-title">{{ t('auth.loginTitle') }}</h1>
        <p class="app-muted q-mt-xs">{{ t('auth.loginLead') }}</p>
      </div>

      <div v-if="oauthError" class="app-banner app-banner--negative q-mb-md">
        {{ t(`auth.errors.${oauthError}`) }}
      </div>
      <div v-if="banned" class="app-banner app-banner--negative q-mb-md" role="alert">
        <p class="q-ma-none text-weight-bold">{{ t('auth.errors.banned') }}</p>
        <p v-if="bannedReason" class="q-mt-xs q-mb-none">
          {{ t('auth.errors.bannedReason', { reason: bannedReason }) }}
        </p>
      </div>

      <!--
        Loading state: don't render any buttons until we know which providers
        the backend supports, to avoid a flash of "ghost" providers that
        would 503 on click.
      -->
      <div v-if="loadingProviders" class="column items-center q-py-md">
        <q-spinner size="32px" color="primary" />
      </div>

      <div v-else class="column q-gutter-md">
        <template v-if="providers">
          <q-btn
            v-if="providers.google"
            outline
            color="primary"
            class="full-width login-provider"
            :label="t('auth.provider.google')"
            :href="oauthStartUrl('/api/v1/auth/google/start')"
            type="a"
            icon="public"
          />
          <q-btn
            v-if="providers.github"
            outline
            color="primary"
            class="full-width login-provider"
            :label="t('auth.provider.github')"
            :href="oauthStartUrl('/api/v1/auth/github/start')"
            type="a"
            icon="code"
          />
          <q-btn
            v-if="providers.gitlab"
            outline
            color="primary"
            class="full-width login-provider"
            :label="t('auth.provider.gitlab')"
            :href="oauthStartUrl('/api/v1/auth/gitlab/start')"
            type="a"
            icon="source"
          />

          <!--
            OAuth setup guidance whenever no OAuth provider is enabled.
            (Development login does not replace OAuth for real deployments;
            show this above dev login so operators still see how to configure.)
          -->
          <div
            v-if="providers && !anyOauthEnabled"
            class="app-panel app-panel--muted column q-gutter-sm"
          >
            <div class="row items-center q-gutter-sm">
              <q-icon name="info" color="primary" size="20px" />
              <p class="text-weight-bold q-ma-none">
                {{ t('auth.noProviders.title') }}
              </p>
            </div>
            <p class="app-muted q-ma-none">{{ t('auth.noProviders.lead') }}</p>
            <ul class="login-help-list">
              <li>
                {{ t('auth.noProviders.env') }}
                <code>GOOGLE_CLIENT_ID</code>, <code>GOOGLE_CLIENT_SECRET</code>
              </li>
              <li><code>GITHUB_CLIENT_ID</code>, <code>GITHUB_CLIENT_SECRET</code></li>
              <li>
                <code>GITLAB_CLIENT_ID</code>, <code>GITLAB_CLIENT_SECRET</code> ({{
                  t('auth.noProviders.optional')
                }}: <code>GITLAB_OAUTH_BASE_URL</code>)
              </li>
              <li>
                {{ t('auth.noProviders.devAlt') }}
                <code>ENABLE_DEV_AUTH=true</code>.
              </li>
            </ul>
            <p class="app-muted q-ma-none text-caption">
              {{ t('auth.noProviders.restart') }}
            </p>
          </div>

          <template v-if="providers.dev">
            <div class="login-divider" role="separator">
              <span>{{ t('auth.devDivider') }}</span>
            </div>
            <p class="text-caption app-muted q-ma-none">{{ t('auth.devLoginHint') }}</p>
            <q-input
              v-model="username"
              outlined
              :label="t('auth.username')"
              autofocus
              :rules="[(v) => !!v || t('auth.usernameRequired')]"
            />
            <q-btn
              unelevated
              color="primary"
              class="full-width"
              :label="t('auth.devLogin')"
              :loading="loading"
              @click="onDevLogin"
            />
          </template>
        </template>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import AppLogo from 'components/AppLogo.vue';
import { getApiBaseUrl, getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';
import { useAuthStore } from 'src/stores/auth-store';

type AuthProviders = components['schemas']['AuthProviders'];

const { t } = useI18n();
const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const username = ref('alice');
const loading = ref(false);
const providers = ref<AuthProviders | null>(null);
const loadingProviders = ref(true);

const anyOauthEnabled = computed(
  () =>
    !!providers.value &&
    (providers.value.google || providers.value.github || providers.value.gitlab),
);

const oauthError = computed(() => {
  const raw = route.query.error;
  if (typeof raw !== 'string') return null;
  // Only surface known error codes; ignore arbitrary input.
  return raw === 'oauth_state' || raw === 'oauth_provider' ? raw : null;
});

const banned = computed(() => route.query.error === 'banned');
const bannedReason = computed(() => {
  if (!banned.value) return '';
  const raw = route.query.reason;
  return typeof raw === 'string' ? raw.slice(0, 500) : '';
});

function oauthStartUrl(path: string): string {
  const base = getApiBaseUrl();
  if (base.length === 0) {
    return path;
  }
  return `${base}${path}`;
}

function safeRedirectTarget(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) return '/';
  if (!value.startsWith('/')) return '/';
  if (value.startsWith('//') || value.startsWith('/\\')) return '/';
  return value;
}

async function fetchProviders(): Promise<void> {
  loadingProviders.value = true;
  try {
    const { data, error } = await getApiClient().GET('/api/v1/auth/providers');
    if (error || !data) {
      // Fail open — assume nothing is configured so we show admin guidance
      // instead of half-working buttons.
      providers.value = { google: false, github: false, gitlab: false, dev: false };
    } else {
      providers.value = data;
    }
  } catch {
    // Network / client errors: same fail-open so the login page never renders empty.
    providers.value = { google: false, github: false, gitlab: false, dev: false };
  } finally {
    loadingProviders.value = false;
  }
}

async function onDevLogin() {
  loading.value = true;
  try {
    await auth.devLogin(username.value.trim());
    const redirect = safeRedirectTarget(route.query.redirect);
    await router.replace(redirect);
  } catch (err) {
    // Dev login is the only flow where we see the ban response inline (OAuth
    // bans redirect through `_banned_redirect`). We surface the reason in a
    // translated notification so operators get the same UX as OAuth bans.
    if (err instanceof Error && err.message.startsWith('banned')) {
      const reason = err.message.slice('banned:'.length).trim();
      await router.replace({
        name: 'login',
        query: reason ? { error: 'banned', reason } : { error: 'banned' },
      });
      return;
    }
    $q.notify({ type: 'negative', message: t('auth.devLoginFailed') });
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void fetchProviders();
});
</script>

<style scoped lang="scss">
.login-page {
  min-height: calc(100vh - 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(24px, 5vw, 56px) 16px;
  background:
    radial-gradient(800px 400px at 10% 10%, var(--app-brand-soft), transparent 60%),
    radial-gradient(
      600px 300px at 90% 90%,
      color-mix(in srgb, var(--q-secondary) 14%, transparent),
      transparent 60%
    );
}
.login-card {
  width: 100%;
  max-width: 440px;
  padding: clamp(28px, 4vw, 40px);
}
.login-title {
  font-size: 1.6rem;
  font-weight: 700;
  margin: 0;
}
.login-provider {
  justify-content: flex-start;
}
.login-divider {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--app-ink-subtle);
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 8px 0 -4px;
}
.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1 1 auto;
  height: 1px;
  background: var(--app-border);
}
.login-help-list {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.9rem;
  line-height: 1.6;
}
.login-help-list code {
  background: var(--app-surface);
  padding: 1px 6px;
  border-radius: 6px;
  font-size: 0.85em;
}
.app-banner {
  padding: 10px 14px;
  border-radius: var(--app-radius-md);
  background: color-mix(in srgb, var(--q-negative) 14%, transparent);
  color: var(--q-negative);
  font-size: 0.9rem;
}
.app-panel--muted {
  background: var(--app-surface-muted);
}
</style>
