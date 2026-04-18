<template>
  <q-page class="app-container q-py-xl">
    <PageHeader :title="t('messages.title')" :lead="t('messages.lead')">
      <template #actions>
        <q-btn unelevated color="primary" icon="edit" :label="t('messages.compose.cta')">
          <q-menu auto-close>
            <q-list style="min-width: 240px">
              <q-item clickable @click="openCompose()">
                <q-item-section avatar>
                  <q-icon name="person" />
                </q-item-section>
                <q-item-section>{{ t('messages.compose.title') }}</q-item-section>
              </q-item>
              <q-item clickable @click="composeMode = 'superusers'; composeOpen = true">
                <q-item-section avatar>
                  <q-icon name="shield_person" color="primary" />
                </q-item-section>
                <q-item-section>{{ t('messages.compose.toSuperusers') }}</q-item-section>
              </q-item>
            </q-list>
          </q-menu>
        </q-btn>
      </template>
    </PageHeader>

    <section class="app-panel">
      <div class="row items-center justify-between q-mb-md">
        <q-tabs
          v-model="tab"
          dense
          inline-label
          active-color="primary"
          indicator-color="primary"
          align="left"
          narrow-indicator
        >
          <q-tab name="inbox" :label="t('messages.inboxTab')" icon="inbox" />
          <q-tab name="sent" :label="t('messages.sentTab')" icon="send" />
        </q-tabs>

        <div class="row q-gutter-sm items-center">
          <q-select
            v-if="tab === 'inbox'"
            v-model="filter"
            dense
            outlined
            :options="filterOptions"
            :label="t('messages.filter.label')"
            emit-value
            map-options
            style="min-width: 180px"
          />
          <q-btn
            v-if="tab === 'inbox' && store.unread > 0"
            flat
            dense
            icon="mark_email_read"
            :label="t('messages.markAllRead')"
            @click="onMarkAllRead"
          />
        </div>
      </div>

      <q-separator class="q-mb-md" />

      <q-tab-panels v-model="tab" animated>
        <q-tab-panel name="inbox" class="q-pa-none">
          <EmptyState
            v-if="filteredInbox.length === 0"
            icon="inbox"
            :title="filter === 'unread' ? t('messages.emptyUnread') : t('messages.empty')"
          />
          <q-list v-else separator class="app-surface">
            <q-item
              v-for="m in filteredInbox"
              :key="m.id"
              clickable
              :class="{ 'message--unread': m.read_at === null }"
              @click="onMessageClick(m)"
            >
              <q-item-section avatar>
                <OrgAvatar
                  :name="m.sender_username ?? t('messages.fromAnonymous')"
                  :size="36"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  <strong>{{ m.sender_username ?? t('messages.fromAnonymous') }}</strong>
                  <q-badge
                    :color="badgeColor(m.target_kind)"
                    class="q-ml-sm"
                    align="middle"
                  >
                    {{ renderTargetBadge(m) }}
                  </q-badge>
                </q-item-label>
                <q-item-label caption>{{ formatDate(m.created_at) }}</q-item-label>
                <q-item-label class="q-mt-xs">{{ m.body }}</q-item-label>
              </q-item-section>
              <q-item-section side top>
                <q-btn
                  v-if="m.read_at === null"
                  flat
                  dense
                  round
                  icon="mark_email_read"
                  :title="t('messages.markRead')"
                  @click.stop="void store.markRead(m.id)"
                />
                <q-btn
                  v-if="m.sender_username && m.sender_id !== auth.user?.id"
                  flat
                  dense
                  round
                  icon="reply"
                  :title="t('messages.reply')"
                  @click.stop="openCompose(m.sender_username)"
                />
              </q-item-section>
            </q-item>
          </q-list>
        </q-tab-panel>

        <q-tab-panel name="sent" class="q-pa-none">
          <EmptyState
            v-if="store.sent.length === 0"
            icon="send"
            :title="t('messages.empty')"
          />
          <q-list v-else separator class="app-surface">
            <q-item v-for="m in store.sent" :key="m.id">
              <q-item-section avatar>
                <OrgAvatar
                  :name="m.recipient_username ?? ''"
                  :size="36"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>
                  <strong>{{ m.recipient_username }}</strong>
                  <q-badge
                    :color="badgeColor(m.target_kind)"
                    class="q-ml-sm"
                    align="middle"
                  >
                    {{ renderTargetBadge(m) }}
                  </q-badge>
                </q-item-label>
                <q-item-label caption>{{ formatDate(m.created_at) }}</q-item-label>
                <q-item-label class="q-mt-xs">{{ m.body }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </q-tab-panel>
      </q-tab-panels>
    </section>

    <MessageComposeDialog
      v-model="composeOpen"
      :mode="composeMode"
      :initial-recipient="initialRecipient"
      @sent="onSent"
    />
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { useQuasar } from 'quasar';

import EmptyState from 'components/EmptyState.vue';
import MessageComposeDialog from 'components/MessageComposeDialog.vue';
import OrgAvatar from 'components/OrgAvatar.vue';
import PageHeader from 'components/PageHeader.vue';
import { useAuthStore } from 'src/stores/auth-store';
import { useMessagesStore, type Message } from 'src/stores/messages-store';

const { t } = useI18n();
const $q = useQuasar();
const store = useMessagesStore();
const auth = useAuthStore();

const tab = ref<'inbox' | 'sent'>('inbox');
const filter = ref<'all' | 'unread' | 'direct' | 'org_owners' | 'superusers'>('all');
const composeOpen = ref(false);
const composeMode = ref<'direct' | 'superusers' | 'org_owners'>('direct');
const initialRecipient = ref<string | undefined>();

const filterOptions = computed(() => [
  { value: 'all', label: t('messages.filter.all') },
  { value: 'unread', label: t('messages.filter.unread') },
  { value: 'direct', label: t('messages.filter.direct') },
  { value: 'org_owners', label: t('messages.filter.org') },
  { value: 'superusers', label: t('messages.filter.superusers') },
]);

const filteredInbox = computed<Message[]>(() => {
  const rows = store.inbox;
  if (filter.value === 'all') return rows;
  if (filter.value === 'unread') return rows.filter((m) => m.read_at === null);
  return rows.filter((m) => m.target_kind === filter.value);
});

function openCompose(recipient?: string): void {
  composeMode.value = 'direct';
  initialRecipient.value = recipient;
  composeOpen.value = true;
}

function onSent(): void {
  void store.refreshInbox();
  void store.refreshSent();
}

async function onMarkAllRead(): Promise<void> {
  await store.markAllRead();
  $q.notify({ type: 'positive', message: t('messages.markAllRead') });
}

function onMessageClick(m: Message): void {
  if (m.read_at === null) void store.markRead(m.id);
}

function badgeColor(kind: Message['target_kind']): string {
  if (kind === 'superusers') return 'primary';
  if (kind === 'org_owners') return 'secondary';
  return 'grey-7';
}

function renderTargetBadge(m: Message): string {
  if (m.target_kind === 'org_owners') {
    return t('messages.targetBadge.org_owners', { slug: m.target_org_slug ?? '—' });
  }
  if (m.target_kind === 'superusers') {
    return t('messages.targetBadge.superusers');
  }
  return t('messages.targetBadge.direct');
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

onMounted(() => {
  void store.refreshInbox();
  void store.refreshSent();
});

watch(tab, (next) => {
  if (next === 'sent' && store.sent.length === 0) void store.refreshSent();
});
</script>

<style scoped lang="scss">
.message--unread {
  background: var(--q-primary-50, rgba(99, 102, 241, 0.06));
}
</style>
