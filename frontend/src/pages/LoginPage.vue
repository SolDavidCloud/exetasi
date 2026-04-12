<template>
  <q-page class="flex flex-center q-pa-md">
    <q-card flat bordered style="width: 100%; max-width: 420px">
      <q-card-section>
        <div class="text-h5">{{ t('auth.loginTitle') }}</div>
        <div class="text-body2 text-grey-7 q-mt-sm">{{ t('auth.loginLead') }}</div>
      </q-card-section>

      <q-card-section class="q-gutter-md">
        <q-btn
          outline
          color="primary"
          class="full-width"
          :label="t('auth.provider.google')"
          :href="oauthStartUrl('/api/v1/auth/google/start')"
          type="a"
        />
        <q-btn
          color="dark"
          class="full-width"
          :label="t('auth.provider.github')"
          :href="oauthStartUrl('/api/v1/auth/github/start')"
          type="a"
        />
        <q-btn
          outline
          color="secondary"
          class="full-width"
          :label="t('auth.provider.gitlab')"
          :href="oauthStartUrl('/api/v1/auth/gitlab/start')"
          type="a"
        />

        <template v-if="isDev">
          <q-separator />
          <div class="text-caption text-grey-7">{{ t('auth.devLoginHint') }}</div>
          <q-input v-model="username" outlined dense :label="t('auth.username')" />
          <q-btn
            color="primary"
            class="full-width"
            :label="t('auth.devLogin')"
            :loading="loading"
            @click="onDevLogin"
          />
        </template>
      </q-card-section>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import { getApiBaseUrl } from 'src/api/client';
import { useAuthStore } from 'src/stores/auth-store';

const { t } = useI18n();
const $q = useQuasar();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const username = ref('alice');
const loading = ref(false);

const isDev = import.meta.env.DEV;

function oauthStartUrl(path: string): string {
  const base = getApiBaseUrl();
  if (base.length === 0) {
    return path;
  }
  return `${base}${path}`;
}

async function onDevLogin() {
  loading.value = true;
  try {
    await auth.devLogin(username.value.trim());
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
    await router.replace(redirect);
  } catch {
    $q.notify({ type: 'negative', message: t('auth.devLoginFailed') });
  } finally {
    loading.value = false;
  }
}
</script>
