<template>
  <section class="app-panel">
    <header class="alerts-panel__header">
      <div>
        <h2 class="alerts-panel__title">{{ title }}</h2>
        <p class="app-muted q-ma-none">{{ lead }}</p>
      </div>
      <q-btn
        unelevated
        color="primary"
        icon="add"
        :label="t('alerts.crud.newCta')"
        @click="openForm()"
      />
    </header>
    <q-separator class="q-my-md" />

    <EmptyState
      v-if="!loading && rows.length === 0"
      icon="campaign"
      :title="t('alerts.crud.emptyTitle')"
      :description="t('alerts.crud.emptyDesc')"
    />

    <q-list v-else separator bordered>
      <q-item v-for="row in rows" :key="row.id">
        <q-item-section avatar>
          <q-icon :name="severityIcon(row.severity)" :color="severityColor(row.severity)" />
        </q-item-section>
        <q-item-section>
          <q-item-label>
            {{ row.title }}
            <q-chip
              dense
              size="sm"
              :color="severityColor(row.severity)"
              text-color="white"
              class="q-ml-xs"
            >
              {{ t(`alerts.severity.${row.severity}`) }}
            </q-chip>
          </q-item-label>
          <q-item-label caption class="q-mt-xs" style="white-space: pre-wrap">
            {{ row.body }}
          </q-item-label>
          <q-item-label caption class="app-muted q-mt-xs">
            {{ windowLabel(row) }}
          </q-item-label>
        </q-item-section>
        <q-item-section side top>
          <q-btn
            flat
            dense
            round
            icon="delete"
            color="negative"
            :loading="deleting === row.id"
            @click="onDelete(row.id)"
          />
        </q-item-section>
      </q-item>
    </q-list>

    <q-dialog v-model="formOpen">
      <q-card style="min-width: 420px; max-width: 560px; width: 100%">
        <q-card-section>
          <p class="text-h6 q-ma-none">{{ t('alerts.crud.formTitle') }}</p>
        </q-card-section>
        <q-card-section class="column q-gutter-md">
          <q-input
            v-model="form.title"
            outlined
            :label="t('alerts.crud.fields.title')"
            :maxlength="200"
            counter
          />
          <q-input
            v-model="form.body"
            outlined
            type="textarea"
            autogrow
            :label="t('alerts.crud.fields.body')"
            :maxlength="2000"
            counter
          />
          <q-select
            v-model="form.severity"
            outlined
            :options="severityOptions"
            :label="t('alerts.crud.fields.severity')"
            emit-value
            map-options
          />
          <div class="row q-gutter-md">
            <q-input
              v-model="form.starts_at"
              outlined
              type="datetime-local"
              :label="t('alerts.crud.fields.startsAt')"
              class="col"
              :hint="t('alerts.crud.fields.startsAtHint')"
            />
            <q-input
              v-model="form.ends_at"
              outlined
              type="datetime-local"
              :label="t('alerts.crud.fields.endsAt')"
              class="col"
              :hint="t('alerts.crud.fields.endsAtHint')"
            />
          </div>
          <q-toggle v-model="form.dismissible" :label="t('alerts.crud.fields.dismissible')" />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat :label="t('actions.cancel')" v-close-popup />
          <q-btn
            unelevated
            color="primary"
            :label="t('alerts.crud.saveCta')"
            :disable="!canSubmit"
            :loading="submitting"
            @click="onSubmit"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </section>
</template>

<script setup lang="ts">
import { useQuasar } from 'quasar';
import { computed, onMounted, reactive, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import EmptyState from 'components/EmptyState.vue';
import { useAlertsStore, type OrgAlert, type SystemAnnouncement } from 'src/stores/alerts-store';

type Severity = 'info' | 'warning' | 'critical';
type AlertRow = (SystemAnnouncement | OrgAlert) & {
  starts_at?: string | null;
  ends_at?: string | null;
};

interface Props {
  kind: 'system' | 'org';
  orgSlug?: string;
  title: string;
  lead: string;
}

const props = defineProps<Props>();
const { t } = useI18n();
const $q = useQuasar();
const alerts = useAlertsStore();

const rows = ref<AlertRow[]>([]);
const loading = ref(false);
const deleting = ref<string | null>(null);

const formOpen = ref(false);
const submitting = ref(false);
const form = reactive<{
  title: string;
  body: string;
  severity: Severity;
  starts_at: string;
  ends_at: string;
  dismissible: boolean;
}>({
  title: '',
  body: '',
  severity: 'info',
  starts_at: '',
  ends_at: '',
  dismissible: true,
});

const severityOptions = computed(() => [
  { label: t('alerts.severity.info'), value: 'info' },
  { label: t('alerts.severity.warning'), value: 'warning' },
  { label: t('alerts.severity.critical'), value: 'critical' },
]);

const canSubmit = computed(() => form.title.trim().length > 0 && form.body.trim().length > 0);

async function reload(): Promise<void> {
  loading.value = true;
  try {
    if (props.kind === 'system') {
      const list = await alerts.listAllSystem();
      rows.value = (list ?? []) as AlertRow[];
    } else if (props.orgSlug) {
      const list = await alerts.listAllForOrg(props.orgSlug);
      rows.value = (list ?? []) as AlertRow[];
    }
  } finally {
    loading.value = false;
  }
}

function openForm(): void {
  form.title = '';
  form.body = '';
  form.severity = 'info';
  form.starts_at = '';
  form.ends_at = '';
  form.dismissible = true;
  formOpen.value = true;
}

function toIso(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = new Date(trimmed);
  if (Number.isNaN(parsed.getTime())) return undefined;
  return parsed.toISOString();
}

async function onSubmit(): Promise<void> {
  submitting.value = true;
  try {
    const body = {
      title: form.title.trim(),
      body: form.body.trim(),
      severity: form.severity,
      dismissible: form.dismissible,
      starts_at: toIso(form.starts_at) ?? null,
      ends_at: toIso(form.ends_at) ?? null,
    };
    let created: AlertRow | null = null;
    if (props.kind === 'system') {
      created = (await alerts.createSystem(body)) as AlertRow | null;
    } else if (props.orgSlug) {
      created = (await alerts.createForOrg(props.orgSlug, body)) as AlertRow | null;
    }
    if (!created) {
      $q.notify({ type: 'negative', message: t('alerts.crud.errors.create') });
      return;
    }
    $q.notify({ type: 'positive', message: t('alerts.crud.messages.created') });
    formOpen.value = false;
    await reload();
  } finally {
    submitting.value = false;
  }
}

async function onDelete(id: string): Promise<void> {
  deleting.value = id;
  try {
    let ok = false;
    if (props.kind === 'system') {
      ok = await alerts.deleteSystem(id);
    } else if (props.orgSlug) {
      ok = await alerts.deleteForOrg(props.orgSlug, id);
    }
    if (!ok) {
      $q.notify({ type: 'negative', message: t('alerts.crud.errors.delete') });
      return;
    }
    $q.notify({ type: 'positive', message: t('alerts.crud.messages.deleted') });
    await reload();
  } finally {
    deleting.value = null;
  }
}

function severityIcon(s: Severity): string {
  if (s === 'critical') return 'error';
  if (s === 'warning') return 'warning';
  return 'campaign';
}
function severityColor(s: Severity): string {
  if (s === 'critical') return 'negative';
  if (s === 'warning') return 'warning';
  return 'primary';
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function windowLabel(row: AlertRow): string {
  return t('alerts.crud.window', {
    start: formatDate(row.starts_at),
    end: formatDate(row.ends_at),
  });
}

onMounted(() => {
  void reload();
});
</script>

<style scoped lang="scss">
.alerts-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}
.alerts-panel__title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}
</style>
