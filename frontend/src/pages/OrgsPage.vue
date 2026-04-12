<template>
  <q-page class="q-pa-md">
    <div class="column q-gutter-md" style="max-width: 720px">
      <div class="text-h5">{{ t('orgs.title') }}</div>
      <q-list v-if="orgs.length" bordered separator>
        <q-item v-for="o in orgs" :key="o.id">
          <q-item-section>
            <q-item-label>{{ o.name }}</q-item-label>
            <q-item-label caption>{{ o.slug }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat dense color="primary" :label="t('orgs.viewExams')" @click="loadExams(o.slug)" />
          </q-item-section>
        </q-item>
      </q-list>
      <q-banner v-else rounded class="bg-grey-2">{{ t('orgs.empty') }}</q-banner>

      <q-separator />

      <div class="text-subtitle1">{{ t('orgs.createTitle') }}</div>
      <q-input v-model="newName" outlined dense :label="t('orgs.name')" />
      <q-btn color="primary" :label="t('orgs.create')" :loading="creating" @click="createOrg" />

      <q-banner v-if="exams.length" rounded class="bg-blue-1 q-mt-md">
        <div class="text-subtitle2">{{ t('orgs.examsFor', { slug: activeSlug }) }}</div>
        <ul class="q-my-sm">
          <li v-for="e in exams" :key="e.id">{{ e.name }}</li>
        </ul>
      </q-banner>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';

import { getApiClient } from 'src/api/client';

const { t } = useI18n();
const $q = useQuasar();

const orgs = ref<
  Array<{
    id: string;
    name: string;
    slug: string;
    description: string;
    avatar_url: string | null;
    is_personal: boolean;
  }>
>([]);

const exams = ref<Array<{ id: string; name: string; is_archived: boolean; visibility: string }>>(
  [],
);
const activeSlug = ref('');
const newName = ref('');
const creating = ref(false);

async function refresh() {
  const { data, error } = await getApiClient().GET('/api/v1/orgs');
  if (error) {
    orgs.value = [];
    return;
  }
  orgs.value = data ?? [];
}

async function loadExams(slug: string) {
  activeSlug.value = slug;
  const { data, error } = await getApiClient().GET('/api/v1/orgs/{org_slug}/exams', {
    params: { path: { org_slug: slug } },
  });
  if (error) {
    exams.value = [];
    return;
  }
  exams.value = data ?? [];
}

async function createOrg() {
  creating.value = true;
  try {
    const { error } = await getApiClient().POST('/api/v1/orgs', {
      body: { name: newName.value.trim(), description: '' },
    });
    if (error) {
      $q.notify({ type: 'negative', message: t('orgs.createFailed') });
      return;
    }
    newName.value = '';
    await refresh();
  } finally {
    creating.value = false;
  }
}

onMounted(() => {
  void refresh();
});
</script>
