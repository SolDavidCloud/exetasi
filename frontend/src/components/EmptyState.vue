<template>
  <div class="empty-state app-panel">
    <div class="empty-state__icon" aria-hidden="true">
      <q-icon :name="icon" size="40px" />
    </div>
    <div class="empty-state__text">
      <p class="empty-state__title">{{ title }}</p>
      <p v-if="description" class="empty-state__desc app-muted">{{ description }}</p>
    </div>
    <div v-if="$slots.default" class="empty-state__actions">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  title: string;
  description?: string;
  icon?: string;
}

withDefaults(defineProps<Props>(), {
  description: '',
  icon: 'auto_awesome',
});
</script>

<style scoped lang="scss">
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  padding: clamp(28px, 4vw, 48px);
}
.empty-state__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--app-brand-soft);
  color: var(--q-primary);
}
.empty-state__title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}
.empty-state__desc {
  margin: 0;
  max-width: 48ch;
}
.empty-state__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
