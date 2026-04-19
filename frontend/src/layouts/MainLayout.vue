<template>
  <q-layout view="hHh Lpr lff">
    <q-header flat class="app-header">
      <q-toolbar class="app-container">
        <q-btn
          flat
          dense
          round
          icon="menu"
          class="lt-md"
          :aria-label="t('layout.menu')"
          @click="toggleLeftDrawer"
        />
        <AppLogo class="q-mr-md" />

        <q-space />

        <q-btn
          flat
          round
          dense
          :icon="themeIcon"
          :aria-label="t('layout.toggleTheme')"
          :aria-pressed="theme.isDark"
          @click="theme.toggle"
        />

        <template v-if="auth.isAuthenticated && auth.user">
          <q-btn
            flat
            round
            dense
            icon="inbox"
            class="q-ml-sm"
            :aria-label="t('messages.navTitle')"
            :to="{ name: 'messages' }"
          >
            <q-badge
              v-if="messages.unread > 0"
              floating
              color="negative"
              rounded
              :label="String(messages.unread)"
            />
          </q-btn>
          <q-btn flat dense no-caps class="q-ml-sm app-user-btn">
            <OrgAvatar :name="auth.user.username" :avatar-url="auth.user.avatar_url" :size="32" />
            <span class="q-ml-sm gt-sm">{{ auth.user.username }}</span>
            <q-icon name="expand_more" class="q-ml-xs" />
            <q-menu anchor="bottom right" self="top right">
              <q-list style="min-width: 200px">
                <q-item clickable v-close-popup :to="{ name: 'profile' }">
                  <q-item-section avatar>
                    <q-icon name="person" />
                  </q-item-section>
                  <q-item-section>{{ t('profile.title') }}</q-item-section>
                </q-item>
                <q-item clickable v-close-popup :to="{ name: 'orgs' }">
                  <q-item-section avatar>
                    <q-icon name="groups" />
                  </q-item-section>
                  <q-item-section>{{ t('orgs.title') }}</q-item-section>
                </q-item>
                <q-item v-if="auth.isSuperuser" clickable v-close-popup :to="{ name: 'admin' }">
                  <q-item-section avatar>
                    <q-icon name="admin_panel_settings" size="24px" color="primary" />
                  </q-item-section>
                  <q-item-section>{{ t('admin.navTitle') }}</q-item-section>
                </q-item>
                <q-separator />
                <q-item clickable v-close-popup @click="onLogout">
                  <q-item-section avatar>
                    <q-icon name="logout" />
                  </q-item-section>
                  <q-item-section>{{ t('auth.logout') }}</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </template>
        <template v-else>
          <q-btn
            unelevated
            color="primary"
            class="q-ml-sm"
            :to="{ name: 'login' }"
            :label="t('auth.loginNav')"
          />
        </template>
      </q-toolbar>
    </q-header>

    <q-drawer
      v-model="leftDrawerOpen"
      show-if-above
      :width="260"
      :breakpoint="1024"
      bordered
      :aria-label="t('layout.drawerAria')"
    >
      <div class="app-drawer">
        <div class="app-drawer__section">
          <p class="app-drawer__heading">{{ t('layout.sections.explore') }}</p>
          <q-list padding>
            <q-item clickable :to="{ name: 'home' }" exact>
              <q-item-section avatar>
                <q-icon class="app-drawer__nav-icon" name="home" size="24px" />
              </q-item-section>
              <q-item-section>{{ t('home.navTitle') }}</q-item-section>
            </q-item>
            <q-item v-if="auth.isAuthenticated" clickable :to="{ name: 'orgs' }">
              <q-item-section avatar>
                <q-icon class="app-drawer__nav-icon" name="groups" size="24px" />
              </q-item-section>
              <q-item-section>{{ t('orgs.title') }}</q-item-section>
            </q-item>
            <q-item v-if="auth.isSuperuser" clickable :to="{ name: 'admin' }">
              <q-item-section avatar>
                <q-icon
                  class="app-drawer__nav-icon text-primary"
                  name="admin_panel_settings"
                  size="24px"
                  aria-hidden="true"
                />
              </q-item-section>
              <q-item-section>{{ t('admin.navTitle') }}</q-item-section>
            </q-item>
          </q-list>
        </div>

        <div v-if="auth.isAuthenticated && orgs.list.length" class="app-drawer__section">
          <p class="app-drawer__heading">{{ t('layout.sections.yourOrgs') }}</p>
          <q-list padding>
            <q-item
              v-for="o in orgs.list"
              :key="o.id"
              clickable
              :to="{ name: 'org-detail', params: { slug: o.slug } }"
            >
              <q-item-section avatar>
                <OrgAvatar
                  :name="o.name"
                  :avatar-url="o.avatar_url"
                  :primary-color="o.primary_color"
                  :secondary-color="o.secondary_color"
                  :size="28"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ o.name }}</q-item-label>
                <q-item-label caption>
                  {{ o.slug }} · {{ t(`orgs.roles.${o.role}`) }}
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <div v-if="auth.isAuthenticated" class="app-drawer__section">
          <p class="app-drawer__heading">{{ t('layout.sections.account') }}</p>
          <q-list padding>
            <q-item clickable :to="{ name: 'profile' }">
              <q-item-section avatar>
                <q-icon class="app-drawer__nav-icon" name="person" size="24px" />
              </q-item-section>
              <q-item-section>{{ t('profile.title') }}</q-item-section>
            </q-item>
            <q-item clickable :to="{ name: 'messages' }">
              <q-item-section avatar>
                <q-icon class="app-drawer__nav-icon" name="inbox" size="24px" />
              </q-item-section>
              <q-item-section>{{ t('messages.navTitle') }}</q-item-section>
              <q-item-section v-if="messages.unread > 0" side>
                <q-badge color="negative" rounded>{{ messages.unread }}</q-badge>
              </q-item-section>
            </q-item>
          </q-list>
        </div>
      </div>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>

    <AlertDialog
      :alerts="alerts.system"
      kind="system"
      @acknowledge="(id) => void alerts.acknowledge('system', id)"
    />
  </q-layout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';
import { useRouter } from 'vue-router';

import AlertDialog from 'components/AlertDialog.vue';
import AppLogo from 'components/AppLogo.vue';
import OrgAvatar from 'components/OrgAvatar.vue';
import { useAlertsStore } from 'src/stores/alerts-store';
import { useAuthStore } from 'src/stores/auth-store';
import { useMessagesStore } from 'src/stores/messages-store';
import { useOrgsStore } from 'src/stores/orgs-store';
import { useThemeStore } from 'src/stores/theme-store';

const { t } = useI18n();
const $q = useQuasar();
const router = useRouter();
const auth = useAuthStore();
const orgs = useOrgsStore();
const messages = useMessagesStore();
const alerts = useAlertsStore();
const theme = useThemeStore();

const leftDrawerOpen = ref(false);

const themeIcon = computed(() => (theme.isDark ? 'light_mode' : 'dark_mode'));

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value;
}

async function onLogout(): Promise<void> {
  await auth.logout();
  $q.notify({ type: 'info', message: t('auth.loggedOut') });
  await router.replace({ name: 'home' });
}

async function refreshOrgs(): Promise<void> {
  if (auth.isAuthenticated && !orgs.listLoaded) {
    await orgs.fetchAll();
  }
}

async function refreshInbox(): Promise<void> {
  if (auth.isAuthenticated) {
    await messages.refreshInbox();
  }
}

async function refreshAlerts(): Promise<void> {
  if (auth.isAuthenticated && !alerts.systemLoaded) {
    await alerts.refreshSystemActive();
  }
}

onMounted(() => {
  void refreshOrgs();
  void refreshInbox();
  void refreshAlerts();
});

watch(
  () => auth.isAuthenticated,
  (next) => {
    if (next) {
      void orgs.fetchAll();
      void messages.refreshInbox();
      void alerts.refreshSystemActive();
    } else {
      orgs.items = [];
      orgs.listLoaded = false;
      messages.reset();
      alerts.reset();
    }
  },
);
</script>

<style scoped lang="scss">
.app-header {
  position: sticky;
  top: 0;
}
.app-user-btn {
  border-radius: 999px;
  padding: 4px 10px 4px 4px;
}
.app-drawer {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 16px 8px;
}
.app-drawer__heading {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--app-ink-subtle);
  padding: 0 12px;
  margin: 0 0 6px;
}

/* Fixed-width icon rail so every drawer row’s label starts on the same x (incl. Admin vs Profile) */
.app-drawer :deep(.q-item .q-item__section--avatar) {
  width: 48px;
  min-width: 48px;
  max-width: 48px;
  flex: 0 0 48px;
  align-items: center;
  justify-content: center;
}
.app-drawer__nav-icon {
  width: 24px;
  height: 24px;
  flex: 0 0 24px;
}
</style>
