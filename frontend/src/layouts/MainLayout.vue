<template>
  <q-layout view="lHh Lpr lFf">
    <q-header elevated>
      <q-toolbar>
        <q-btn
          flat
          dense
          round
          icon="menu"
          :aria-label="t('layout.menu')"
          @click="toggleLeftDrawer"
        />

        <q-toolbar-title>
          {{ t('app.title') }}
        </q-toolbar-title>

        <div class="text-caption">Quasar v{{ $q.version }}</div>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      bordered
      :aria-label="t('layout.drawerAria')"
    >
      <q-list padding>
        <q-item clickable :to="{ name: 'home' }" exact>
          <q-item-section avatar>
            <q-icon name="home" />
          </q-item-section>
          <q-item-section>{{ t('home.title') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated" clickable :to="{ name: 'orgs' }">
          <q-item-section avatar>
            <q-icon name="groups" />
          </q-item-section>
          <q-item-section>{{ t('orgs.title') }}</q-item-section>
        </q-item>
        <q-item v-if="auth.isAuthenticated" clickable :to="{ name: 'profile' }">
          <q-item-section avatar>
            <q-icon name="person" />
          </q-item-section>
          <q-item-section>{{ t('profile.title') }}</q-item-section>
        </q-item>
        <q-item v-else clickable :to="{ name: 'login' }">
          <q-item-section avatar>
            <q-icon name="login" />
          </q-item-section>
          <q-item-section>{{ t('auth.loginNav') }}</q-item-section>
        </q-item>
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';

import { useAuthStore } from 'src/stores/auth-store';

const { t } = useI18n();
const auth = useAuthStore();

const leftDrawerOpen = ref(false);

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value;
}
</script>
