import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';

export type Message = components['schemas']['MessagePublic'];

/**
 * Inbox + outbox state for the messaging feature. Sorting and filtering
 * live client-side (the backend just returns rows in reverse chronological
 * order) so the user can switch lenses instantly.
 */
export const useMessagesStore = defineStore('messages', () => {
  const inbox = ref<Message[]>([]);
  const sent = ref<Message[]>([]);
  const unread = ref(0);
  const loading = ref(false);
  const lastError = ref<string | null>(null);

  const unreadMessages = computed(() => inbox.value.filter((m) => m.read_at === null));

  async function refreshInbox(): Promise<void> {
    loading.value = true;
    try {
      const { data, error } = await getApiClient().GET('/api/v1/messages', {});
      if (error || !data) {
        lastError.value = 'inbox_load_failed';
        return;
      }
      inbox.value = data.items;
      unread.value = data.unread;
      lastError.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function refreshSent(): Promise<void> {
    loading.value = true;
    try {
      const { data, error } = await getApiClient().GET('/api/v1/messages/sent', {});
      if (error || !data) {
        lastError.value = 'sent_load_failed';
        return;
      }
      sent.value = data;
      lastError.value = null;
    } finally {
      loading.value = false;
    }
  }

  async function sendToUser(username: string, body: string): Promise<boolean> {
    const { data, error } = await getApiClient().POST('/api/v1/messages/to-user', {
      body: { recipient_username: username, body },
    });
    if (error || !data) {
      // Narrow: we don't expose the detailed error — the compose dialog
      // turns this into a toast ("User not found or message too long").
      lastError.value = 'send_failed';
      return false;
    }
    sent.value.unshift(data);
    return true;
  }

  async function sendToOrgOwners(orgSlug: string, body: string): Promise<number | null> {
    const { data, error } = await getApiClient().POST(
      '/api/v1/messages/to-org/{org_slug}',
      {
        params: { path: { org_slug: orgSlug } },
        body: { body },
      },
    );
    if (error || !data) {
      lastError.value = 'send_failed';
      return null;
    }
    return data.recipients;
  }

  async function sendToSuperusers(body: string): Promise<number | null> {
    const { data, error } = await getApiClient().POST('/api/v1/messages/to-superusers', {
      body: { body },
    });
    if (error || !data) {
      lastError.value = 'send_failed';
      return null;
    }
    return data.recipients;
  }

  async function markRead(messageId: string): Promise<void> {
    const { data, error } = await getApiClient().POST(
      '/api/v1/messages/{message_id}/read',
      { params: { path: { message_id: messageId } } },
    );
    if (error || !data) return;
    const idx = inbox.value.findIndex((m) => m.id === messageId);
    if (idx >= 0 && inbox.value[idx]?.read_at === null) {
      inbox.value.splice(idx, 1, data);
      unread.value = Math.max(0, unread.value - 1);
    }
  }

  async function markAllRead(): Promise<void> {
    const { error } = await getApiClient().POST('/api/v1/messages/read-all', {});
    if (error) return;
    const now = new Date().toISOString();
    inbox.value = inbox.value.map((m) => (m.read_at ? m : { ...m, read_at: now }));
    unread.value = 0;
  }

  function reset(): void {
    inbox.value = [];
    sent.value = [];
    unread.value = 0;
    lastError.value = null;
  }

  return {
    inbox,
    sent,
    unread,
    loading,
    lastError,
    unreadMessages,
    refreshInbox,
    refreshSent,
    sendToUser,
    sendToOrgOwners,
    sendToSuperusers,
    markRead,
    markAllRead,
    reset,
  };
});
