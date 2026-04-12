<template>
  <q-page class="q-pa-md">
    <div class="column q-gutter-md" style="max-width: 640px">
      <div class="text-h5">{{ t('profile.title') }}</div>
      <q-banner v-if="auth.user" rounded class="bg-grey-2">
        <div class="text-body1"><strong>{{ t('profile.username') }}</strong> {{ auth.user.username }}</div>
        <div class="text-body2 q-mt-sm">{{ auth.user.bio || t('profile.noBio') }}</div>
      </q-banner>
      <q-btn color="negative" outline :label="t('auth.logout')" @click="onLogout" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import { useAuthStore } from 'src/stores/auth-store';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const auth = useAuthStore();

async function onLogout() {
  await auth.logout();
  $q.notify({ type: 'info', message: t('auth.loggedOut') });
  await router.replace({ name: 'home' });
}
</script>
