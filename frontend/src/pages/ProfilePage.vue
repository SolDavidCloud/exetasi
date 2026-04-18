<template>
  <q-page class="app-container app-container--narrow q-py-xl">
    <PageHeader :title="t('profile.title')" :lead="t('profile.lead')" />

    <section v-if="auth.user" class="app-panel column q-gutter-md">
      <div class="row items-center q-gutter-md">
        <OrgAvatar
          :name="auth.user.username"
          :avatar-url="auth.user.avatar_url"
          :size="72"
        />
        <div>
          <p class="text-h6 q-ma-none">{{ auth.user.username }}</p>
          <p class="app-muted q-ma-none">
            {{ auth.user.bio || t('profile.noBio') }}
          </p>
        </div>
      </div>
    </section>

    <section class="app-panel q-mt-md">
      <p class="section-head">{{ t('profile.appearance') }}</p>
      <p class="app-muted q-mt-xs q-mb-md">{{ t('profile.appearanceLead') }}</p>
      <q-option-group
        v-model="themeMode"
        inline
        :options="themeOptions"
        type="radio"
        color="primary"
      />
    </section>

    <section class="app-panel q-mt-md">
      <p class="section-head">{{ t('profile.sessionTitle') }}</p>
      <p class="app-muted q-mt-xs q-mb-md">{{ t('profile.sessionLead') }}</p>
      <q-btn
        outline
        color="negative"
        icon="logout"
        :label="t('auth.logout')"
        @click="onLogout"
      />
    </section>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useQuasar } from 'quasar';

import OrgAvatar from 'components/OrgAvatar.vue';
import PageHeader from 'components/PageHeader.vue';
import { useAuthStore } from 'src/stores/auth-store';
import { useThemeStore, type ThemeMode } from 'src/stores/theme-store';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const auth = useAuthStore();
const theme = useThemeStore();

const themeMode = computed<ThemeMode>({
  get: () => theme.mode,
  set: (value) => theme.setMode(value),
});

const themeOptions = computed(() => [
  { label: t('profile.themeAuto'), value: 'auto' as const },
  { label: t('profile.themeLight'), value: 'light' as const },
  { label: t('profile.themeDark'), value: 'dark' as const },
]);

async function onLogout() {
  await auth.logout();
  $q.notify({ type: 'info', message: t('auth.loggedOut') });
  await router.replace({ name: 'home' });
}
</script>

<style scoped lang="scss">
.section-head {
  font-weight: 700;
  font-size: 1.05rem;
  margin: 0;
}
</style>
