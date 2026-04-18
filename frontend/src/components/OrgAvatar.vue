<template>
  <span
    class="org-avatar"
    :style="styleObject"
    :aria-label="ariaLabel"
    role="img"
  >
    <img v-if="src" :src="src" :alt="''" />
    <span v-else class="org-avatar__initials">{{ initials }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  name: string;
  avatarUrl?: string | null;
  primaryColor?: string | null;
  secondaryColor?: string | null;
  size?: number | string;
}

const props = withDefaults(defineProps<Props>(), {
  avatarUrl: null,
  primaryColor: null,
  secondaryColor: null,
  size: 48,
});

const ariaLabel = computed(() => props.name);

const src = computed(() => (props.avatarUrl ? props.avatarUrl : ''));

const initials = computed(() => {
  const parts = props.name
    .split(/[\s_\-/]+/u)
    .map((p) => p.trim())
    .filter(Boolean);
  if (parts.length === 0) return '?';
  const first = parts[0]?.[0] ?? '';
  const second = parts[1]?.[0] ?? '';
  return (first + second).toUpperCase() || '?';
});

const styleObject = computed<Record<string, string>>(() => {
  const size = typeof props.size === 'number' ? `${props.size}px` : props.size;
  const style: Record<string, string> = {
    width: size,
    height: size,
    fontSize: `calc(${size} / 2.4)`,
  };
  if (props.primaryColor) {
    const end = props.secondaryColor ?? props.primaryColor;
    style.background = `linear-gradient(135deg, ${props.primaryColor}, ${end})`;
  }
  return style;
});
</script>

<style scoped lang="scss">
.org-avatar__initials {
  line-height: 1;
  user-select: none;
}
</style>
