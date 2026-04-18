<template>
  <q-dialog :model-value="visible" persistent @update:model-value="onClose">
    <q-card :class="cardClass" style="min-width: 360px; max-width: 560px; width: 100%">
      <q-card-section class="row items-start q-gutter-md">
        <q-icon :name="iconName" size="32px" :class="iconClass" />
        <div class="col">
          <p class="text-h6 q-ma-none">{{ current?.title }}</p>
          <p class="app-muted q-mt-xs q-mb-none">
            {{ formatDate(current?.created_at) }}
          </p>
        </div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <p class="q-ma-none" style="white-space: pre-wrap">{{ current?.body }}</p>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn
          v-if="current?.dismissible !== false"
          unelevated
          color="primary"
          :label="t('alerts.dismiss')"
          @click="onDismiss"
        />
        <q-btn v-else unelevated color="primary" :label="t('alerts.ok')" @click="onClose(false)" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';

interface AlertLike {
  id: string;
  title: string;
  body: string;
  severity: 'info' | 'warning' | 'critical';
  dismissible: boolean;
  created_at: string;
}

interface Props {
  alerts: AlertLike[];
  kind: 'system' | 'org';
}

const props = defineProps<Props>();
const emit = defineEmits<{ (e: 'acknowledge', alertId: string): void }>();

const { t } = useI18n();

// Index tracks position in `props.alerts`; we only close the dialog when
// every alert in the list has been handled so the user sees each one.
const index = ref(0);
const visible = ref(false);
const current = computed(() => props.alerts[index.value] ?? null);

const cardClass = computed(() => {
  if (current.value?.severity === 'critical') return 'alert-dialog--critical';
  if (current.value?.severity === 'warning') return 'alert-dialog--warning';
  return 'alert-dialog--info';
});

const iconName = computed(() => {
  if (current.value?.severity === 'critical') return 'error';
  if (current.value?.severity === 'warning') return 'warning';
  return 'campaign';
});

const iconClass = computed(() => {
  if (current.value?.severity === 'critical') return 'text-negative';
  if (current.value?.severity === 'warning') return 'text-warning';
  return 'text-primary';
});

watch(
  () => props.alerts.length,
  (count) => {
    if (count > 0) {
      index.value = 0;
      visible.value = true;
    } else {
      visible.value = false;
    }
  },
  { immediate: true },
);

function advance(): void {
  if (index.value + 1 < props.alerts.length) {
    index.value += 1;
  } else {
    visible.value = false;
  }
}

function onDismiss(): void {
  const alertId = current.value?.id;
  if (alertId) emit('acknowledge', alertId);
  advance();
}

function onClose(value: boolean): void {
  if (!value) advance();
}

function formatDate(iso: string | undefined): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}
</script>

<style scoped lang="scss">
.alert-dialog--critical {
  border-top: 4px solid var(--q-negative);
}
.alert-dialog--warning {
  border-top: 4px solid var(--q-warning);
}
.alert-dialog--info {
  border-top: 4px solid var(--q-primary);
}
</style>
