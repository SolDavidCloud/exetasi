import { defineStore } from 'pinia';
import { ref } from 'vue';

import { getApiClient } from 'src/api/client';
import type { components } from 'src/api/generated/paths';

export type AdminUser = components['schemas']['AdminUserPublic'];

export const useAdminStore = defineStore('admin', () => {
  const users = ref<AdminUser[]>([]);
  const loading = ref(false);
  const lastQuery = ref<string>('');

  async function fetchUsers(query = ''): Promise<AdminUser[]> {
    loading.value = true;
    try {
      const params: { query?: { q?: string | null } } = query
        ? { query: { q: query } }
        : {};
      const { data, error } = await getApiClient().GET('/api/v1/admin/users', params);
      if (error) {
        return users.value;
      }
      users.value = data ?? [];
      lastQuery.value = query;
      return users.value;
    } finally {
      loading.value = false;
    }
  }

  function replace(updated: AdminUser): void {
    const idx = users.value.findIndex((u) => u.id === updated.id);
    if (idx >= 0) users.value.splice(idx, 1, updated);
  }

  async function setSuperuser(username: string, value: boolean): Promise<AdminUser | null> {
    const { data, error } = await getApiClient().PATCH(
      '/api/v1/admin/users/{username}/superuser',
      {
        params: { path: { username } },
        body: { is_superuser: value },
      },
    );
    if (error || !data) return null;
    replace(data);
    return data;
  }

  async function setCanCreateOrgs(username: string, allowed: boolean): Promise<AdminUser | null> {
    const { data, error } = await getApiClient().PATCH(
      '/api/v1/admin/users/{username}/can-create-orgs',
      {
        params: { path: { username } },
        body: { allowed },
      },
    );
    if (error || !data) return null;
    replace(data);
    return data;
  }

  async function banUser(username: string, reason: string): Promise<AdminUser | null> {
    const { data, error } = await getApiClient().POST(
      '/api/v1/admin/users/{username}/ban',
      {
        params: { path: { username } },
        body: { reason },
      },
    );
    if (error || !data) return null;
    replace(data);
    return data;
  }

  async function unbanUser(username: string): Promise<AdminUser | null> {
    const { data, error } = await getApiClient().POST(
      '/api/v1/admin/users/{username}/unban',
      { params: { path: { username } } },
    );
    if (error || !data) return null;
    replace(data);
    return data;
  }

  async function transferOwner(orgSlug: string, newOwnerUsername: string): Promise<boolean> {
    const { error } = await getApiClient().POST(
      '/api/v1/admin/orgs/{org_slug}/transfer-owner',
      {
        params: { path: { org_slug: orgSlug } },
        body: { new_owner_username: newOwnerUsername },
      },
    );
    return !error;
  }

  return {
    users,
    loading,
    lastQuery,
    fetchUsers,
    setSuperuser,
    setCanCreateOrgs,
    banUser,
    unbanUser,
    transferOwner,
  };
});
