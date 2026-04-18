import { defineStore } from 'pinia';
import { computed, ref } from 'vue';

import { getApiClient } from 'src/api/client';

export interface AuthUser {
  id: string;
  username: string;
  bio: string;
  avatar_url: string | null;
  is_superuser: boolean;
  can_create_orgs: boolean;
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null);
  const loaded = ref(false);

  const isAuthenticated = computed(() => user.value !== null);
  const isSuperuser = computed(() => user.value?.is_superuser === true);
  const canCreateOrgs = computed(
    () => user.value?.is_superuser === true || user.value?.can_create_orgs === true,
  );

  async function fetchSession(): Promise<void> {
    const { data, error } = await getApiClient().GET('/api/v1/users/me');
    loaded.value = true;
    if (error) {
      user.value = null;
      return;
    }
    user.value = data ?? null;
  }

  async function devLogin(username: string): Promise<void> {
    const { error } = await getApiClient().POST('/api/v1/auth/dev/login', {
      body: { username },
    });
    if (error) {
      // If the backend returned a structured "banned" detail, surface it up
      // to the login page so it can render the reason inline — same UX as
      // the OAuth ban redirect.
      const detail = (error as { detail?: unknown }).detail;
      if (detail && typeof detail === 'object' && 'code' in detail) {
        const code = (detail as { code?: unknown }).code;
        if (code === 'banned') {
          const reason =
            'reason' in detail && typeof (detail as { reason: unknown }).reason === 'string'
              ? (detail as { reason: string }).reason
              : '';
          throw new Error(`banned:${reason}`);
        }
      }
      throw new Error('login_failed');
    }
    await fetchSession();
  }

  async function logout(): Promise<void> {
    await getApiClient().POST('/api/v1/auth/logout');
    user.value = null;
  }

  return {
    user,
    loaded,
    isAuthenticated,
    isSuperuser,
    canCreateOrgs,
    fetchSession,
    devLogin,
    logout,
  };
});
