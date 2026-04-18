<template>
  <div class="palette-field">
    <div class="palette-field__row">
      <label class="palette-field__swatch" :style="{ background: normalized || 'transparent' }">
        <input
          type="color"
          :value="normalized || fallback"
          :aria-label="t('theme.colorPicker', { label })"
          @input="onPick"
        />
      </label>
      <q-input
        :model-value="modelValue ?? ''"
        outlined
        dense
        class="palette-field__hex"
        :label="label"
        :hint="hint ?? t('theme.hexHint')"
        :rules="[validate]"
        lazy-rules
        placeholder="#4f46e5"
        @update:model-value="onType"
      >
        <template #append>
          <q-btn
            v-if="modelValue"
            flat
            dense
            round
            size="sm"
            icon="close"
            :aria-label="t('theme.clearColor')"
            @click="emit('update:modelValue', null)"
          />
        </template>
      </q-input>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

interface Props {
  modelValue: string | null;
  label: string;
  hint?: string;
  fallback?: string;
}

const props = withDefaults(defineProps<Props>(), {
  fallback: '#4f46e5',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void;
}>();

const { t } = useI18n();

const HEX_RE = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/u;

const normalized = computed<string>(() => {
  if (!props.modelValue) return '';
  return HEX_RE.test(props.modelValue) ? props.modelValue : '';
});

function validate(value: string): boolean | string {
  if (!value) return true;
  return HEX_RE.test(value) || t('theme.invalidHex');
}

function onPick(event: Event): void {
  const target = event.target as HTMLInputElement;
  emit('update:modelValue', target.value.toLowerCase());
}

function onType(value: string | number | null): void {
  if (value === null || value === '') {
    emit('update:modelValue', null);
    return;
  }
  emit('update:modelValue', String(value));
}
</script>

<style scoped lang="scss">
.palette-field__row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.palette-field__swatch {
  position: relative;
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  border-radius: 12px;
  border: 1px solid var(--app-border);
  box-shadow: var(--app-shadow-sm);
  cursor: pointer;
  overflow: hidden;
}
.palette-field__swatch input[type='color'] {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
  padding: 0;
  opacity: 0;
  cursor: pointer;
}
.palette-field__hex {
  flex: 1 1 auto;
  min-width: 0;
}
</style>
