<template>
  <q-page class="q-pa-md">
    <div class="column q-gutter-md" style="max-width: 720px">
      <div>
        <h1 class="text-h4">{{ t('home.title') }}</h1>
        <div class="text-body1 text-grey-7">{{ t('home.lead') }}</div>
      </div>

      <div class="row q-gutter-sm items-center">
        <q-btn
          color="primary"
          :loading="loading"
          :label="t('home.pingBackend')"
          @click="pingBackend"
        />
        <div v-if="statusText" class="text-body2">{{ statusText }}</div>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { getApiClient } from 'src/api/client';

const { t } = useI18n();

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

async function pingBackend() {
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
