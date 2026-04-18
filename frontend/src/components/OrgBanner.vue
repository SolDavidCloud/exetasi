<template>
  <div class="org-banner" :class="{ 'org-banner--compact': compact }">
    <img
      v-if="bannerUrl"
      class="org-banner__image"
      :src="bannerUrl"
      :alt="''"
      loading="lazy"
    />
    <div v-if="bannerUrl" class="org-banner__overlay" aria-hidden="true" />
    <slot />
  </div>
</template>

<script setup lang="ts">
interface Props {
  bannerUrl?: string | null;
  compact?: boolean;
}

withDefaults(defineProps<Props>(), {
  bannerUrl: null,
  compact: false,
});
</script>

<style scoped lang="scss">
.org-banner--compact {
  height: clamp(80px, 14vw, 120px);
  border-radius: var(--app-radius-md);
}
</style>
