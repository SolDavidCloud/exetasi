<template>
  <header class="page-header">
    <div class="page-header__text">
      <p v-if="eyebrow" class="app-chip">{{ eyebrow }}</p>
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="lead" class="page-header__lead app-muted">{{ lead }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
interface Props {
  title: string;
  lead?: string;
  eyebrow?: string;
}

defineProps<Props>();
</script>

<style scoped lang="scss">
.page-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  margin-bottom: 24px;
}
.page-header__text {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.page-header__title {
  font-size: clamp(1.6rem, 2.8vw, 2.1rem);
  font-weight: 700;
  margin: 0;
  line-height: 1.15;
}
.page-header__lead {
  margin: 0;
  font-size: 1rem;
  max-width: 60ch;
}
.page-header__actions {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
</style>
