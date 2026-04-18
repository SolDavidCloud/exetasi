<template>
  <q-dialog v-model="model">
    <q-card style="min-width: 360px; max-width: 520px; width: 100%">
      <q-card-section>
        <p class="text-h6 q-ma-none">{{ t('messages.compose.title') }}</p>
        <p v-if="mode !== 'direct'" class="app-muted q-mt-xs q-mb-none">
          {{
            mode === 'superusers'
              ? t('messages.compose.superusersLead')
              : t('messages.compose.orgOwnersLead')
          }}
        </p>
      </q-card-section>
      <q-card-section class="column q-gutter-md">
        <q-input
          v-if="mode === 'direct'"
          v-model="recipient"
          outlined
          autofocus
          :label="t('messages.compose.recipient')"
          :hint="t('messages.compose.recipientHint')"
          :rules="[(v) => !!v?.trim() || t('messages.compose.recipient')]"
        />
        <q-input
          v-model="body"
          outlined
          type="textarea"
          autogrow
          :autofocus="mode !== 'direct'"
          :label="t('messages.compose.body')"
          :hint="t('messages.compose.bodyHint')"
          :maxlength="500"
          counter
        />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn flat :label="t('actions.cancel')" v-close-popup />
        <q-btn
          unelevated
          color="primary"
          :label="t('messages.compose.send')"
          :loading="sending"
          :disable="!canSend"
          @click="onSend"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';

import { useMessagesStore } from 'src/stores/messages-store';

interface Props {
  modelValue: boolean;
  initialRecipient?: string | undefined;
  mode?: 'direct' | 'superusers' | 'org_owners';
  orgSlug?: string | undefined;
}

const props = withDefaults(defineProps<Props>(), {
  initialRecipient: undefined,
  mode: 'direct',
  orgSlug: undefined,
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void;
  (e: 'sent', count: number): void;
}>();

const { t } = useI18n();
const $q = useQuasar();
const store = useMessagesStore();

const model = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

const recipient = ref<string>(props.initialRecipient ?? '');
const body = ref<string>('');
const sending = ref(false);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      recipient.value = props.initialRecipient ?? '';
      body.value = '';
    }
  },
);

const canSend = computed(() => {
  if (!body.value.trim()) return false;
  if (props.mode === 'direct' && !recipient.value.trim()) return false;
  if (props.mode === 'org_owners' && !props.orgSlug) return false;
  return true;
});

async function onSend(): Promise<void> {
  sending.value = true;
  try {
    if (props.mode === 'direct') {
      const ok = await store.sendToUser(recipient.value.trim(), body.value.trim());
      if (!ok) {
        $q.notify({ type: 'negative', message: t('messages.unknownRecipient') });
        return;
      }
      $q.notify({ type: 'positive', message: t('messages.toastSent') });
      emit('sent', 1);
    } else if (props.mode === 'superusers') {
      const count = await store.sendToSuperusers(body.value.trim());
      if (count === null) {
        $q.notify({ type: 'negative', message: t('messages.toastFailed') });
        return;
      }
      $q.notify({
        type: 'positive',
        message: t('messages.toastFanout', { count }),
      });
      emit('sent', count);
    } else if (props.mode === 'org_owners' && props.orgSlug) {
      const count = await store.sendToOrgOwners(props.orgSlug, body.value.trim());
      if (count === null) {
        $q.notify({ type: 'negative', message: t('messages.toastFailed') });
        return;
      }
      $q.notify({
        type: 'positive',
        message: t('messages.toastFanout', { count }),
      });
      emit('sent', count);
    }
    model.value = false;
  } finally {
    sending.value = false;
  }
}
</script>
